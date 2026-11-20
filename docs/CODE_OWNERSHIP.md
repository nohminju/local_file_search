# 담당 범위

아래는 현재 역할 분담입니다. 파일 전체의 단독 작성자를 뜻하지 않으며, 실제 기여는 Git 이력으로 확인합니다.

| 담당자 | 파일·영역 | 역할 |
|---|---|---|
| 이수아 | `app.py`, `connection/service.py` | 모듈 생성·모델 공유, 분석·검색 연결, 경로와 DB ID 연결, 파일별 중복 제거·결과 수 제한·읽기 실패 반환 |
| 김하은 | `file_loader/document_loader.py` | 지원 파일 수집, PDF·PPTX 본문·내부 이미지와 일반 이미지 읽기, 청크 반환 |
| 윤소영 | `similarity/document_embedder.py`, `query_encoder/text_encoder.py` | 원본 텍스트 임베딩 모듈 담당. 현재 본문은 통합 보완한 SentenceDocumentEmbedder, 이미지 검색어는 KoreanTextEncoder 사용 |
| 임현서 | `file_encoder/image_encoder.py`, `file_encoder/document_encoder.py` | 일반 이미지와 문서에서 추출한 이미지 인코딩 |
| 노민주 | `database/db_info.py`, `database/manager.py`, `database/faiss.py` | 파일 자료형, SQLite 저장·조회, FAISS 인덱싱·검색·저장·복원 |
| 공동 | `gui/window.py` | 폴더 선택, 분석·검색 요청, 작업 상태·결과 표시, 파일 열기 |

테스트·문서는 담당별 검증과 설명을 담습니다. 이수아는 전체 연결 검증과 통합 활동 기록을 정리합니다. `study/`는 Git에서 제외하는 로컬 공부 자료입니다.

## 공동 수정과 현재 연결

- app.py는 본문용 SentenceDocumentEmbedder(ko-sroberta, 768차원)와 이미지용 OpenCLIP(512차원)을 생성합니다. 본문 검색어는 전자의 encode_query(), 이미지 검색어는 KoreanTextEncoder.encode_text()를 사용합니다.
- 일반 사진과 문서 내부 그림은 같은 ImageEncoder를 사용합니다. DocumentEncoder는 그림 전달용 래퍼이며 PDF/PPTX의 글은 DocumentLoader가 별도로 추출합니다.
- connection/text_preparation.py는 추출 본문만 126토큰·32토큰 겹침으로 나눕니다. 파일명은 임베딩하지 않습니다.
- 서비스는 일반 이미지에 이미지 점수만, PDF/PPTX에 본문·이미지 중 높은 원본 점수를 적용합니다. 하한·합산·RRF·재정렬 모델은 쓰지 않습니다. 통합 결과는 내용 해시로 묶고 점수 동점은 경로로 정합니다.
- GUI는 통합검색·이미지 검색·본문 검색을 선택하며 콘솔은 기본 통합검색입니다. DocumentEmbedder.search()와 FAISS의 선택적 min_score·compare_raw_scores()는 앱 검색에서 호출하거나 지정하지 않습니다.
- SQLite는 임시 DB이고 FAISS는 메모리 인덱스입니다. save/load 함수는 앱에 연결하지 않았습니다. 연결하려면 파일 정보·벡터·경로별 DB ID를 함께 복원해야 합니다.
- 현재 본문 모델·분할·연결·테스트의 추가 보완은 사용자 요청에 따른 AI 통합 작업입니다. 원본 팀원 모듈 작성과 구분합니다. [최신 검색 기준](SEARCH_BEHAVIOR.md), [이번 주 기여와 오늘 통합 문제](INTEGRATION_NOTES_2026-11-20.md)를 참고하세요.

## 원본 기여 참고

아래 링크는 각 모듈의 원본 기여를 확인하는 자료입니다. 이후 수정 전부를 나타내거나 현재 파일과 동일함을 뜻하지 않습니다.

| 모듈 | 원본 기록 |
|---|---|
| 로더 | [김하은 · bdf874e](https://github.com/Edmond1889/local_file_search/blob/bdf874e/document_loader.py) |
| 이미지 검색어 인코더 | [duoloo · 5b08637](https://github.com/Edmond1889/local_file_search/blob/5b08637/text_encoder.py) |
| 본문 인코더 | [duoloo · 0b20d2d](https://github.com/Edmond1889/local_file_search/blob/0b20d2d/document_embedder.py) |
| 이미지·문서 이미지 인코더 | [hyunsli7557-ux · f86f7f8](https://github.com/Edmond1889/local_file_search/blob/f86f7f8/encoders/image_encoder.py), [b6dd0e8](https://github.com/Edmond1889/local_file_search/blob/b6dd0e8/encoders/document_encoder.py) |
| SQLite·FAISS | [nohminju · d3a7462](https://github.com/Edmond1889/local_file_search/blob/d3a7462/database/manager.py), [2a4d883](https://github.com/Edmond1889/local_file_search/blob/2a4d883/database/faiss.py) |

과거 OpenCLIP 본문 구현은 원본 API로 남아 있으나 앱의 모델 선택 분기는 제거했습니다. 현재 본문 연결 클래스(connection/sentence_document_embedder.py)가 원본 API를 상속해 사용합니다. 파일명 검색은 중간 실험에서 추가했다가 제거했으므로 파일명 일치 출처를 현재 기능으로 설명하지 않습니다.


## 팀원 파일 원본 복원 — 2026-11-20 최종 반영

사용자 요청으로 팀원 파일 5개(database/faiss.py, file_encoder/document_encoder.py, file_loader/document_loader.py, query_encoder/text_encoder.py, similarity/document_embedder.py)를 원본 PR #27 병합 직전 160f055와 동일하게 복원했습니다. 팀원 담당 디렉터리에 AI가 추가한 본문 어댑터도 남기지 않도록 connection/sentence_document_embedder.py로 옮겼습니다. 긴 본문 분할은 connection/text_preparation.py에 유지합니다.

본문 ko-sroberta와 이미지 OpenCLIP 분리는 연결 모듈에서 유지하며 app.py가 FAISS 차원을 명시합니다. 원본 FAISS의 기본 본문 차원은 512지만 앱은 본문용 768을 전달합니다. 원본 FAISS는 chunk_type을 메타데이터로 저장하지 않으므로 과거 filename 메타데이터 보호 조건은 키가 있을 때만 동작합니다. 현재 앱은 메모리 인덱스를 새로 만들고 파일명을 인코딩하지 않습니다.

이 복원 이후 테스트 결과는 ACTIVITY_LOG에 추가합니다. 이전 실모델 수치는 복원 전 실행의 기록이며 새 실행 결과로 표현하지 않습니다. 앞서 서술된 팀원 파일 수정은 작업 과정의 이력이고 최종 차이에서는 제거합니다. 현재 원본 파일과 연결 코드의 구분은 이 절을 기준으로 합니다.
