# Document Search Demo

기준: 2026-10-30 · 작업 폴더: `C:\Capstone\document-search-demo-v1`

팀원 로더·인코더·DB를 연결한 로컬 문서 검색 데모다. PDF·PPTX의 추출 가능한 본문을 문장으로 검색한다.
이미지 파일과 PPTX 내부 이미지는 **이미지 유사도 검색(임시 구현)**으로 검색한다. 팀원 인코더의 벡터를 임시 코사인 비교 함수에 전달한다.

## 실행

PowerShell에서 실행한다.

```powershell
cd C:\Capstone\document-search-demo-v1
python -m pip install -r requirements.txt
python app.py --gui
```

이미 설치했다면 설치 명령은 생략한다. GUI에서 **폴더 선택 → 분석 → 검색 문장 입력 → 검색 대상 선택 → 검색** 순서로 사용한다. 대상은 문서 본문 또는 이미지 유사도 검색(임시 구현)이다.
콘솔은 `python app.py`로 실행한다. 폴더 경로를 입력하고 분석 후 검색 문장을 입력한다. 다음 입력에서 i를 누르면 임시 이미지 검색, Enter를 누르면 본문 검색이다. 검색 문장을 비우면 종료한다.

`python` 실행 시 `Python`만 출력되면 Windows 실행 별칭 대신 설치된 `python.exe`의 전체 경로로 실행한다. VS Code에서도 같은 인터프리터를 선택한다.

첫 실행에는 모델 다운로드가 필요할 수 있다. GUI는 모델 준비·분석 중 잠시 응답을 기다려야 한다.
본문 검색은 글자가 추출되는 PDF·PPTX, 임시 이미지 검색은 JPG·PNG 등 이미지나 그림이 들어 있는 PPTX로 확인한다.

## 현재 범위

- TXT·코드·DOCX·옛 PPT·HWP/HWPX는 현재 로더가 수집하지 않는다.
- 스캔 PDF의 OCR과 PDF 페이지 이미지화는 없다.
- DB에는 파일 정보가 저장된다. 본문·이미지 벡터는 메모리에 있으며 재실행하면 다시 분석한다.
- 이미지 비교 코드는 `similarity/temporary_image_similarity.py`이며 담당자 구현을 받으면 교체한다. 본문·이미지 점수는 합치지 않는다.
- 검색 결과는 파일 이름·경로·유사도 점수다. 점수는 정확도나 확률이 아니다.
- 기본 결과는 상위 5개다. 고양이 사진 3개를 확인할 때는 `assets\images` 폴더만 선택해 분석한다.

[문서 목록](docs/README.md) · 코드 공부 자료는 로컬 `study` 폴더에 있으며 GitHub 백업에서는 제외한다.
