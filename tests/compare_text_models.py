"""동일 로더·이미지 벡터·점수 기준으로 본문 모델만 바꾸는 비교 도구."""
import os
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hashlib import sha256
import json
import time
import unicodedata
from urllib.parse import unquote
import numpy as np
import torch
from app import build_service
from database.faiss import FaissManager
from connection.sentence_document_embedder import SentenceDocumentEmbedder

# 첫 6개는 이전 평가와 같은 질의다. 추가 질의도 모델 출력을 보기 전에 고정했다.
# 앞 3개 사진의 무관 문서는 주제명으로 확인한다. 본문은 제목/본문 주제로 정한 기대 대상이다.
CASES = [
    ('고양이', 'image', ['Test1.jpg', 'Test2.jpg', 'Test3.jpg', '고양이.jpeg']),
    ('누워있는 고양이', 'image', ['Test2.jpg']),
    ('파란 눈을 가진 고양이', 'image', ['Test1.jpg', 'Test3.jpg']),
    ('관계형 데이터베이스의 기본키와 외래키', 'text', ['데이터베이스', '데이터 베이스']),
    ('동적 계획법의 최적 부분 구조와 중복 부분 문제', 'text', ['동적계획법']),
    ('딥러닝', 'text', ['딥러닝']),
    ('피자', 'image', ['피자']),
    ('판다', 'image', ['판다']),
    ('비행기', 'image', ['비행기', 'images.jpeg']),
    ('기독교와 시인 고정희', 'text', ['기독교와 시인']),
    ('바울 사상과 현대 몸에 대한 이해', 'text', ['바울사상']),
    ('페르소나와 사용자 경로맵', 'text', ['페르소나']),
    ('인간 컴퓨터 상호작용의 과업 분석', 'text', ['과업', '상호작용 2']),
]

def name(text):
    return unicodedata.normalize('NFC', unquote(text))

def main():
    torch.set_num_threads(4)
    service = build_service(document_backend='openclip')
    try:
        started = time.perf_counter()
        documents, failures = service.analyze(ROOT / 'test_esset')
        print(f'BASELINE ANALYZED {len(documents)} in {time.perf_counter()-started:.1f}s', flush=True)
        corpus = [{'file': name(d.file_name), 'sha256': d.file_hash} for d in documents]
        candidates = {'baseline_openclip': [], 'candidate_sentence': []}

        def collect(label):
            for query, kind, expected in CASES:
                results = service.search(query, top_k=len(documents))
                docs = service.search(query, top_k=len(documents), mode='documents')
                images = service.search(query, top_k=len(documents), mode='images')
                expected_hashes = {d.file_hash for d in documents if any(x in name(d.file_name) for x in expected)}
                rank = next((i for i, r in enumerate(results, 1) if r.file.file_hash in expected_hashes), None)
                rows = [dict(file=name(r.file.file_name), sha256=r.file.file_hash, score=r.score,
                             source=r.source, document_score=r.document_score,
                             image_score=r.image_score, sort_score=r.sort_score) for r in results]
                record = dict(query=query, kind=kind, expected_name_parts=expected,
                              expected_best_rank=rank, results=rows,
                              raw_documents=[dict(file=name(d.file_name), score=float(s)) for d, s in docs],
                              raw_images=[dict(file=name(d.file_name), score=float(s)) for d, s in images])
                candidates[label].append(record)
                print(json.dumps(dict(model=label, query=query, expected_rank=rank, top3=rows[:3]), ensure_ascii=False), flush=True)

        collect('baseline_openclip')
        # 동일한 모든 원본 청크를 다시 읽지 않고 인덱스 메타데이터에서 복원한다.
        from types import SimpleNamespace
        chunks = [SimpleNamespace(**meta) for meta in service.vector_index.chunk_metas['doc']]
        unique, positions, by_text = [], [], {}
        for chunk in chunks:
            if chunk.text not in by_text:
                by_text[chunk.text] = len(unique)
                unique.append(chunk)
            positions.append(by_text[chunk.text])
        started = time.perf_counter()
        embedder = SentenceDocumentEmbedder()
        embedder.embed_chunks(unique)
        index = FaissManager(doc_dim=768, img_dim=512)
        index.indices['img'] = service.vector_index.indices['img']
        index.chunk_metas['img'] = service.vector_index.chunk_metas['img']
        index.add_documents(embedder.embeddings[positions], chunks)
        service.document_embedder = embedder
        service.vector_index = index
        seconds = time.perf_counter() - started
        print(f'CANDIDATE TEXT READY {len(unique)} unique chunks in {seconds:.1f}s', flush=True)
        collect('candidate_sentence')
        report = dict(corpus=corpus, failures=[(p.name, e) for p, e in failures],
                      files=len(documents), document_chunks=len(chunks), unique_texts=len(unique),
                      image_chunks=len(index.chunk_metas['img']), threads=4,
                      document_floor=service.document_min_score, image_floor=service.image_min_score,
                      candidate_model='jhgan/ko-sroberta-multitask',
                      baseline_model='xlm-roberta-base-ViT-B-32',
                      candidate_load_and_text_seconds=seconds,
                      method='Same files, same image index, same floors and max-margin ranking. Only text model/index differs.',
                      results=candidates)
        output = ROOT / 'docs/records/2026-11-20/TEXT_MODEL_COMPARISON_2026-11-20.json'
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'SAVED {output}', flush=True)
    finally:
        service.session_directory.cleanup()

if __name__ == '__main__':
    raise SystemExit('이전 검색 방식의 비교 도구입니다. 저장된 JSON 또는 해당 Git 커밋을 참고하세요. 현재 재정렬 검증은 tests/compare_similarity_search.py를 실행하세요.')
