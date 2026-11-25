# 원본 main 방식 직접 비교용

2026-11-25에 만든 별도 폴더입니다. 기존 document-search-demo-v3는 변경하지 않았습니다.

## 기준과 변경 범위

- 원본 main 0bf2242(2026-11-25 확인)의 Python 소스를 그대로 유지합니다. 처음 fc2a48d에서 만든 사본에 최신 팀원 변경도 반영했습니다. 기존 v3 폴더는 이동하지 않았습니다. 이 폴더는 원본 저장소의 compare 브랜치 게시용으로 별도 Git 저장소를 구성합니다.
- 최신 main에 팀원의 import 경로 수정과 사용하지 않는 FAISS search_combined 삭제가 반영돼 있습니다. 이 폴더의 모든 Python 파일은 main 0bf2242와 바이트 단위로 같으며, 서비스·본문 어댑터·모델·검색 정렬·GUI를 AI가 별도로 수정하지 않았습니다.
- main에 빠진 deepl·python-dotenv 의존성만 requirements.txt에 보완했습니다.
- 개인 .env 제외 규칙을 추가했습니다. 현재 PC에서는 개인 .env를 로컬에만 보관합니다. 사용자는 실제 키 게시 대신 키 없는 설정 예시 포함을 선택했습니다. Git에는 .env.example만 포함하고 개인 .env와 키 내용은 포함하지 않습니다. 이 폴더를 다른 사람에게 전달할 때 .env는 제외하세요.
- 새 .venv나 모델 사본은 만들지 않았습니다. 이 PC에서는 이미 라이브러리가 설치된 v2 Python 환경을 공유합니다. 실행되는 app.py는 이 비교 폴더의 파일입니다.

## main 방식의 검색어 처리

본문은 서비스의 영→한 함수를 거친 뒤 상속한 encode_query에서 한→영 함수도 거칩니다. 한국어 입력은 영어로, 영어 입력은 영→한→영 처리 후 ko-sroberta로 비교합니다. 원문 본문 자체를 번역하는 것은 아닙니다. 번역 실패 시 원문으로 대체합니다.

이미지는 한→영 번역 후 OpenCLIP으로 비교합니다. 이미지 경로는 현재 v3와 같습니다. GUI 환산 일치도는 원본 0.32 이상을 모두 100%로 표시하며 정확도·확률이 아닙니다.

## 이 PC에서 실행

아래 명령은 PowerShell 터미널에 입력합니다. app.py 소스에 붙여 넣지 마세요.

```powershell
Set-Location C:\Capstone\document-search-main-compare
& C:\Capstone\document-search-demo-v2\.venv314\Scripts\python.exe app.py --gui
```

현재 통합본은 별도로 다음과 같이 실행합니다.

```powershell
Set-Location C:\Capstone\document-search-demo-v3
& C:\Capstone\document-search-demo-v2\.venv314\Scripts\python.exe app.py --gui
```

두 방식 모두 같은 분석 폴더 C:\Capstone\document-search-demo-v3\test_esset을 선택하고 같은 검색 모드와 검색어로 비교하세요. 비교 폴더에도 당시 추적 샘플이 있지만 같은 경로를 선택하면 파일 차이를 피할 수 있습니다. 앱을 각각 실행하면 모델도 각각 로딩하므로 메모리가 부족하면 한 창씩 비교하세요.

## 다른 Windows PC

Python과 Tkinter를 준비합니다. GitHub에서 받는 경우 다음 명령으로 compare 브랜치를 받고, 이미 받은 폴더가 있으면 그 폴더를 터미널 작업 위치로 선택하세요.

```powershell
git clone --branch compare --single-branch https://github.com/nohminju/local_file_search.git document-search-main-compare
Set-Location .\document-search-main-compare
Copy-Item .env.example .env
```

복사한 .env를 편집해 DEEPL_API_KEY= 뒤에 본인 키를 입력하고 저장합니다. 명령은 소스 파일이 아니라 터미널에 입력하세요. 다음은 최초 한 번 설치와 실행입니다.

```powershell
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe app.py --gui
```

기존 검증 환경은 Python 3.14입니다. 새 PC 전체 설치·GUI 육안 실행은 별도 확인하지 않았습니다. 원본 main의 과거 테스트를 현재 통합본의 96개 통과 결과와 동일하게 해석하지 마세요. 이 폴더의 검증 결과는 아래에 추가합니다.

검증: 이 비교 폴더에서 app import·전체 Python 구문 검사 및 API 없는 대역을 사용한 본문 영→한→영/이미지 한→영 호출 경로 확인을 통과했습니다. 전체 회귀·실모델 분석·GUI 육안 실행을 새로 수행한 것은 아닙니다.


## 실제 비교 실험과의 관계

실제 검색 수치는 main fc2a48d 방식과 v3 88429d0을 같은 인덱스에서 비교한 결과입니다. 이후 main 0bf2242는 import 수정과 앱에서 사용하지 않는 FAISS RRF 보조 함수 삭제만 포함하며 본문·이미지 개별 검색과 서비스 번역 흐름은 같습니다. 이 새 폴더 전체에서 실제 모델 비교를 다시 실행한 것으로 표현하지 않습니다.
