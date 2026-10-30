# DB와 DocumentInfo

`database/db_info.py`의 DocumentInfo는 아래 파일 정보를 묶는 자료형이다.
연결 코드가 객체를 만들고 DB는 `document.file_name`처럼 값을 꺼내 저장한다.

| 항목 | 의미 |
|---|---|
| file_path / file_name | 절대 경로 / 파일 이름 |
| file_extension / file_size | 확장자 / 바이트 크기 |
| file_hash | 파일 내용의 SHA-256 문자열 |
| created_at / updated_at | 정보 생성 시각 / 파일 수정 시각, UTC 문자열 |
| file_id | 저장 후 DB가 반환하는 번호 |

루트의 `document_info.py`는 같은 클래스를 전달하는 import 연결 파일이다.
DB 원본이 `from document_info import DocumentInfo`를 사용해서 필요하다.
팀원 DB의 import를 `database.db_info`로 수정할 때 제거할 수 있다. 클래스 정의는 중복되지 않는다.

테이블은 `document_metadata`다. Repository는 `save()`와 `find_by_id()`로 저장·조회한다.
현재 앱은 임시 DB를 사용하며 벡터는 메모리에 둔다. 재실행 후 검색을 복원하지 않는다.
같은 경로의 중복 저장은 오류가 나며 DB·벡터를 함께 되돌리는 기능은 없다.
원본 SQLite 연결 종료 처리는 담당자 점검이 필요하다. Windows에서 임시 DB 정리 시 잠금이 발생할 수 있다.

이전 image-search-demo-v2는 `storage/db_manager.py`의 VectorIndex가 정규화한 벡터의 내적을 계산했다.
최신 DB에는 VectorIndex가 없다. 현재 본문 비교는 팀원 DocumentEmbedder, 이미지 비교는 `similarity/temporary_image_similarity.py`의 임시 구현이 맡는다. DB 안에 비교 함수를 추가하지 않았다.
