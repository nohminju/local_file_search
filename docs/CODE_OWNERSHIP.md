# 담당 범위

아래는 현재 역할 분담입니다. 파일 전체의 단독 작성자를 뜻하지 않으며, 실제 기여는 Git 이력으로 확인합니다.

| 담당자 | 파일·영역 | 역할 |
|---|---|---|
| 이수아 | `app.py`, `connection/service.py` | 모듈 생성·모델 공유, 분석·검색 연결, 경로와 DB ID 연결, 파일별 중복 제거·결과 수 제한·읽기 실패 반환 |
| 김하은 | `file_loader/document_loader.py` | 지원 파일 수집, PDF·PPTX 본문·내부 이미지와 일반 이미지 읽기, 청크 반환 |
| 윤소영 | `similarity/document_embedder.py`, `query_encoder/text_encoder.py` | 본문·본문 검색어 및 이미지 검색어 인코딩 |
| 임현서 | `file_encoder/image_encoder.py`, `file_encoder/document_encoder.py` | 일반 이미지와 문서에서 추출한 이미지 인코딩 |
| 노민주 | `database/db_info.py`, `database/manager.py`, `database/faiss.py` | 파일 자료형, SQLite 저장·조회, FAISS 인덱싱·검색·저장·복원 |
| 공동 | `gui/window.py` | 폴더 선택, 분석·검색 요청, 작업 상태·결과 표시, 파일 열기 |

테스트·문서는 담당별 검증과 설명을 담습니다. 이수아는 전체 연결 검증과 통합 활동 기록을 정리합니다. `study/`는 Git에서 제외하는 로컬 공부 자료입니다.

## 공동 수정과 현재 연결

- 본문·이미지의 벡터 비교는 FAISS에 맡기고 서비스에서 파일별 결과를 정리합니다. `DocumentEmbedder.search()`는 앱에서 호출하지 않습니다.
- RRF 통합 검색 초안은 노민주의 `bc66a2d`에서 추가됐습니다. 이후 서비스 클래스·기존 분석·검색을 복원하고 GUI·콘솔에서 모드 선택 없이 본문·이미지를 함께 검색하도록 연결했습니다. 2026-11-20 사용자 요청으로 현재는 모델별 원본 유사도 하한을 적용한 뒤 기준 초과 비율의 최댓값으로 정렬하고 원본 유사도를 표시합니다. 두 검색에 등장해도 합산하지 않습니다. 같은 내용은 SHA-256으로 묶습니다. [오류·수정 기록](SERVICE_REPAIR_2026-11-17.md)
- SQLite 연결 종료와 FAISS 입력·저장 검증은 팀원 변경을 반영했습니다. FAISS 빈 입력·복원 실패 시 상태 유지 검증은 통합 과정에서 추가 보완했습니다. 자세한 작업 이력은 [활동 기록](ACTIVITY_LOG.md)에 있습니다.
- FAISS 저장·복원 함수는 앱에서 호출하지 않습니다. 앱에 연결할 때는 파일 정보·벡터 인덱스·경로별 DB ID를 함께 복원해야 합니다.

## 원본 기여 참고

아래 링크는 각 모듈의 원본 기여를 확인하는 자료입니다. 이후 수정 전부를 나타내거나 현재 파일과 동일함을 뜻하지 않습니다.

| 모듈 | 원본 기록 |
|---|---|
| 로더 | [김하은 · bdf874e](https://github.com/Edmond1889/local_file_search/blob/bdf874e/document_loader.py) |
| 이미지 검색어 인코더 | [duoloo · 5b08637](https://github.com/Edmond1889/local_file_search/blob/5b08637/text_encoder.py) |
| 본문 인코더 | [duoloo · 0b20d2d](https://github.com/Edmond1889/local_file_search/blob/0b20d2d/document_embedder.py) |
| 이미지·문서 이미지 인코더 | [hyunsli7557-ux · f86f7f8](https://github.com/Edmond1889/local_file_search/blob/f86f7f8/encoders/image_encoder.py), [b6dd0e8](https://github.com/Edmond1889/local_file_search/blob/b6dd0e8/encoders/document_encoder.py) |
| SQLite·FAISS | [nohminju · d3a7462](https://github.com/Edmond1889/local_file_search/blob/d3a7462/database/manager.py), [2a4d883](https://github.com/Edmond1889/local_file_search/blob/2a4d883/database/faiss.py) |

- 실제 샘플 비교 후 본문/본문 검색어는 SentenceDocumentEmbedder(ko-sroberta 768차원), 이미지/이미지 검색어는 기존 OpenCLIP(512차원)으로 분리했습니다. 기존 OpenCLIP 본문 구현은 비교 경로로 보존했습니다. [비교 보고서](TEXT_MODEL_IMPROVEMENT_2026-11-20.md)
