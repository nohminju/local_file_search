"""파일명·긴 본문 보완 전후를 같은 실샘플 질의로 비교한다."""
import os
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import json
import time
import unicodedata
from urllib.parse import unquote
import torch
from app import build_service
from compare_text_models import CASES

EXTRA = [
    ('페르소나 경로맵', 'text', ['페르소나']),
    ('사용자 여정 지도', 'text', ['페르소나']),
    ('제주 축제 서비스를 이용하는 가상 페르소나', 'text', ['페르소나']),
]

def name(text):
    return unicodedata.normalize('NFC',unquote(text))

def main():
    torch.set_num_threads(4)
    baseline=json.loads((ROOT/'docs/records/2026-11-20/TEXT_MODEL_COMPARISON_2026-11-20.json').read_text(encoding='utf-8'))
    before=baseline['results']['candidate_sentence']
    service=build_service()
    try:
        started=time.perf_counter()
        documents,failures=service.analyze(ROOT/'test_esset')
        seconds=time.perf_counter()-started
        assert sorted(d.file_hash for d in documents)==sorted(d['sha256'] for d in baseline['corpus'])
        print(f'ANALYZED {len(documents)} in {seconds:.1f}s; chunks={len(service.vector_index.chunk_metas["doc"])}',flush=True)
        after=[]
        for query,kind,expected in CASES+EXTRA:
            results=service.search(query,top_k=len(documents))
            expected_hashes={d.file_hash for d in documents if any(x in name(d.file_name) for x in expected)}
            rank=next((i for i,r in enumerate(results,1) if r.file.file_hash in expected_hashes),None)
            rows=[dict(file=name(r.file.file_name),sha256=r.file.file_hash,score=r.score,
                       source=r.source,document_score=r.document_score,image_score=r.image_score,
                       sort_score=r.sort_score) for r in results]
            docs=service.search(query,top_k=len(documents),mode='documents')
            images=service.search(query,top_k=len(documents),mode='images')
            record=dict(query=query,kind=kind,expected_name_parts=expected,expected_best_rank=rank,
                        results=rows,
                        raw_documents=[dict(file=name(d.file_name),score=float(s),source=getattr(hit,'source','documents')) for hit in docs for d,s in [hit]],
                        raw_images=[dict(file=name(d.file_name),score=float(s)) for d,s in images])
            after.append(record)
            print(json.dumps(dict(query=query,expected_rank=rank,top3=rows[:3]),ensure_ascii=False),flush=True)
        persona=next(d for d in documents if '페르소나' in name(d.file_name))
        metas=service.vector_index.chunk_metas['doc']
        meta_counts={key:sum(m.get('chunk_type')==key for m in metas) for key in ['filename','pdf','pptx']}
        output=dict(baseline_commit='09ca810',baseline_source='TEXT_MODEL_COMPARISON_2026-11-20.json candidate_sentence',
                    corpus=[dict(file=name(d.file_name),sha256=d.file_hash) for d in documents],
                    analyzed=len(documents),failures=[(p.name,e) for p,e in failures],analysis_seconds=seconds,
                    document_floor=service.document_min_score,image_floor=service.image_min_score,
                    document_chunks=len(metas),image_chunks=len(service.vector_index.chunk_metas['img']),
                    document_chunk_types=meta_counts,token_limit=service.text_preparer.limit,
                    overlap=service.text_preparer.overlap,
                    persona_indexed_texts=[m for m in metas if m['file_path']==persona.file_path],
                    before=before,after=after)
        (ROOT/'docs/records/2026-11-20/PERSONA_SEARCH_COMPARISON_2026-11-20.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('SAVED PERSONA_SEARCH_COMPARISON_2026-11-20.json',flush=True)
    finally:
        service.session_directory.cleanup()

if __name__ == '__main__':
    raise SystemExit('이전 검색 방식의 비교 도구입니다. 저장된 JSON 또는 해당 Git 커밋을 참고하세요. 현재 재정렬 검증은 tests/compare_similarity_search.py를 실행하세요.')
