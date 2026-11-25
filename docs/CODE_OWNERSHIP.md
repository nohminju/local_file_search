# 담당 범위

아래는 현재 역할 분담입니다. 파일 전체의 단독 작성자를 뜻하지 않으며, 실제 기여는 Git 이력으로 확인합니다.

로컬 기준은 `document-demo-v3`의 `f9a095f`와 후속 통합 변경입니다. 팀원 코드는 FAISS를 분리했고 로컬 통합은 기존 호출부를 연결하고 본문 검색어 처리 경로를 복원했습니다.

| 담당자 | 파일·영역 | 역할 |
|---|---|---|
| 이수아 | `app.py`, `connection/service.py` | 모듈 생성·모델 공유, 분석·검색 연결, 경로와 DB ID 연결, 파일별 중복 제거·결과 수 제한·읽기 실패 반환 |
| 김하은 | `file_loader/document_loader.py` | 지원 파일 수집, PDF·PPTX 본문·내부 이미지와 일반 이미지 읽기, 청크 반환 |
| 윤소영 | `similarity/document_embedder.py`, `query_encoder/text_encoder.py` | 원본 텍스트 임베딩 모듈 담당. 현재 본문은 통합 보완한 SentenceDocumentEmbedder, 이미지 검색어는 KoreanTextEncoder 사용 |
| 임현서 | `file_encoder/image_encoder.py`, `file_encoder/document_encoder.py` | 일반 이미지와 문서에서 추출한 이미지 인코딩 |
| 노민주 | `database/db_info.py`, `database/manager.py`, `database/document_faiss.py`, `database/image_faiss.py` | 파일 자료형, SQLite, 문서·이미지별 FAISS 인덱스 |
| 공동 | `gui/window.py` | 폴더 선택, 분석·검색 요청, 작업 상태·결과 표시, 파일 열기 |

테스트·문서는 담당별 검증과 설명을 담습니다. 이수아는 전체 연결 검증과 통합 활동 기록을 정리합니다. `study/`는 Git에서 제외하는 로컬 공부 자료입니다.

## 공동 수정과 현재 연결

- app.py는 본문용 SentenceDocumentEmbedder(ko-sroberta, 768차원)와 이미지용 OpenCLIP(512차원)을 생성합니다. 본문 검색어는 전자의 encode_query(), 이미지 검색어는 KoreanTextEncoder.encode_text()를 사용합니다.
- 일반 사진과 문서 내부 그림은 같은 ImageEncoder를 사용합니다. DocumentEncoder는 그림 전달용 래퍼이며 PDF/PPTX의 글은 DocumentLoader가 별도로 추출합니다.
- connection/text_preparation.py는 추출 본문만 126토큰·32토큰 겹침으로 나눕니다. 파일명은 임베딩하지 않습니다.
- 서비스는 일반 이미지에 이미지 점수만, PDF/PPTX에 본문·이미지 중 높은 원본 점수를 적용합니다. 하한·합산·RRF·재정렬 모델은 쓰지 않습니다. 통합 결과는 내용 해시로 묶고 점수 동점은 경로로 정합니다.
- GUI는 통합검색·이미지 검색·본문 검색을 선택하며 콘솔은 기본 통합검색입니다. DocumentEmbedder.search()와 FAISS의 compare_raw_scores()는 앱 검색에서 호출하지 않습니다. 게시 직전 보존 병합한 팀원 0bf2242에서 미사용 search_combined()는 제거됐습니다. 최신 FAISS 개별 검색은 min_score 인자가 없습니다.
- SQLite는 임시 DB이고 FAISS는 메모리 인덱스입니다. save/load 함수는 앱에 연결하지 않았습니다. 연결하려면 파일 정보·벡터·경로별 DB ID를 함께 복원해야 합니다.
- 현재 본문 모델·분할·연결·테스트의 추가 보완은 사용자 요청에 따른 AI 통합 작업입니다. 원본 팀원 모듈 작성과 구분합니다. [최신 검색 기준](SEARCH_BEHAVIOR.md), [2026-11-16~20 기여와 통합 문제](INTEGRATION_NOTES_2026-11-20.md)를 참고하세요.

## 원본 기여 참고

아래 링크는 각 모듈의 원본 기여를 확인하는 자료입니다. 이후 수정 전부를 나타내거나 현재 파일과 동일함을 뜻하지 않습니다.

