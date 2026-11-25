"""로더·인코더·FAISS 검색 결과를 SQLite 파일 정보와 연결한다."""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from hashlib import sha256
from pathlib import Path

from database.db_info import DocumentInfo
from file_loader.document_loader import DocumentScanner, DocumentChunk

# 팀원 스캐너의 지원 목록을 그대로 사용하고 검색 경로 분류만 서비스에서 담당한다.
IMAGE_EXTENSIONS = DocumentScanner.SUPPORTED_EXTENSIONS & {'.jpg', '.jpeg', '.png', '.webp'}
DOCUMENT_EXTENSIONS = DocumentScanner.SUPPORTED_EXTENSIONS & {'.pdf', '.pptx'}


class ScoredFile(tuple):
    """기존 (파일, 점수) 규격을 유지하며 본문/이미지 출처를 보존한다."""
    def __new__(cls, file, score, source):
        result = super().__new__(cls, (file, score))
        result.source = source
        return result


@dataclass(frozen=True)
class SearchResult:
    """score는 선택 근거의 원본 코사인 유사도다."""
    file: DocumentInfo
    score: float
    source: str
    document_score: float | None
    image_score: float | None

    def __iter__(self):
        # 기존 (파일 정보, 점수) 소비 코드는 유지하면서 모델별 상세값도 제공한다.
        return iter((self.file, self.score))


