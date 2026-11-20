"""실제 팀원 로더·인코더·DB를 조립하여 실행한다."""
from pathlib import Path
from tempfile import TemporaryDirectory
import open_clip

from file_loader.document_loader import DocumentLoader
from file_encoder.image_encoder import ImageEncoder
from file_encoder.document_encoder import DocumentEncoder
from similarity.document_embedder import DocumentEmbedder as OpenCLIPDocumentEmbedder
from similarity.sentence_document_embedder import SentenceDocumentEmbedder as DocumentEmbedder
from query_encoder.text_encoder import KoreanTextEncoder
from database.manager import Repository
from database.faiss import FaissManager
from connection.service import DocumentSearch
from connection.text_preparation import DocumentTextPreparer


def build_service(document_backend='sentence'):
    if document_backend not in ('sentence', 'openclip'):
        raise ValueError('본문 모델은 sentence 또는 openclip입니다.')
    model_name = 'xlm-roberta-base-ViT-B-32'
    pretrained = 'laion5b_s13b_b90k'
    image_encoder = ImageEncoder(model_name=model_name, pretrained=pretrained)
    document_encoder = DocumentEncoder(image_encoder=image_encoder)
    query_encoder = KoreanTextEncoder(
        model=image_encoder.model,
        tokenizer=open_clip.get_tokenizer(model_name),
    )
    if document_backend == 'sentence':
        document_embedder = DocumentEmbedder()
        document_dim = 768
        text_preparer = DocumentTextPreparer(document_embedder.model.tokenizer,
                                             document_embedder.model.max_seq_length)
    else:
        # 이전 설정과 실제 샘플 비교·진단할 때만 사용한다.
        document_embedder = OpenCLIPDocumentEmbedder(
            model=image_encoder.model,
            tokenizer=query_encoder.tokenizer,
        )
        document_dim = 512
        text_preparer = None
    session = TemporaryDirectory(prefix='document-search-')
    repository = Repository(str(Path(session.name) / 'document_metadata.db'))
    service = DocumentSearch(DocumentLoader(), image_encoder, document_encoder,
                             document_embedder, query_encoder, repository,
                             FaissManager(doc_dim=document_dim, img_dim=512),
                             text_preparer=text_preparer)
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
        results = service.search(query)
        for result in results:
            info, score = result
            source = {'documents': '본문', 'images': '이미지', 'filenames': '파일명'}[result.source]
            print(f'{info.file_name} / {source} 유사도 {score:.4f}\n{info.file_path}')
        if not results:
            print('해당 검색 대상의 결과가 없습니다.')


if __name__ == '__main__':
    import sys
    if '--gui' in sys.argv:
        from gui.window import DocumentSearchApp
        DocumentSearchApp(build_service).mainloop()
    else:
        main()
