# 담당 범위와 공유

## 역할 분담 — 현재 코드 기준

기존 담당자는 유지하고, 맡는 기능과 결과물을 실제 호출 흐름에 맞춰 정리했다. 역할상 책임을 나타내며 실제 작성자 이력을 뜻하지 않는다.

| 담당자 | 담당 영역 | 현재 코드 기준 결과물 |
|---|---|---|
| 이수아 | 전체 실행 흐름·검색 서비스 통합 | 로더·임베딩·FAISS·DB 연결, 검색 모드 분기, 파일별 중복 제거·결과 수 제한, 읽기 실패 목록 반환 |
| 김하은 | 파일 탐색·내용 추출 | 지원 파일 목록 수집, PDF·PPTX 본문과 내부 이미지·일반 이미지 읽기, 청크 반환, 읽기 실패 처리 |
| 윤소영 | 본문·검색 문장 임베딩 | 문서 본문과 본문 검색어를 ko-SRoBERTa 벡터로 변환하고, 이미지 검색어는 OpenCLIP 텍스트 벡터로 변환 |
| 임현서 | 이미지 임베딩 | 이미지 파일과 문서에서 추출한 이미지를 OpenCLIP 이미지 벡터로 변환 |
| 노민주 | 파일 정보 DB·벡터 인덱스·유사도 검색 | SQLite 파일 정보 저장·갱신·조회, FAISS 본문·이미지 인덱스 생성과 검색, 인덱스 저장·불러오기 함수 |
| 다 같이 | GUI | 폴더 선택, 분석·검색 요청, 문서/이미지 모드 선택, 작업 상태·검색 결과 표시, 결과 파일 열기 |

## 현재 코드와 담당 영역

아래 표는 역할 분담을 현재 파일에 대응시킨 것이다. 각 파일을 한 사람이 전부 작성했다는 의미는 아니다.

| 코드 | 담당자·역할 |
|---|---|
| `app.py` / `connection/service.py` | 이수아: 모듈 생성·모델 공유, 분석·검색 순서 제어, 파일 경로와 DB ID 연결, 파일별 결과 정리 |
| `file_loader/document_loader.py` | 김하은: DocumentScanner로 파일 수집, DocumentLoader로 읽기, DocumentChunk 반환 |
| `similarity/document_embedder.py` | 윤소영: 본문 임베딩과 같은 모델의 본문 검색어 인코딩 영역 |
| `query_encoder/text_encoder.py` | 윤소영: 이미지 검색어 인코딩. 이미지 인코더와 같은 OpenCLIP 모델을 공유 |
| `file_encoder/image_encoder.py` / `file_encoder/document_encoder.py` | 임현서: PIL 이미지 인코딩, 문서에서 꺼낸 이미지를 같은 이미지 인코더로 처리 |
| `database/db_info.py` / `database/manager.py` / `database/faiss.py` | 노민주: 파일 자료형, SQLite 저장·조회, 본문·이미지 벡터 인덱싱·검색 |
| `gui/window.py` | 공동: 화면 구성, 작업 큐, 결과 표시·파일 열기 |
| `tests` / `docs` | 담당별 검증·설명 기록. 이수아는 전체 연결 검증과 통합 활동 기록 정리 |
| `study` | 로컬 공부 자료; GitHub 백업에서 제외 |

파일을 찾아 읽는 것은 김하은의 로더, 벡터를 만드는 것은 윤소영·임현서의 인코더, 벡터 유사도로 순위를 구하는 것은 노민주의 FAISS가 담당한다. 이수아의 서비스는 이 결과를 연결해 같은 파일의 중복을 제거하고 기본 5개 파일을 반환한다.

현재 앱의 본문·이미지 비교는 모두 FAISS를 사용한다. `DocumentEmbedder.search()`는 파일에 남아 있지만 앱에서는 호출하지 않는다.

FAISS의 save/load 함수는 있으나 앱에서는 호출하지 않는다. 향후 저장·복원 기능을 연결할 때 노민주는 인덱스 저장·불러오기 동작을, 이수아는 파일 정보·인덱스를 함께 복원하는 실행 흐름을 맡는다. 문서 페이지 전체 이미지화·OCR도 현재 구현 범위에 포함하지 않는다.

## 연결 수정과 공유

### 원본 기여를 확인할 Git 기록

현재 경로에서 새 파일 추가로 보이더라도 원본 커밋은 남아 있다. 아래는 로컬 Git에서 확인한 원본 경로·계정 기록이며, 위 역할표와 실제 작성 이력을 구분해 참고한다.

| 현재 파일 | 확인 가능한 원본 기록 |
|---|---|
| `file_loader/document_loader.py` | [김하은 · document_loader.py · bdf874e](https://github.com/Edmond1889/local_file_search/blob/bdf874e/document_loader.py). `63b57d6`에서 R100 이동으로 인식되어 이전 이력 추적 가능 |
| `query_encoder/text_encoder.py` | [duoloo · text_encoder.py · 5b08637](https://github.com/Edmond1889/local_file_search/blob/5b08637/text_encoder.py). 이전 경로로 이력 추적 가능 |
| `similarity/document_embedder.py` | [duoloo · document_embedder.py · 0b20d2d](https://github.com/Edmond1889/local_file_search/blob/0b20d2d/document_embedder.py). main `3542252`의 원본과 줄바꿈을 제외한 코드가 같음 |
| `file_encoder/image_encoder.py` | [hyunsli7557-ux · encoders/image_encoder.py · f86f7f8](https://github.com/Edmond1889/local_file_search/blob/f86f7f8/encoders/image_encoder.py). 현재 파일과 바이트 단위로 같음 |
| `file_encoder/document_encoder.py` | [hyunsli7557-ux · encoders/document_encoder.py · b6dd0e8](https://github.com/Edmond1889/local_file_search/blob/b6dd0e8/encoders/document_encoder.py). 현재 파일은 import 경로만 다름 |
| `database/manager.py` / `database/faiss.py` | [nohminju · manager.py · d3a7462](https://github.com/Edmond1889/local_file_search/blob/d3a7462/database/manager.py), [faiss.py · 2a4d883](https://github.com/Edmond1889/local_file_search/blob/2a4d883/database/faiss.py). 현재 경로에 작성·수정 기록이 남아 있음 |

### 이번 연결 변경

2026-11-06 연결 수정: app.py·connection/service.py에서 팀원 FaissManager를 사용하도록 연결했다. 테스트·의존성·현재 동작 설명도 갱신했다.
팀원 로더·인코더·DB·FAISS 원본은 수정하지 않았다. 기존 GUI 구조는 유지하고 중복 설명 주석만 정리했다. 임시 이미지 비교 함수와 전용 테스트는 제거했다.
팀원 코드에서 확인된 문제와 검증 범위는 [전달 사항](TEAM_REVIEW_2026-11-06.md)에 정리했다.

공유 전에는 `git status`와 `git diff`로 추가·수정·삭제 목록을 확인한다.
공부 폴더를 제외하려면 `git add .` 대신 올릴 파일 경로만 골라 스테이징한다.
팀원 원본 복사본은 통합 상대 브랜치와 비교해 필요한 변경만 포함한다. DB·캐시·개인 메모도 제외한다.
백업 브랜치에 올리는 작업과 팀 원본 main에 통합하는 작업은 별도로 판단한다.