class DocumentSearch:
    def __init__(self, loader, image_encoder, document_encoder,
                 document_embedder, query_encoder, repository, vector_index,
                 *, text_preparer=None, ocr_extractor=None,
                 image_query_translator=None,
                 document_query_translator=None):
        self.image_query_translator = image_query_translator
        self.document_query_translator = document_query_translator
        self.text_preparer = text_preparer
        self.ocr_extractor = ocr_extractor
        self.loader = loader
        self.image_encoder = image_encoder
        self.document_encoder = document_encoder
        self.document_embedder = document_embedder
        self.query_encoder = query_encoder
        self.repository = repository
        self.vector_index = vector_index
        self.file_ids = {}  # 실제 파일 경로 → DB가 반환한 번호

    def analyze(self, folder_path):
        """파일을 읽어 벡터를 인덱싱하고 파일 정보를 저장한다."""
        folder = Path(folder_path).expanduser().resolve()
        if not folder.is_dir():
            raise ValueError("존재하는 폴더를 선택하세요.")
        if self.file_ids:
            raise ValueError("재분석은 새 서비스로 시작하세요.")

        documents, failures = [], []
        image_vectors, image_chunks = [], []
        text_chunks = []
        for file_path in DocumentScanner(str(folder)).scan_files():
            path = Path(file_path)
            try:
                chunks = self.loader.process_file(str(path))
                if not chunks:
                    failures.append((path, "읽을 본문이나 이미지가 없습니다."))
                    continue
                stat = path.stat()
                info = DocumentInfo(
                    file_path=str(path),
                    file_name=path.name,
                    file_extension=path.suffix.lower(),
                    file_size=stat.st_size,
                    file_hash=sha256(path.read_bytes()).hexdigest(),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            except OSError as error:
                failures.append((path, str(error)))
                continue

            # 문서 이미지도 chunk_type이 image이므로 원본 확장자로 인코더를 고른다.
            encoder = (self.document_encoder if path.suffix.lower() in DOCUMENT_EXTENSIONS
                       else self.image_encoder)
            # 모델 오류는 읽기 실패로 숨기지 않고 호출자에게 전달한다.
            file_images = [chunk for chunk in chunks if chunk.image is not None]
            if file_images:
                vectors = encoder.encode_batch([chunk.image for chunk in file_images])
                if len(vectors) != len(file_images):
                    raise ValueError("이미지 벡터 수와 청크 수가 일치하지 않습니다.")
                image_vectors.extend(vectors)
                image_chunks.extend(file_images)

                 # 이미지 내부의 문자를 추출하여 문서 검색용 청크 생성
                if self.ocr_extractor is not None:
                    for chunk in file_images:
                        ocr_text = self.ocr_extractor.extract(chunk.image)

                        if ocr_text.strip():
                            text_chunks.append(DocumentChunk(
                                file_name=chunk.file_name,
                                file_path=chunk.file_path,
                                page_number=chunk.page_number,
                                text=ocr_text,
                                chunk_type="ocr",
                                image=None
                            ))
            text_chunks.extend(chunk for chunk in chunks if chunk.text.strip())
            documents.append(info)

        if self.text_preparer is not None:
            text_chunks = self.text_preparer.prepare(text_chunks)

        if text_chunks:
            # 같은 본문은 한 번만 인코딩하되 각 파일·페이지의 메타데이터는 유지한다.
            unique_chunks, text_positions, by_text = [], [], {}
            for chunk in text_chunks:
                if chunk.text not in by_text:
                    by_text[chunk.text] = len(unique_chunks)
                    unique_chunks.append(chunk)
                text_positions.append(by_text[chunk.text])
            self.document_embedder.embed_chunks(unique_chunks)
            vectors = self.document_embedder.embeddings[text_positions]
            self.vector_index.add_documents(vectors, text_chunks)
        if image_chunks:
            self.vector_index.add_images(image_vectors, image_chunks)

        for info in documents:
            self.file_ids[info.file_path] = self.repository.save(info)
        return documents, failures

    def search(self, query, top_k=5, mode='hybrid'):
        """검색 모드에 따라 원본 유사도 기준으로 정렬해 결과를 반환한다."""
        query = query.strip()
        if not query or top_k <= 0:
            return []

        if mode == 'hybrid':
            return self.search_hybrid(query, top_k=top_k)
        if mode == 'documents':
            count = len(self.vector_index.chunk_metas['doc'])
            if not count:
                return []
            doc_query = self._translate_query(query, self.document_query_translator)
            query_vector = self.document_embedder.encode_query(doc_query)
            hits = self.vector_index.search_documents(query_vector, top_k=count)
        elif mode == 'images':
            count = len(self.vector_index.chunk_metas['img'])
            if not count:
                return []
            image_query = self._translate_query(query, self.image_query_translator)
            query_vector = self.query_encoder.encode_text(image_query)
            hits = self.vector_index.search_images(query_vector, top_k=count)
        else:
            raise ValueError("검색 대상은 documents, images 또는 hybrid입니다.")

        results = []
        seen = set()
        # FAISS가 점수순으로 반환하므로 같은 파일의 첫 결과가 최고 점수다.
        for hit in hits:
            if mode == 'documents' and hit['chunk'].get('chunk_type') == 'filename':
                continue  # 이전 인덱스의 파일명 청크도 검색에 사용하지 않는다.
            file_id = self.file_ids[hit['chunk']['file_path']]
            if file_id in seen:
                continue
            seen.add(file_id)
            info = self.repository.find_by_id(file_id)
            if info is None:
                raise LookupError(f"DB에 파일 번호 {file_id}가 없습니다.")
            source = mode
            result = ScoredFile(info, hit['score'], source)
            results.append(result)
            if len(results) >= top_k:
                break
        return results

    @staticmethod
    def _translate_query(query, translator):
        if translator is not None:
            try:
                translated = translator(query)
                if isinstance(translated, str) and translated.strip():
                    return translated.strip()
            except Exception as error:
                print(f"[검색어 번역 오류] 원본 검색어를 사용합니다: {error}")
        return query

    def search_hybrid(self, query, top_k=5):
        """본문·OCR·이미지 검색 결과 중 높은 원본 유사도로 정렬한다."""
        query = query.strip()
        if not query or top_k <= 0:
            return []

        # 최종 결과 수를 제한하기 전에 등록 파일 전체에서 최고 점수를 찾는다.
        count = max(len(self.file_ids), top_k)
        doc_hits = self.search(query, top_k=count, mode='documents')
        image_hits = self.search(query, top_k=count, mode='images')

        records = {}
        image_extensions = IMAGE_EXTENSIONS
        document_extensions = DOCUMENT_EXTENSIONS
        for mode, hits in (('documents', doc_hits), ('images', image_hits)):
            for info, raw in hits:
                extension = Path(info.file_path).suffix.lower()
                if extension not in image_extensions | document_extensions:
                    continue
                raw = float(raw)
                if not isfinite(raw):
                    continue
                record = records.setdefault(
                    info.file_id,
                    dict(file=info, documents=None, images=None)
                )
                previous = record[mode]
                if previous is None or raw > previous:
                    record[mode] = raw

        ranked_matches = []
        for record in records.values():
            available = [
                (record[mode], mode)
                for mode in ('documents', 'images')
                if record[mode] is not None
            ]
            raw_score, source = max(available, key=lambda item: item[0])
            result = SearchResult(
                record['file'], raw_score, source,
                record['documents'], record['images']
            )
            ranked_matches.append(result)

        # 원본 유사도 내림차순으로 정렬 (동점이면 파일 경로 순)
        ranked_matches.sort(
            key=lambda item: (-item.score,
                              item.file.file_path.casefold(),
                              item.file.file_path)
        )

        results, seen = [], set()
        for match in ranked_matches:
            file_hash = getattr(match.file, 'file_hash', None)
            identity = ('hash', file_hash) if file_hash else ('path', match.file.file_path)
            if identity in seen:
                continue
            seen.add(identity)
            results.append(match)
            if len(results) >= top_k:
                break
        return results
