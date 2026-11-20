"""로더·인코더·FAISS 검색 결과를 SQLite 파일 정보와 연결한다."""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from hashlib import sha256
from pathlib import Path

from database.db_info import DocumentInfo
from file_loader.document_loader import DocumentScanner


@dataclass(frozen=True)
class SearchResult:
    """score는 선택 모델의 원본 유사도, sort_score는 기준 초과 비율이다."""
    file: DocumentInfo
    score: float
    source: str
    sort_score: float
    document_score: float | None
    image_score: float | None

    def __iter__(self):
        # 기존 (파일 정보, 점수) 소비 코드는 유지하면서 모델별 상세값도 제공한다.
        return iter((self.file, self.score))


class DocumentSearch:
    def __init__(self, loader, image_encoder, document_encoder,
                 document_embedder, query_encoder, repository, vector_index,
                 *, document_min_score=0.4, image_min_score=0.2):
        if any(not isfinite(value) or not -1 <= value < 1
               for value in (document_min_score, image_min_score)):
            raise ValueError("유사도 기준은 -1 이상 1 미만의 유한한 값이어야 합니다.")
        self.document_min_score = document_min_score
        self.image_min_score = image_min_score
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
            encoder = (self.document_encoder if path.suffix.lower() in {'.pdf', '.pptx'}
                       else self.image_encoder)
            # 모델 오류는 읽기 실패로 숨기지 않고 호출자에게 전달한다.
            file_images = [chunk for chunk in chunks if chunk.image is not None]
            if file_images:
                vectors = encoder.encode_batch([chunk.image for chunk in file_images])
                if len(vectors) != len(file_images):
                    raise ValueError("이미지 벡터 수와 청크 수가 일치하지 않습니다.")
                image_vectors.extend(vectors)
                image_chunks.extend(file_images)
            text_chunks.extend(chunk for chunk in chunks if chunk.text.strip())
            documents.append(info)

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
        """기본 검색은 모델별 기준을 통과한 원본 유사도를 보존해 통합한다."""
        query = query.strip()
        if not query or top_k <= 0:
            return []

        if mode == 'hybrid':
            return self.search_hybrid(query, top_k=top_k)
        if mode == 'documents':
            count = len(self.vector_index.chunk_metas['doc'])
            if not count:
                return []
            # 본문과 같은 모델로 검색 문장을 인코딩하고 비교는 팀원 FAISS에 맡긴다.
            query_vector = self.document_embedder.encode_query(query)
            hits = self.vector_index.search_documents(query_vector, top_k=count)
        elif mode == 'images':
            count = len(self.vector_index.chunk_metas['img'])
            if not count:
                return []
            query_vector = self.query_encoder.encode_text(query)
            hits = self.vector_index.search_images(query_vector, top_k=count)
        else:
            raise ValueError("검색 대상은 documents, images 또는 hybrid입니다.")

        results = []
        seen = set()
        # FAISS가 점수순으로 반환하므로 같은 파일의 첫 결과가 최고 점수다.
        for hit in hits:
            file_id = self.file_ids[hit['chunk']['file_path']]
            if file_id in seen:
                continue
            seen.add(file_id)
            info = self.repository.find_by_id(file_id)
            if info is None:
                raise LookupError(f"DB에 파일 번호 {file_id}가 없습니다.")
            results.append((info, hit['score']))
            if len(results) >= top_k:
                break
        return results

    def search_hybrid(self, query, top_k=5):
        """모델별 하한 필터 후 기준 초과 비율의 최댓값으로 정렬한다. 합산하지 않는다."""
        query = query.strip()
        if not query or top_k <= 0:
            return []

        # 필터·내용 중복 제거 후에도 결과를 채울 수 있도록 등록 파일 전체를 후보로 받는다.
        count = max(len(self.file_ids), top_k * 2)
        doc_results = self.search(query, top_k=count, mode='documents')
        img_results = self.search(query, top_k=count, mode='images')
        records = {}
        for mode, results in (('documents', doc_results), ('images', img_results)):
            for info, score in results:
                score = float(score)
                if not isfinite(score):
                    continue
                record = records.setdefault(info.file_id, dict(file=info, documents=None, images=None))
                record[mode] = score

        matches = []
        for record in records.values():
            eligible = []
            for mode, floor in (('documents', self.document_min_score),
                                ('images', self.image_min_score)):
                raw = record[mode]
                if raw is not None and raw >= floor:
                    # 서로 다른 하한을 0, 코사인 유사도 1을 1로 맞춘 운영상 정렬값.
                    # 확률 보정이 아니며 두 검색에 등장해도 점수를 더하지 않는다.
                    eligible.append(((min(raw, 1.0) - floor) / (1.0 - floor), mode, raw))
            if not eligible:
                continue
            # 같은 정렬값이면 본문을 표시한다. 파일 간 동점은 아래에서 경로로 정한다.
            sort_score, source, raw = max(eligible, key=lambda item: item[0])
            matches.append(SearchResult(record['file'], raw, source, sort_score,
                                        record['documents'], record['images']))

        matches.sort(key=lambda result: (-result.sort_score,
                                         result.file.file_path.casefold(), result.file.file_path))
        results, seen = [], set()
        for match in matches:
            file_hash = getattr(match.file, 'file_hash', None)
            identity = ('hash', file_hash) if file_hash else ('path', match.file.file_path)
            if identity in seen:
                continue
            seen.add(identity)
            results.append(match)
            if len(results) >= top_k:
                break
        return results
