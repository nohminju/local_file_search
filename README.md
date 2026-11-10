# Document Search Demo (v2)

팀원 로더·인코더·DB·FAISS를 연결한 로컬 문서 검색 데모다. PDF·PPTX 본문이나 이미지 내용을 문장으로 검색한다.

현재 브랜치는 `document-demo-v2`이며, 2026-11-10에 `origin/document-demo-v2`의 `edb186a`까지 반영했다(`origin/main`의 `ea5d58c` 포함). 팀원 SQLite 연결 종료·FAISS 검증 변경을 반영하고 입력 개수 검사와 복원 실패 시 상태 유지를 보완했다. 폴더 내부 구조는 유지한다.

## 실행

```powershell
cd C:\Capstone\document-search-demo-v2
python -m pip install -r requirements.txt
python app.py --gui
```

GUI는 **폴더 선택 → 분석 → 검색어 입력 → 문서/이미지 선택 → 검색** 순서다. 결과의 열기 버튼이나 더블클릭으로 파일을 연다. 분석·검색은 작업 스레드에서 수행한다.

콘솔은 `python app.py`로 실행한다. 분석할 폴더와 검색어를 입력한 뒤 이미지 검색은 i, 본문 검색은 Enter를 선택한다. 검색어를 비우면 종료한다.

첫 실행에는 모델 다운로드가 필요할 수 있다. 설치와 실행에 같은 Python 환경을 사용한다. `python` 실행 시 `Python`만 출력되면 설치된 python.exe의 전체 경로로 실행하고 VS Code에서도 같은 인터프리터를 선택한다.

## 분석과 검색 흐름

1. `app.build_service()`가 로더·인코더·FAISS·SQLite 저장소를 만들고 `DocumentSearch`에 전달한다.
2. `DocumentScanner`가 지원 파일을 모으고 `DocumentLoader`가 본문·페이지·이미지가 담긴 `DocumentChunk`를 반환한다.
3. 비어 있지 않은 본문은 ko-SRoBERTa, 이미지는 OpenCLIP으로 인코딩해 별도 FAISS 인덱스에 넣는다. 문서 이미지도 같은 이미지 인코더를 사용한다.
4. 파일 정보는 `DocumentInfo`로 만들어 SQLite에 저장하고 경로를 파일 ID와 연결한다. 파일별 OSError는 실패 목록에 넣고 다른 파일은 계속 분석한다. 모델·FAISS·DB 오류는 호출자에게 전달한다.
5. 본문 검색어는 본문 모델로, 이미지 검색어는 이미지 모델을 공유하는 OpenCLIP 텍스트 인코더로 바꾼다. 이미지 검색어의 `(1, 512)` 배열을 그대로 FAISS에 전달한다.
6. FAISS가 정규화한 벡터의 내적 점수순으로 청크를 반환한다. 서비스는 결과 dict의 파일 경로로 DB 정보를 찾고 같은 파일은 최고 점수 하나만 남긴다.

`search(query, top_k=5, mode='documents')`의 mode는 `documents` 또는 `images`다. `seen`으로 파일 중복을 제거한 뒤 top_k개를 채우면 멈춘다. 반환값은 `(DocumentInfo, 점수)` 목록이다. 본문·이미지 점수는 합치지 않으며 점수는 정확도나 확률이 아니다.

`analyze(folder)`는 `(저장한 파일 목록, 읽기 실패 목록)`을 반환한다. 같은 서비스로 재분석하지 않으며 GUI에서 다시 분석하면 새 서비스를 만든다. 기존 `DocumentEmbedder.search()`는 현재 앱에서 호출하지 않는다.

## 지원 범위

| 파일 | 현재 동작 |
|---|---|
| PDF | 추출 가능한 본문 검색, 내부 이미지 검색(가로·세로 모두 100px 이상) |
| PPTX | 글·표 본문 검색, 슬라이드의 여러 내부 이미지를 각각 검색 |
| JPG / JPEG / PNG / WEBP | 이미지 읽기·인코딩·검색 |
| PPT / HWP / HWPX / TXT / 코드 / DOCX / 노트북 | 현재 스캐너가 수집하지 않음 |

PDF 페이지 전체 이미지화·OCR은 없다. PPTX의 여러 그림 누락과 PDF 이미지 열거 예외 처리는 팀원 업데이트로 해결됐다. SQLite 연결은 작업이 끝나면 명시적으로 닫는다.

## 데이터

