"""실제 모델로 로컬 자료를 검증합니다. 실행 예: python tests/real_sample_search_check.py"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')

import torch
from app import build_service

CASES = [
    ('고양이', ['Test1.jpg', 'Test2.jpg', 'Test3.jpg', '고양이.jpeg']),
    ('누워있는 고양이', ['Test2.jpg']),
    ('파란 눈을 가진 고양이', ['Test1.jpg', 'Test3.jpg']),
    ('관계형 데이터베이스의 기본키와 외래키', ['데이터베이스', '데이터 베이스']),
    ('동적 계획법의 최적 부분 구조와 중복 부분 문제', ['동적계획법']),
    ('딥러닝', ['딥러닝']),
]


def normalized(text):
    return unicodedata.normalize('NFC', text)


def main():
    parser = argparse.ArgumentParser(description='캐시된 실제 모델로 샘플 검색 순위를 기록합니다.')
    parser.add_argument('--folder', type=Path, default=ROOT / 'test_esset')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/records/2026-11-20/REAL_SAMPLE_SIMILARITY_RESULTS_2026-11-20.json')
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if args.threads < 1 or not args.folder.is_dir():
        parser.error('존재하는 샘플 폴더와 양수 threads가 필요합니다.')
    torch.set_num_threads(args.threads)
    started = time.perf_counter()
    service = build_service()
    model_seconds = time.perf_counter() - started
    original_loader = service.loader.process_file
    extracted = []

    def load(path):
        chunks = original_loader(path)
        texts = [c for c in chunks if c.text.strip()]
        extracted.append({'file': normalized(Path(path).name), 'text_chunks': len(texts),
                          'image_chunks': sum(c.image is not None for c in chunks),
                          'text_preview': texts[0].text[:250] if texts else ''})
        print(f'LOADED {normalized(Path(path).name)}: {len(texts)} text / {sum(c.image is not None for c in chunks)} image', flush=True)
        return chunks

    service.loader.process_file = load
    try:
        started = time.perf_counter()
        documents, failures = service.analyze(args.folder)
        analysis_seconds = time.perf_counter() - started
        report = {'python': platform.python_version(), 'torch': torch.__version__,
                  'image_model': 'xlm-roberta-base-ViT-B-32',
                  'document_model': 'jhgan/ko-sroberta-multitask', 'pretrained': 'laion5b_s13b_b90k',
                  'device': str(service.image_encoder.device), 'threads': args.threads,
                  'thresholds': None, 'filename_search': False,
                  'ranking': 'image files: image cosine only; PDF/PPTX: max(body cosine, image cosine); descending raw score; no sum',
                  'model_load_seconds': model_seconds, 'analysis_seconds': analysis_seconds,
                  'analyzed': len(documents), 'failures': [(p.name, error) for p, error in failures],
                  'chunk_counts': {k: len(v) for k, v in service.vector_index.chunk_metas.items()},
                  'files': [{'file': normalized(p.name), 'sha256': sha256(p.read_bytes()).hexdigest(),
                             'bytes': p.stat().st_size} for p in sorted(args.folder.iterdir()) if p.is_file()],
                  'extraction': extracted, 'queries': []}

        def file_row(info, score):
            return {'file': normalized(info.file_name), 'score': float(score), 'sha256': info.file_hash}

        for query, expected in CASES:
            raw_docs = service.search(query, top_k=len(documents), mode='documents')
            raw_images = service.search(query, top_k=len(documents), mode='images')
            hybrid = service.search(query, top_k=len(documents))
            results = [dict(file_row(r.file, r.score), source=r.source,
                            document_score=r.document_score, image_score=r.image_score) for r in hybrid]
            expected_hashes = {info.file_hash for info in documents
                               if any(part in normalized(info.file_name) for part in expected)}
            ranks = [i for i, row in enumerate(results, 1) if row['sha256'] in expected_hashes]
            report['queries'].append({'query': query, 'expected_name_parts': expected,
                                      'expected_best_rank': min(ranks) if ranks else None,
                                      'raw_documents': [file_row(*row) for row in raw_docs],
                                      'raw_images': [file_row(*row) for row in raw_images],
                                      'results': results})
            print(json.dumps({'query': query, 'expected_best_rank': min(ranks) if ranks else None,
                              'top5': results[:5]}, ensure_ascii=False), flush=True)

        # 본문 추출과 검색 연결을 구분하기 위해 모델 입력 청크 하나를 완전 일치로 재검색한다.
        for part in ('동적계획법', '데이터베이스'):
            chunk = next((c for c in service.document_embedder.chunks
                          if part in normalized(c.file_name) and len(c.text.strip()) > 30), None)
            if chunk is None:
                continue
            query = chunk.text.strip()
            rows = service.search(query, top_k=5)
            expected_hash = next(d.file_hash for d in documents if d.file_path == chunk.file_path)
            result_rows = [dict(file_row(r.file, r.score), source=r.source,
                                document_score=r.document_score, image_score=r.image_score) for r in rows]
            rank = next((i for i, r in enumerate(result_rows, 1) if r['sha256'] == expected_hash), None)
            report['queries'].append({'query': query, 'kind': 'exact_extracted_chunk_diagnostic',
                                      'expected_file': normalized(chunk.file_name), 'expected_best_rank': rank,
                                      'results': result_rows})
            print(json.dumps({'exact_text_file': normalized(chunk.file_name), 'expected_best_rank': rank,
                              'top5': result_rows}, ensure_ascii=False), flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'SAVED {args.output}; analyzed={len(documents)}; failures={len(failures)}; seconds={analysis_seconds:.1f}', flush=True)
    finally:
        service.session_directory.cleanup()


if __name__ == '__main__':
    main()
