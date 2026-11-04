from datetime import datetime
from document_info import DocumentInfo
from repository import Repository

repo = Repository()

cat_documents = [
    DocumentInfo(
        file_path="/images/cats/cute_cat_01.png",
        file_name="cute_cat_01",
        file_extension="png",
        file_size=2048576,
        file_hash="hash_cat_001",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    ),
    DocumentInfo(
        file_path="/images/cats/sleeping_cat_02.jpg",
        file_name="sleeping_cat_02",
        file_extension="jpg",
        file_size=1048576,
        file_hash="hash_cat_002",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
]

if __name__ == "__main__":
    for doc in cat_documents:
        saved_id = repo.save(doc)
        print(f"저장 완료 (ID: {saved_id}) - {doc.file_name}.{doc.file_extension}")
