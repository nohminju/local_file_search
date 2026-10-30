# 연결 순서

## 분석

`app.build_service()` → `DocumentSearch.analyze(folder)` 순서로 실행한다.

1. `DocumentScanner.scan_files()`가 지원하는 파일 경로를 모은다.
2. `DocumentLoader.process_file(path)`가 확장자를 구분해 DocumentChunk 목록을 반환한다.
3. 본문이 있는 청크는 모아서 `DocumentEmbedder.embed_chunks(chunks)`에 전달한다.
4. 이미지 파일의 PIL 이미지는 ImageEncoder, 문서에서 꺼낸 이미지는 DocumentEncoder에 전달한다.
5. 파일 정보는 DocumentInfo로 만들어 `Repository.save(info)`에 저장한다. 반환된 ID를 경로·이미지 벡터와 연결한다.

`analyze()`의 반환값은 `(저장한 파일 목록, (읽기 실패 경로, 이유) 목록)`이다.
빈 파일·읽지 못한 파일은 실패 목록에 들어간다. 모델·DB 오류는 호출자에게 전달한다.
같은 서비스로 재분석하지 않는다. GUI에서 분석을 다시 누르면 새 서비스를 만든다.

## 검색

화면과 콘솔은 `service.search(query, mode=...)`를 호출한다. documents는 본문, images는 임시 이미지 검색이다.
팀원 `DocumentEmbedder.search()`가 검색 문장을 본문과 같은 모델로 인코딩하고 비교한다.
같은 파일의 여러 청크가 나오면 가장 높은 점수 하나를 사용하고, DB에서 이름·경로를 조회한다.
반환값은 `(DocumentInfo, 점수)` 목록이며 기본 최대 결과 수는 5개다.

이미지 검색: `encode_query(query, mode='images')` → KoreanTextEncoder → 임시 `search_images()` → DB 조회 순서다.
임시 함수는 이미지·문장 벡터의 코사인 유사도를 계산해 파일별 최고 점수 순으로 반환한다. 비교할 이미지가 없으면 빈 목록이다.
본문과 이미지는 서로 다른 모델 공간이므로 점수를 합치지 않는다. 담당자 이미지 비교 구현을 받으면 임시 함수를 교체한다.
