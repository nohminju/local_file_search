"""로더·인코더·FAISS 검색 결과를 SQLite 파일 정보와 연결한다."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from database.db_info import DocumentInfo
from file_loader.document_loader import DocumentScanner


class DocumentSearch:
    def __init__(self, loader, image_encoder, document_encoder,
                 document_embedder, query_encoder, repository, vector_index):
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
            for chunk in chunks:
                if chunk.image is not None:
                    image_vectors.append(encoder.encode(chunk.image))
                    image_chunks.append(chunk)
            text_chunks.extend(chunk for chunk in chunks if chunk.text.strip())
            documents.append(info)

        if text_chunks:
            self.document_embedder.embed_chunks(text_chunks)
            self.vector_index.add_documents(self.document_embedder.embeddings, text_chunks)
        if image_chunks:
            self.vector_index.add_images(image_vectors, image_chunks)

        for info in documents:
            self.file_ids[info.file_path] = self.repository.save(info)
        return documents, failures

    def search(self, query, top_k=5, mode='documents'):
        """FAISS 점수순으로 파일 중복을 제거해 최대 top_k개를 반환한다."""
        query = query.strip()
        if not query or top_k <= 0:
            return []

        if mode == 'documents':
            count = len(self.vector_index.chunk_metas['doc'])
            if not count:
                return []
            # 본문과 같은 모델로 검색 문장을 인코딩하고 비교는 팀원 FAISS에 맡긴다.
            query_vector = self.document_embedder.model.encode([query])
            hits = self.vector_index.search_documents(query_vector, top_k=count)
        elif mode == 'images':
            count = len(self.vector_index.chunk_metas['img'])
            if not count:
                return []
            query_vector = self.query_encoder.encode_text(query)
            hits = self.vector_index.search_images(query_vector, top_k=count)
        else:
            raise ValueError("검색 대상은 documents 또는 images입니다.")

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
