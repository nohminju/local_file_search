"""일반 이미지는 이미지 점수만, PDF/PPTX는 본문·이미지 최고 원본 점수로 검증한다."""
import os
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
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

EXTRA=[('페르소나 경로맵','text',['페르소나']),
       ('사용자 여정 지도','text',['페르소나']),
       ('제주 축제 서비스를 이용하는 가상 페르소나','text',['페르소나'])]
def name(text): return unicodedata.normalize('NFC',unquote(text))

def main():
    torch.set_num_threads(4)
    baseline_path=ROOT/'docs/records/2026-11-20/PERSONA_SEARCH_COMPARISON_2026-11-20.json'
    if not baseline_path.is_file():
        raise SystemExit('로컬 전용 과거 비교 JSON이 없습니다. 독립 샘플 검사는 tests/real_sample_search_check.py를 실행하세요.')
    baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
    service=build_service()
    try:
        started=time.perf_counter()
        documents,failures=service.analyze(ROOT/'test_esset')
        seconds=time.perf_counter()-started
        assert sorted(d.file_hash for d in documents)==sorted(d['sha256'] for d in baseline['corpus'])
        assert not any(m.get('chunk_type')=='filename' for m in service.vector_index.chunk_metas['doc'])
        print(f'ANALYZED {len(documents)}; failures={len(failures)}; seconds={seconds:.1f}',flush=True)
        queries=[]
        for query,kind,expected in CASES+EXTRA:
            started=time.perf_counter()
            results=service.search(query,top_k=len(documents))
            search_seconds=time.perf_counter()-started
            expected_hashes={d.file_hash for d in documents if any(part in name(d.file_name) for part in expected)}
            rank=next((i for i,r in enumerate(results,1) if r.file.file_hash in expected_hashes),None)
            before=next(q for q in baseline['after'] if q['query']==query)
            rows=[dict(file=name(r.file.file_name),sha256=r.file.file_hash,source=r.source,
                       score=r.score,document_score=r.document_score,image_score=r.image_score) for r in results]
            for r in results:
                if Path(r.file.file_path).suffix.lower() in {'.jpg','.jpeg','.png','.webp'}:
                    assert r.source=='images' and r.document_score is None and r.score==r.image_score
                else:
                    assert r.score==max(s for s in (r.document_score,r.image_score) if s is not None)
            entry=dict(query=query,kind=kind,expected_name_parts=expected,before_rank=before['expected_best_rank'],
                       after_rank=rank,search_seconds=search_seconds,results=rows)
            queries.append(entry)
            print(json.dumps(dict(query=query,before=before['expected_best_rank'],after=rank,
                                  seconds=search_seconds,top5=rows[:5]),ensure_ascii=False),flush=True)
        output=dict(baseline_commit='4233ebf',baseline='filename-enabled margin ranking',
                    ranking='raw image cosine for image files; max raw body/image cosine for PDF/PPTX',
                    filename_search=False,thresholds=None,reranker=None,
                    analyzed=len(documents),failures=[(p.name,e) for p,e in failures],analysis_seconds=seconds,
                    document_chunks=len(service.vector_index.chunk_metas['doc']),
                    image_chunks=len(service.vector_index.chunk_metas['img']),
                    corpus=[dict(file=name(d.file_name),sha256=d.file_hash) for d in documents],queries=queries)
        (ROOT/'docs/records/2026-11-20/RAW_SIMILARITY_COMPARISON_2026-11-20.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('SAVED RAW_SIMILARITY_COMPARISON_2026-11-20.json',flush=True)
    finally:
        service.session_directory.cleanup()

if __name__=='__main__': main()
