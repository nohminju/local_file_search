# Local File Search

PDF·PPTX의 본문과 내부 이미지, 일반 이미지 파일을 문장으로 검색하는 로컬 프로그램입니다.

## 설치와 실행

Python과 Tkinter가 필요합니다. 통합 검증에는 Python 3.14 환경을 사용했습니다. 설치와 실행에는 같은 Python 환경을 사용하세요.

```powershell
python -m pip install -r requirements.txt
python app.py --gui
```

콘솔 실행은 `python app.py`입니다. GUI에서는 폴더 선택 → 분석 → 검색어 입력 → 검색 순서로 사용합니다. 첫 실행에는 모델 다운로드가 필요할 수 있습니다.

이 PC에서는 기존 환경을 재사용해 다음과 같이 실행할 수 있습니다.

```powershell
cd C:\Capstone\document-search-demo-v3
& C:\Capstone\document-search-demo-v2\.venv314\Scripts\python.exe app.py --gui
```

## 현재 모델과 연결

2026-11-20 main의 변경을 반영해 본문·이미지·검색어 모두 OpenCLIP `xlm-roberta-base-ViT-B-32` / `laion5b_s13b_b90k`를 사용합니다. 앱에서 모델 객체와 tokenizer를 공유하며 본문·이미지는 각각 별도 512차원 FAISS 인덱스에 저장합니다. 이전 본문 모델은 `jhgan/ko-sroberta-multitask` / 768차원이었습니다.

본문 검색은 `DocumentEmbedder.encode_query()`를 호출합니다. 이미지는 파일 안의 그림을 배치로 인코딩하고, 동일 본문은 한 번만 인코딩한 뒤 모든 원본 청크의 파일·페이지 메타데이터를 연결합니다. 본문 인코딩도 기본 8개씩 배치 처리합니다.

## 검색 결과

- 모드 선택 없이 본문과 이미지를 함께 검색하고 파일별 최고 결과를 사용합니다.
- 본문 0.4, 이미지 0.2의 초기 하한을 적용합니다. `DocumentSearch`의 `document_min_score`, `image_min_score`로 조정합니다. **본문 0.4는 이전 모델에서 정한 값을 유지한 것으로 새 OpenCLIP 본문 모델에 대한 적정성은 미검증입니다.**
- 각 검색에서 하한을 통과한 점수를 `(원본 유사도 - 해당 하한) / (1 - 해당 하한)`으로 변환하고, **파일별 최댓값 하나**로 정렬합니다. 두 검색에 나와도 합산·가산하지 않습니다. 원본 유사도가 1을 조금 넘는 부동소수점 오차는 정렬 계산에서만 1로 제한합니다.
- GUI·콘솔에는 최댓값을 제공한 본문/이미지의 원본 유사도를 표시합니다. 같은 정렬값이면 본문을 표시하며, 양쪽 원본 점수는 SearchResult.document_score/image_score에 보관합니다.
- 이 변환은 모델별 하한을 맞춘 운영상 규칙이며 학습된 관련성·확률 보정이 아닙니다. 실제 모델이 무관한 파일에 높은 점수를 주는 오류까지 해결하지는 못합니다.
- 같은 파일의 여러 페이지·그림을 묶고 SHA-256이 같은 내용도 하나만 반환합니다. 동점은 경로 순서로 정합니다.
- 기본 최대 5개이며 하한을 통과한 결과가 부족하면 적게 반환합니다.

이전 본문 모델의 실제 검색 품질·속도 측정은 [11월 17일 기록](docs/SEARCH_AND_UNUSED_CODE_2026-11-17.md)에 있습니다. 현재 모델의 성능 수치로 해석하지 마세요. OpenCLIP tokenizer의 최대 길이를 넘는 본문은 잘릴 수 있으며 별도 긴 문장 분할은 구현하지 않았습니다.

## 지원 범위와 제약

- PDF: 추출 가능한 본문과 가로·세로 모두 100px 이상인 내부 이미지.
- PPTX: 글·표의 본문과 내부 이미지.
- JPG / JPEG / PNG / WEBP: 일반 이미지.
- PPT, HWP/HWPX, DOCX, TXT는 수집하지 않습니다. OCR과 문서 페이지 전체 이미지화는 지원하지 않습니다.
- 파일명은 URL 디코딩 후 NFC로 정규화합니다. 실제 파일 경로는 변경하지 않습니다.
- SQLite는 임시 DB, FAISS는 메모리 인덱스입니다. 재실행 시 다시 분석하며 GUI 재분석은 새 서비스를 만듭니다. 저장·복원 함수는 앱에 연결하지 않았습니다.
- 샘플은 기존 `assets/images`, `test_assets`, `test.sample` 경로를 유지합니다. `encode_with_crops()`는 기본 분석에서 사용하지 않습니다.

## 코드와 검증

`app.py`가 객체를 만들고 `connection/service.py`가 분석·검색을 연결합니다. `gui/window.py`가 화면과 작업 큐를 담당합니다. [담당 범위](docs/CODE_OWNERSHIP.md), [통합 변경 정리](docs/INTEGRATION_2026-11-20.md), [활동 기록](docs/ACTIVITY_LOG.md)을 참고하세요.

```powershell
python -B -m unittest discover -s tests -v
```

2026-11-20 통합 테스트 66개가 통과했습니다. 모델 출력 대역과 실제 로더·SQLite·FAISS를 사용합니다. 이전 RRF 통합 단계에서는 캐시된 실제 OpenCLIP 모델로 PPTX 1개·PNG 1개의 분석과 통합 검색을 확인했습니다. 전체 데이터 검색 품질 평가와 GUI 육안 확인은 하지 않았습니다. Windows FAISS 저장 테스트는 한글 임시 경로 문제를 피하도록 영문 TEMP/TMP 경로를 사용했습니다.
