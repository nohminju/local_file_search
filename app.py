"""실제 팀원 로더·인코더·DB를 조립하여 실행한다."""
from pathlib import Path
from tempfile import TemporaryDirectory

from file_loader.document_loader import DocumentLoader
from file_encoder.image_encoder import ImageEncoder
from file_encoder.document_encoder import DocumentEncoder
from similarity.document_embedder import DocumentEmbedder
from query_encoder.text_encoder import KoreanTextEncoder
from database.db_manager import Repository
from connection.service import DocumentSearch


def build_service():
    # 이미지와 이미지 검색 문장은 같은 OpenCLIP 모델·가중치를 사용한다.
    model_name = 'xlm-roberta-base-ViT-B-32'
    pretrained = 'laion5b_s13b_b90k'
    image_encoder = ImageEncoder(model_name=model_name, pretrained=pretrained)
    document_encoder = DocumentEncoder(image_encoder=image_encoder)
    query_encoder = KoreanTextEncoder(model_name=model_name, pretrained=pretrained)

    # 문서 본문은 별도 ko-SRoBERTa로 인코딩·비교한다.
    document_embedder = DocumentEmbedder()
    session = TemporaryDirectory(prefix='document-search-')
    repository = Repository(str(Path(session.name) / 'document_metadata.db'))
    service = DocumentSearch(DocumentLoader(), image_encoder, document_encoder,
                             document_embedder, query_encoder, repository)
    service.session_directory = session
    return service


def main():
    folder = input('분석할 폴더: ').strip().strip('"')
    if not Path(folder).is_dir():
        raise ValueError('존재하는 폴더를 입력하세요.')
    print('실제 모델 준비·분석 중입니다. 첫 실행은 모델 다운로드가 필요할 수 있습니다.')
    service = build_service()
    documents, failures = service.analyze(folder)
    print(f'저장 {len(documents)}개 / 읽기 실패 {len(failures)}개')
    for path, reason in failures:
        print(f'{path.name}: {reason}')
    while True:
        query = input('검색 문장 (Enter로 종료): ').strip()
        if not query:
            break
        mode = 'images' if input('이미지 유사도 검색(임시 구현)은 i, 본문 검색은 Enter: ').strip() == 'i' else 'documents'
        results = service.search(query, mode=mode)
        for info, score in results:
            print(f'{info.file_name} / {score:.4f}\n{info.file_path}')
        if not results:
            print('해당 검색 대상의 결과가 없습니다.')


if __name__ == '__main__':
    import sys
    if '--gui' in sys.argv:
        import tkinter as tk
        from gui.window import DocumentSearchApp
        root = tk.Tk()
        DocumentSearchApp(root, build_service)
        root.mainloop()
    else:
        main()
