# 담당 범위와 공유

| 코드 | 구분 |
|---|---|
| file_loader/document_loader.py | 팀원 로더 |
| file_encoder/image_encoder.py / document_encoder.py | 팀원 이미지 인코더·문서 이미지 연결 |
| similarity/document_embedder.py | 팀원 본문 인코딩·유사도 검색 |
| query_encoder/text_encoder.py | 팀원 이미지용 문장 인코더 |
| database/db_info.py / db_manager.py | 팀원 파일 자료형·DB |
| connection/service.py / app.py / gui/window.py | 내 연결·실행·화면 코드 |
| similarity/temporary_image_similarity.py | 사용자 요청으로 추가한 임시 이미지 비교 구현. 담당자 구현으로 교체 예정 |
| document_info.py | 내 import 연결 파일 |
| docs / study / tests | 설명·공부 자료·연결 검증 |

팀원 알고리즘 본문은 유지한다. document_encoder.py는 가져올 때 import 경로만 현재 위치에 맞춘 상태다.
내 임시 로더·빈 인코더는 제거했다. 이미지 비교는 사용자 요청으로 임시 구현을 다시 연결했으며 파일명·화면에 임시 상태를 표시한다.

공유 전에는 `git status`와 `git diff`로 추가·수정·삭제 목록을 확인한다.
공부 폴더를 제외하려면 `git add .` 대신 올릴 파일 경로만 골라 스테이징한다.
팀원 원본 복사본은 통합 상대 브랜치와 비교해 필요한 변경만 포함한다. DB·캐시·개인 메모도 제외한다.
백업 브랜치에 올리는 작업과 팀 원본 main에 통합하는 작업은 별도로 판단한다.
