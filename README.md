# Local File Search

PDF·PPTX의 추출 본문과 내부 이미지, 일반 이미지를 검색합니다. 현재 로컬 기준은 `document-demo-v3`의 팀원 커밋 `f9a095f`와 그 위에 적용한 통합 변경입니다.

## 1. main에서 받은 팀원 변경

| 담당·파일 | main에서 받은 변경 |
|---|---|
| 김하은 · connection/translator.py | Google을 DeepL 양방향 번역으로 교체. 한→영·영→한 함수, .env API 키 로딩, lru_cache 캐시, 단독 영단어가 그대로 반환될 때 관사를 붙여 재시도 추가 |
| 김하은 · connection/service.py | 본문용 영→한, 이미지용 한→영 번역 연결. 원본 유사도 최댓값 정렬은 유지 |
| 윤소영(duoloo) · similarity/document_embedder.py | 검색어 인코딩 전 한→영 번역과 모델 입력 길이 속성 추가 |
| 윤소영(duoloo) · gui/window.py | 원본 점수만 표시하던 결과 카드에 환산 일치도 %와 원본 유사도를 함께 표시 |
| 노민주 · database/faiss.py | 개별 검색의 min_score 인자 제거, 하한·RRF 방식의 search_combined 보조 함수 추가, 벡터 배열 차원 검사 보완 |
| 노민주 · database/manager.py | DB 처리 설명·주석 보강. 이번 차이에서 실행 동작 변경은 없음 |

FAISS 저장·복원은 원래 있던 기능입니다. 이번 변경 전체를 신규 기능으로 설명하지 않습니다. GUI 환산식과 DeepL 번역기·FAISS 알고리즘은 팀원 변경을 그대로 수용했습니다.

`document-demo-v3`에서 추가로 받은 변경은 FAISS 분리입니다. 팀원은 문서용 `DocumentFaiss`와 이미지용 `ImageFaiss`에 벡터 추가·검색·저장·복원을 나눴습니다. 로컬의 `database/faiss.py`는 기존 호출부가 이 두 클래스로 인덱싱·검색하도록 연결하고 이전 통합 저장 형식도 읽습니다.

## 2. 로컬 통합 시 수정한 것

| 파일·영역 | 로컬 통합 시 수정 |
|---|---|
| similarity/document_embedder.py | 팀원 코드의 번역기 import를 실제 connection.translator 경로로 수정. 팀원 파일의 추가 수정은 이것뿐 |
| app.py | 이미지 검색에 한→영 번역기를 전달하고 본문 검색어는 팀원 임베더에 그대로 전달 |
| connection/service.py | 기존 미커밋 번역 작업과 main의 충돌 해결. 주입받은 함수를 경로별로 호출하고 예외·빈 값·잘못된 반환이면 원문 사용 |
| connection/sentence_document_embedder.py | 팀원 encode_query를 상속해 한국어 검색어를 영어로 번역하고 ko-sroberta로 인코딩 |
| requirements.txt·.gitignore | deepl·python-dotenv 의존성과 .env 제외 규칙 반영 |
| 테스트·비교 도구·문서 | 번역 방향·실패 대체·중복 번역 방지 검증, 변경된 FAISS API·GUI 표시 반영. 과거 Google 평가와 현재 DeepL 연결 구분 |

**본문 번역을 바로잡은 이유**

팀원 코드에서 한국어 검색어를 영어로 바꾸는 동작은 의도한 동작이었습니다. 다만 당시 main에 영어를 입력하면 서비스의 영→한과 임베더의 한→영이 연달아 실행됐습니다. 초기 통합에서는 AI가 한국어 검색어를 보존해야 한다고 잘못 판단해 임베더의 번역을 막았습니다. 이 판단은 Git 병합 충돌 해결과 별개였습니다. 현재는 서비스가 본문 검색어를 그대로 넘기고 팀원 임베더가 처리해, `고양이`는 영어로 한 번 번역하고 `cat`은 그대로 인코딩합니다.

기존 본문 어댑터·긴 본문 분할·이미지 모델 공유는 이번에 새로 만든 기능이 아니라 유지한 연결 구조입니다. 이후 실행 오류 점검에서는 app.py 첫 줄에 들어가 있던 터미널 명령 `python app.py --gui`만 제거했고 구문 검사와 앱 import가 통과했습니다. 팀원 GUI 계산식은 추가 수정하지 않았습니다.

기존 미커밋 작업은 stash 백업으로 보존했습니다. 현재 통합 수정과 비교 보고서는 사용자 저장소의 document-demo-v3 브랜치에서 관리합니다. 원본 방식은 별도 compare 브랜치에서 비교할 수 있습니다. **현재 GitHub main만 내려받으면 이 로컬 통합본과 같지 않습니다.** 다른 사람이 같은 상태를 실행하려면 현재 수정본이 포함된 프로젝트 폴더를 전달받아야 합니다. 다른 PC에는 가상환경을 복사하지 말고 아래 절차로 새로 만드세요.

<a id="분석과-검색-흐름"></a>

## 3. 현재 검색 진행 방식

### 폴더 분석

