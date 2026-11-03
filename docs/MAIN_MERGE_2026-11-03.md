# 2026-11-03 main 병합

원본: C:\Capstone\main, 커밋 `3542252`.
main은 읽기만 했고 아래 파일을 현재 작업본으로 가져왔다.

| 원본 → 작업본 | 실제 변경 |
|---|---|
| storage/db_info.py → database/db_info.py | 머리 주석만 삭제. 필드 변경 없음 |
| storage/db_manager.py → database/db_manager.py | DocumentInfo import를 `.db_info`로 수정 |
| encoders/text_encoder.py → query_encoder/text_encoder.py | model·tokenizer 공유, 단일 입력도 2차원 NumPy 배열 반환 |
| document_embedder.py → similarity/document_embedder.py | 외부 model 전달 지원, 빈 본문 제외, 설명 주석 정리 |

입력 인코더의 model_name·pretrained 인자와 to_numpy 옵션, 파일 끝 실행 예시는 제거됐다.
문서 본문의 코사인 비교 수식과 DB 테이블·저장 로직은 바뀌지 않았다.

내 연결 코드에서는 이미지 모델과 tokenizer를 입력 인코더에 전달하고,
검색 문장 반환값의 첫 행 `[0]`을 꺼내 임시 이미지 비교 함수에 넘긴다.
DB가 자료형을 직접 가져오므로 루트 document_info.py는 제거했다.
본문은 이미 비어 있지 않은 청크만 넘기므로 원본의 빈 본문 필터와 청크 순서가 맞는다.

팀원 파일 4개는 원본과 바이트 단위로 같게 유지했다.
README·DB/연결/구조 문서·공부용 비유·설명 포함 전체 코드를 현재 규격으로 갱신했다.

검증: 자동 테스트 26개 통과. 실제 모델로 PDF 본문·PPTX/PNG 이미지·고양이 사진 3장 검색을 확인했다.
공부 노트의 정의 셀 실행과 실제 소스 11개 일치, Markdown 링크도 확인했다.