| 모듈 | 원본 기록 |
|---|---|
| 로더 | [김하은 · bdf874e](https://github.com/Edmond1889/local_file_search/blob/bdf874e/document_loader.py) |
| 이미지 검색어 인코더 | [duoloo · 5b08637](https://github.com/Edmond1889/local_file_search/blob/5b08637/text_encoder.py) |
| 본문 인코더 | [duoloo · 0b20d2d](https://github.com/Edmond1889/local_file_search/blob/0b20d2d/document_embedder.py) |
| 이미지·문서 이미지 인코더 | [hyunsli7557-ux · f86f7f8](https://github.com/Edmond1889/local_file_search/blob/f86f7f8/encoders/image_encoder.py), [b6dd0e8](https://github.com/Edmond1889/local_file_search/blob/b6dd0e8/encoders/document_encoder.py) |
| SQLite·FAISS | [nohminju · d3a7462](https://github.com/Edmond1889/local_file_search/blob/d3a7462/database/manager.py), [2a4d883](https://github.com/Edmond1889/local_file_search/blob/2a4d883/database/faiss.py) |

팀원 DocumentEmbedder가 청크 처리와 검색어 한→영 번역을 담당합니다. SentenceDocumentEmbedder는 모델 생성과 `_encode()`를 구현해 같은 검색어 처리 흐름에서 ko-sroberta를 사용합니다.

## 현재 통합 코드의 책임

- `app.py`는 모델·인덱스를 조립하고 이미지 경로에 한→영 번역기를 전달합니다.
- `connection/service.py`는 본문 검색어를 임베더에 전달하고 이미지 검색어는 번역 후 이미지 검색 인코더에 전달합니다.
- `connection/sentence_document_embedder.py`는 팀원 `encode_query()`를 상속합니다. 문서 본문은 추출한 원문으로 인코딩합니다.
- `database/faiss.py`는 두 팀원 인덱스에 추가·검색을 위임하고 기존 통합 저장 자료의 호환을 담당합니다.
- connection/text_preparation.py: 모델 길이를 넘는 추출 본문의 분할. 파일명·OCR은 처리하지 않음.

과거 팀원 코드 복원과 번역기 연결 과정은 [활동 기록](ACTIVITY_LOG.md)에 보존했습니다.


## 이번 main 수신 변경 — 3610720 → fc2a48d

| 담당·파일 | main에서 받은 변경 |
|---|---|
| 김하은 · connection/translator.py | Google을 DeepL 양방향 번역으로 교체. 한→영·영→한 함수, .env API 키 로딩, lru_cache 캐시, 단독 영단어가 그대로 반환될 때 관사를 붙여 재시도 추가 |
| 김하은 · connection/service.py | 본문용 영→한, 이미지용 한→영 번역 연결. 원본 유사도 최댓값 정렬은 유지 |
| 윤소영(duoloo) · similarity/document_embedder.py | 검색어 인코딩 전 한→영 번역과 모델 입력 길이 속성 추가 |
| 윤소영(duoloo) · gui/window.py | 원본 점수만 표시하던 결과 카드에 환산 일치도 %와 원본 유사도를 함께 표시 |
| 노민주 · database/faiss.py | 개별 검색의 min_score 인자 제거, 하한·RRF 방식의 search_combined 보조 함수 추가, 벡터 배열 차원 검사 보완 |
| 노민주 · database/manager.py | DB 처리 설명·주석 보강. 이번 차이에서 실행 동작 변경은 없음 |

FAISS save/load는 기존 기능입니다. GUI 환산식·DeepL 번역기·FAISS 알고리즘은 수신한 팀원 구현을 유지했습니다. 표의 작성자는 이번 Git 커밋 기준이며 파일 전체의 단독 작성자를 뜻하지 않습니다.

## 이번 로컬 통합 수정 — fc2a48d 대비

| 파일·영역 | 로컬 통합 시 수정 |
|---|---|
| similarity/document_embedder.py | 팀원 코드의 번역기 import를 실제 connection.translator 경로로 수정. 팀원 파일의 추가 수정은 이것뿐 |
| app.py | 이미지 검색에 한→영 번역기를 전달하고 본문 검색어는 팀원 임베더에 그대로 전달 |
| connection/service.py | 기존 미커밋 번역 작업과 main의 충돌 해결. 주입받은 함수를 경로별로 호출하고 예외·빈 값·잘못된 반환이면 원문 사용 |
| connection/sentence_document_embedder.py | 팀원 encode_query를 상속해 한국어 검색어를 영어로 번역하고 ko-sroberta로 인코딩 |
| requirements.txt·.gitignore | deepl·python-dotenv 의존성과 .env 제외 규칙 반영 |
| 테스트·비교 도구·문서 | 번역 방향·실패 대체·중복 번역 방지 검증, 변경된 FAISS API·GUI 표시 반영. 과거 Google 평가와 현재 DeepL 연결 구분 |

본문 모델과 분할·모델 공유 구조는 유지했습니다. [GUI 설치·실행](../README.md#4-gui-설치와-실행)