1. 선택 폴더와 하위 폴더에서 PDF·PPTX·JPG/JPEG/PNG/WEBP를 수집합니다.
2. PDF/PPTX의 추출 가능한 본문과 내부 이미지, 일반 이미지 파일을 읽습니다.
3. 긴 본문은 현재 모델 기준 126토큰·32토큰 겹침으로 나눕니다. 같은 본문은 한 번 인코딩하고 파일·페이지 연결은 유지합니다.
4. 본문은 ko-sroberta 768차원, 이미지는 OpenCLIP 512차원으로 벡터화합니다.
5. 본문·이미지 벡터는 별도 FAISS 인덱스에, 파일 정보는 임시 SQLite DB에 보관합니다.

| 대상 | 모델 |
|---|---|
| 본문·본문 검색어 | jhgan/ko-sroberta-multitask |
| 이미지·이미지 검색어 | OpenCLIP xlm-roberta-base-ViT-B-32 / laion5b_s13b_b90k |

이미지와 이미지 검색어는 모델 객체를 공유하고 본문 모델은 별도로 로딩합니다.

### 검색어 처리와 결과 정렬

| 모드 | 진행 |
|---|---|
| 본문 검색 | 한국어→영어 번역 → ko-sroberta 인코딩 → 본문 벡터와 코사인 유사도 비교 |
| 이미지 검색 | 한국어→영어 번역 → OpenCLIP 인코딩 → 이미지 벡터와 코사인 유사도 비교 |
| 통합검색 | 두 경로를 실행 → 일반 이미지는 이미지 최고 점수, PDF/PPTX는 본문·내부 이미지 최고 점수 중 큰 값 선택 |

예를 들어 본문·이미지 검색 모두 `고양이`를 입력하면 한→영 번역 결과를 사용하고, `cat`은 API 호출 없이 그대로 사용합니다. 파일에서 추출한 본문은 원문으로 인덱싱합니다. 번역기는 ASCII 여부로 분기하며 실패 시 원문을 사용합니다. 개별 검색은 파일별 최고 점수를 사용합니다. 통합검색은 내용 해시로 중복을 묶고 동점은 경로순이며 기본 5개를 표시합니다.

앱은 원본 점수로 정렬합니다. 파일명은 결과 표시·열기·DB 연결에 사용합니다. GUI에서 분석한 벡터는 메모리에 보관하며 다음 실행 때 다시 분석합니다.

### GUI 일치도와 제약

GUI의 일치도는 팀원이 추가한 아래 환산값을 0~100%로 제한한 표시입니다.

```text
표시값 = (원본 점수 - 0.15) / (0.32 - 0.15) × 100
```

**0.32 이상은 모두 100%로 표시됩니다. 정확도·확률이 아니며 정렬에는 원본 점수를 사용합니다.** 두 모델의 원본 점수도 같은 신뢰도로 보정된 값이 아니므로 통합 순위에 무관한 파일이 섞일 수 있습니다.

OCR·페이지 전체 이미지화는 지원하지 않습니다. 그림으로 된 글은 본문으로 검색되지 않으며 PPT·HWP/HWPX·DOCX·TXT/MD도 수집하지 않습니다. 앱을 다시 실행하면 다시 분석해야 합니다. 번역 실패 후 원문 반환도 캐시에 남을 수 있어 설정·네트워크를 고친 뒤 재시작이 필요할 수 있습니다.

## 4. GUI 설치와 실행

### 다른 사람의 Windows PC — 최초 한 번 준비

아래 명령은 **VS Code의 터미널 → 새 터미널 → PowerShell**에서 실행합니다. app.py 파일 안에 입력하지 마세요.

1. Python과 Tkinter, Python 실행 명령을 준비합니다. 기존 통합 검증은 Python 3.14에서 했습니다. 새 PC 전체 설치 검증은 아직 하지 않았습니다.
2. 현재 수정본이 포함된 프로젝트 폴더를 전달받고 VS Code에서 그 폴더를 엽니다. app.py와 requirements.txt가 보이는 위치가 프로젝트 루트입니다. 개인 .env와 다른 사람의 .venv는 공유하지 않습니다.
3. 터미널에서 현재 위치를 확인하고 가상환경·의존성을 준비합니다.

```powershell
# app.py와 requirements.txt가 나오는 위치인지 확인
Get-Location
Get-ChildItem app.py, requirements.txt

# 최초 한 번: 이 PC 전용 가상환경 생성과 라이브러리 설치
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# GUI 실행
& .\.venv\Scripts\python.exe app.py --gui
```

`py`가 없지만 정상 설치된 `python` 명령이 있다면 첫 명령은 `python -m venv .venv`로 바꿀 수 있습니다. 둘 다 없다면 Python 설치·실행 경로 설정이 필요합니다. 가상환경 활성화 명령 없이 해당 Python을 직접 실행하므로 PowerShell 활성화 스크립트 정책을 바꿀 필요는 없습니다.

### 다음 실행부터

프로젝트 폴더를 열고 터미널에서 아래 명령만 실행합니다.

```powershell
& .\.venv\Scripts\python.exe app.py --gui
```