- `DocumentChunk`는 파일 경로·페이지·본문·PIL 이미지를 담는다. `DocumentInfo`는 파일 경로·이름·확장자·크기·SHA-256·생성/수정 시각·DB ID를 담는다. 시각은 UTC 문자열이다.
- `database/manager.py`의 Repository가 `document_metadata` 테이블에 저장·조회한다. 같은 경로를 다시 저장하면 같은 ID를 반환하며 정보는 갱신하고 created_at은 유지한다.
- 본문 768차원·이미지 512차원 벡터와 청크 메타데이터는 별도 FAISS 인덱스에 둔다. SQLite에는 파일 정보를 저장한다.
- 현재 앱은 임시 DB와 메모리 인덱스를 사용하므로 재실행하면 다시 분석한다. FAISS save/load 함수는 있지만 앱에서는 호출하지 않는다. 저장 시 오래된 인덱스 파일을 정리하고, 복원 시 파일 존재 여부·벡터 수·차원을 검증한다. 검증 실패 시 기존 검색 상태를 유지한다. 앱에 복원을 연결하려면 SQLite 파일 정보와 서비스의 경로별 파일 ID도 함께 복원해야 한다.
- 관련 없는 파일도 상위 결과에 나올 수 있다. 실제 자료로 검색 품질과 제외 기준을 평가해야 한다. 사용자가 `타입스크립트`와 `typescript`의 검색 결과 차이를 보고했다. 대상 문서와 실제 순위·점수는 아직 확보하지 않아 원인이나 개선 효과는 검증하지 않았다. 같은 조건에서 재현한 뒤 기술 용어 별칭 확장이나 키워드·벡터 검색 순위 결합을 비교할 수 있다.

## 사용 모델

이미지 검색에는 **LAION-5B로 사전학습된 ViT-B/32–XLM-RoBERTa Base 기반 CLIP 모델**을 OpenCLIP 라이브러리로 불러와 사용한다. 이미지 인코더는 ViT-B/32, 텍스트 인코더는 XLM-RoBERTa Base다. [공식 모델 설명](https://huggingface.co/laion/CLIP-ViT-B-32-xlm-roberta-base-laion5B-s13B-b90k)

| 용도 | 모델 | 벡터 차원 |
|---|---|---|
| 문서 본문·본문 검색어 | `jhgan/ko-sroberta-multitask` (ko-SRoBERTa) | 768 |
| 이미지·이미지 검색어 | OpenCLIP `xlm-roberta-base-ViT-B-32`, 가중치 `laion5b_s13b_b90k` | 512 |

본문 모델은 Sentence Transformers로 불러온다. 이미지와 이미지 검색어 인코더는 같은 OpenCLIP 모델 객체를 공유하며, 문서에서 추출한 이미지도 이 모델을 사용한다. FAISS는 만들어진 벡터의 유사도 검색을 담당한다. 모델 설정은 `app.py`, `similarity/document_embedder.py`, `file_encoder/image_encoder.py`, `query_encoder/text_encoder.py`에서 확인할 수 있다.

## 이미지 모델 비교

2026-11-06에 같은 이미지 7장·한국어 검색어 20개로 비교했다. 정답이 있는 18개는 두 모델 모두 1위 정답 18/18이었다. CPU·FP32·4스레드·3회 측정에서 기존/SigLIP 2의 이미지 7장 인코딩 중앙값은 각각 0.490/2.240초, 검색어 처리 중앙값은 65.2/115.6ms였다. 다운로드·준비·파일 읽기·DB·GUI 시간은 제외했다.

이 소규모 자료에서는 품질 우위를 확인하지 못했고 기존 모델이 빨랐다. 앱 모델은 유지한다. [재실행 코드](tests/image_model_comparison.py) · [조건·전체 순위·원시 측정](tests/image_model_comparison_results.json) · [활동 기록](docs/ACTIVITY_LOG.md). 재실행에는 로컬 study 이미지가 필요하다.

## 검증

```powershell
python -B -m unittest discover -s tests -v
```

2026-11-10에 전체 37개 테스트가 통과했다. 실제 로더·SQLite·FAISS와 모델 출력 대역을 사용했다. FAISS 입력 불일치, 저장·복원 검색 결과, 오래된 인덱스 삭제, 잘못된 복원 시 기존 상태 유지를 검증한다. 실제 모델 검색 품질 평가와 GUI 시각 검증은 이번 실행에 포함하지 않았다. 자세한 실행 결과는 활동 기록에 있다.

## 관련 기록

- [담당 영역·파일 역할·원본 커밋](docs/CODE_OWNERSHIP.md)
- [사용자 판단과 AI 작업을 구분한 활동 기록](docs/ACTIVITY_LOG.md)

로컬 `study`는 GitHub 백업에서 제외한다. [공부 자료 안내](study/README.md)의 전체 코드 사본·노트북은 2026-11-03 당시 자료로 현재 실행 코드와 다르다.
