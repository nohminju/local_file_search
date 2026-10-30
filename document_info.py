"""팀원 DB의 import 경로를 맞춘다. 새 자료형을 만드는 파일은 아니다."""
# 실제 DocumentInfo는 database/db_info.py에 한 번만 정의되어 있다.
# db_manager.py가 'from document_info import DocumentInfo'로 가져오므로
# 여기서 같은 클래스를 전달한다. 이 파일을 지우면 그 import가 실패한다.
# 팀원 DB의 import를 정식 경로로 고칠 때 이 연결 파일도 없앨 수 있다.
from database.db_info import DocumentInfo