VS Code의 `Python: Select Interpreter`에서도 이 프로젝트의 `.venv\Scripts\python.exe`를 선택하면 편합니다. `python app.py --gui`는 터미널의 python이 이 환경을 가리킬 때 같은 방식으로 동작합니다. 처음에는 위처럼 경로를 명시하면 환경 혼동을 줄일 수 있습니다.

### DeepL 번역 설정

번역을 쓰려면 프로젝트 루트에 `.env` 파일을 만들고 자신의 API 키를 입력하거나 같은 이름의 환경 변수를 설정합니다.

```dotenv
DEEPL_API_KEY=본인의_API_키
```

키가 없거나 요청에 실패해도 원문 검색으로 대체합니다. 실제 번역 요청은 검색어를 외부 DeepL로 전송하므로 인터넷과 API 사용 가능 상태가 필요합니다. 실제 키는 Git에 포함하지 않습니다.

### 현재 작업 PC의 기존 환경으로 실행

아래 경로는 이 PC에만 해당합니다. 다른 사람은 위 절차로 자신의 .venv를 만드세요.

```powershell
Set-Location C:\Capstone\document-search-demo-v3
& C:\Capstone\document-search-demo-v2\.venv314\Scripts\python.exe app.py --gui
```

창에서 **폴더 선택 → 분석 완료 → 검색어 입력 → 검색** 순서로 사용합니다. 통합검색·이미지 검색·본문 검색을 선택할 수 있습니다. GUI가 뜨기 전 라이브러리를 불러오며 출력 없이 기다리는 구간이 있을 수 있습니다. 이 PC의 앱 import 확인은 약 16초였으며 다른 PC의 소요 시간을 보장하는 수치는 아닙니다. 첫 분석에는 모델 다운로드와 파일 분석 시간이 추가될 수 있습니다. 코드 변경 전 창은 닫고 다시 실행하세요.

### 실행이 안 될 때

| 증상 | 확인할 부분 |
|---|---|
| python 실행 후 Python만 출력되고 종료 | 이 PC에서 확인한 Windows 실행 별칭 증상. 실제 .venv Python 경로를 지정해 실행 |
| app.py를 찾을 수 없음 | 터미널 위치를 app.py가 있는 프로젝트 폴더로 변경 |
| ModuleNotFoundError | 실행에 쓰는 같은 .venv Python으로 requirements.txt 설치 |
| tkinter 모듈·Tk 초기화 오류 | 설치한 Python에 Tkinter/Tk가 있는지 확인. pip requirements만으로 해결되는 항목이 아님 |
| 첫 줄의 python app.py --gui에서 SyntaxError | 실행 명령이 소스에 들어갔는지 확인. 명령은 터미널에 입력 |
| 출력 없이 기다림 | 라이브러리 초기 로딩 중인지 확인. 오류가 나오면 터미널 내용 확인 |

콘솔 실행은 같은 Python으로 `app.py`만 실행하면 됩니다.

## 검증과 추가 문서

[원본 main과 통합본의 실제 검색 비교](docs/MAIN_COMPARISON_2026-11-25.md)에서 코드 차이·전체 질의 순위·원본 점수를 확인할 수 있습니다. 원본 방식 직접 실행은 [compare 브랜치](https://github.com/nohminju/local_file_search/tree/compare)의 안내를 참고하세요.

분리된 FAISS와 팀원 검색어 인코더를 연결한 로컬 버전에서 회귀 테스트 96개가 통과했습니다(6.500초). 이 버전의 실제 파일 검색 순위는 아직 재측정하지 않았습니다. 이전의 38파일·32질의 점수는 본문을 한국어로 검색하던 통합본과 당시 main을 비교한 결과입니다. [당시 비교 보고서](docs/MAIN_COMPARISON_2026-11-25.md)

가상환경을 준비한 PC에서 회귀 테스트는 다음과 같습니다.

```powershell
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Windows FAISS 저장/복원 테스트에서 한글 사용자 임시 경로를 열지 못한 오류를 확인했고 영문 임시 경로에서는 통과했습니다. 현재 앱은 인덱스를 파일에 저장하지 않습니다. 테스트가 같은 경로 오류로 실패하면 영문 경로의 임시 폴더를 지정할 수 있습니다. 아래 환경 변수는 현재 터미널 프로세스에 적용됩니다.

```powershell
# 프로젝트를 둔 전체 경로에 한글이 없는 경우의 예
New-Item -ItemType Directory -Force .integration-tmp\test-temp | Out-Null
$env:TEMP = (Resolve-Path .integration-tmp\test-temp).Path
$env:TMP = $env:TEMP
& .\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

[담당·변경 구분](docs/CODE_OWNERSHIP.md), [검색 동작·과설계 점검·개선 후보](docs/SEARCH_BEHAVIOR.md), [문서 안내](docs/README.md), [활동 기록](docs/ACTIVITY_LOG.md)을 참고하세요. study/·docs/archive/·docs/records/는 로컬 보관 자료로 Git에서 제외하며 test_esset/은 제외하지 않습니다. 파일 이동·이름 변경은 없습니다.
