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

실제 샘플 비교 후 본문과 이미지를 다른 모델로 검색하도록 개선했습니다.

| 검색 대상 | 모델 | 벡터 차원 |
|---|---|---:|
| 본문·본문 검색어 | `jhgan/ko-sroberta-multitask` | 768 |
| 이미지·이미지 검색어 | OpenCLIP `xlm-roberta-base-ViT-B-32` / `laion5b_s13b_b90k` | 512 |

이미지와 이미지 검색어만 모델 객체를 공유합니다. `query_encoder/text_encoder.py`는 이미지 검색어용이고 본문 검색어는 `SentenceDocumentEmbedder.encode_query()`를 호출합니다. 본문·이미지는 별도 FAISS 인덱스를 사용합니다. `build_service()`는 현재 두 모델을 조립하며 실험용 모델 전환 분기는 제거했습니다.

이미지는 배치로 인코딩하고 같은 본문은 한 번만 인코딩한 뒤 원래 파일·페이지 메타데이터에 연결합니다. 본문은 기본 8개씩 배치 처리합니다.

## 검색 결과

- GUI의 **통합검색 / 이미지 검색 / 본문 검색**을 선택합니다.
- 일반 이미지는 이미지 원본 유사도만 사용합니다. PDF/PPTX는 추출 본문·내부 이미지의 최고 원본 유사도 중 더 높은 값을 사용합니다.
- 통합검색은 그 점수의 내림차순입니다. **파일명 검색·하한·합산·기준 초과 비율 보정·RRF·재정렬 모델을 사용하지 않습니다.**
- 결과 카드에는 선택한 본문/이미지 원본 유사도를 표시합니다. 두 모델의 점수는 같은 신뢰도로 보정된 확률이 아닙니다.
- 같은 내용은 SHA-256으로 묶고 동점은 경로로 정합니다. 기본 최대 5개이며 유한한 0·음수 점수도 반환합니다. “관련 결과 없음”을 점수로 판단하지 않습니다.
- 파일명은 결과 표시·파일 열기 용도로만 보관합니다. 인코더·정렬 입력에 포함하지 않습니다.

본문은 모델 길이에 맞춰 126토큰씩 32토큰 겹침으로 나눕니다. 추출 글은 별도 TXT가 아닌 메모리의 DocumentChunk.text에 전달됩니다. PDF의 실제 텍스트와 PPTX의 글·표는 OCR 없이 검색하지만, 그림으로 된 글은 현재 OCR로 읽지 않습니다.

## 지원 범위와 제약

- PDF: 추출 가능한 본문과 가로·세로 모두 100px 이상인 내부 이미지.
- PPTX: 글·표의 본문과 내부 이미지.
- JPG / JPEG / PNG / WEBP: 일반 이미지.
- PPT, HWP/HWPX, DOCX, TXT는 수집하지 않습니다. OCR과 문서 페이지 전체 이미지화는 지원하지 않습니다.
- 로더의 표시용 파일명은 URL 디코딩 후 NFC로 정규화합니다. 파일명 검색은 하지 않고 실제 파일 경로도 변경하지 않습니다.
- SQLite는 임시 DB, FAISS는 메모리 인덱스입니다. 재실행 시 다시 분석하며 GUI 재분석은 새 서비스를 만듭니다. 저장·복원 함수는 앱에 연결하지 않았습니다.
- 샘플은 `test_esset` 폴더에 통합했습니다. PPT 파일도 보관하지만 현재 분석 대상에서는 제외합니다. `encode_with_crops()`는 기본 분석에서 사용하지 않습니다.

## 코드와 검증

오늘 통합 중 확인한 유사도 문제·본문 추출 흐름과 이번 주 팀원 변경은 [통합 문제·연구일지 초안](docs/INTEGRATION_NOTES_2026-11-20.md)에 정리했습니다.

`app.py`가 객체를 만들고 `connection/service.py`가 분석·검색을 연결합니다. `gui/window.py`가 화면과 작업 큐를 담당합니다. [담당 범위](docs/CODE_OWNERSHIP.md), [문서 안내](docs/README.md), [활동 기록](docs/ACTIVITY_LOG.md)을 참고하세요.

```powershell
python -B -m unittest discover -s tests -v
```

2026-11-20 구조 정리 후 회귀 테스트 80개가 통과했습니다. 실제 38개 샘플·질의 16개에서 원본 유사도 규칙과 파일명 제외를 확인했습니다. 고양이 3개·데이터베이스·동적계획법·딥러닝은 1위였지만 피자 8위·비행기 12위·페르소나 주제 질의 12위 등 남은 오류가 있습니다. 분석 후 질의별 검색은 이번 실행에서 약 0.43~0.55초였습니다. [현재 정렬 규칙·전후 순위](docs/SEARCH_BEHAVIOR.md)와 [원시 점수](docs/records/2026-11-20/RAW_SIMILARITY_COMPARISON_2026-11-20.json)를 참고하세요. 고정된 로컬 표본의 결과이며 일반 정확도를 보장하지 않습니다.

무거운 Qwen 재정렬 모델은 사용자 요청으로 약 4.27GB 삭제했고 앱 연결도 제거했습니다. 추가 모델 준비 없이 `python app.py --gui`로 실행합니다. 이미 열린 GUI는 재시작·재분석해야 최신 규칙이 적용됩니다.

과거 설명(`docs/archive/`)과 원시 결과(`docs/records/`)는 로컬 보관 자료이며 Git에서 제외합니다. 해당 자료 링크는 자료가 있는 PC에서만 열립니다. 현재 동작과 주요 검증 결과는 [검색 안내](docs/SEARCH_BEHAVIOR.md)에 남겼습니다.
