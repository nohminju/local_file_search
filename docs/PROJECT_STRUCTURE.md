# 폴더 역할

| 위치 | 역할 |
|---|---|
| file_loader/document_loader.py | 파일 수집, 이미지·PDF·PPTX 읽기 |
| file_encoder/image_encoder.py | PIL 이미지를 OpenCLIP 벡터로 변환 |
| file_encoder/document_encoder.py | 문서에서 꺼낸 PIL 이미지를 ImageEncoder에 전달 |
| similarity/document_embedder.py | 본문·검색 문장을 ko-SRoBERTa로 인코딩하고 비교 |
| query_encoder/text_encoder.py | 이미지와 같은 OpenCLIP 모델로 검색 문장 인코딩 |
| similarity/temporary_image_similarity.py | 임시 구현된 이미지 유사도 비교·파일별 최고 점수 정렬 |
| database/db_info.py | 파일 정보를 묶는 DocumentInfo 정의 |
| database/db_manager.py | SQLite 파일 정보 저장·조회 |
| document_info.py | 팀원 DB가 사용하는 import 이름 연결 |
| connection/service.py | 로더·인코더 결과와 DB 파일 ID 연결 |
| app.py | 객체 생성과 콘솔 실행, GUI 실행 분기 |
| gui/window.py | 폴더 선택·분석·본문/임시 이미지 검색 화면 |
| tests / study | 연결 검증 / 설명 포함 전체 코드 |

최신 DocumentLoader에 이미지 읽기가 포함되어 별도 image_loader.py는 없다.
DocumentEncoder는 PDF 경로를 읽지 않는다. PDF 본문은 DocumentEmbedder로 전달한다.
