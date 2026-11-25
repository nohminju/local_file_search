"""한 실제 인덱스에서 이미지 검색어 번역 전후를 비교한다. 본문 번역은 끈다."""
import os
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import json
import argparse
import time
import unicodedata
from urllib.parse import unquote
import torch
from app import build_service
from connection.translator import translate_ko_to_en
from compare_text_models import CASES

EXTRA=[('페르소나 경로맵','text',['페르소나']),('사용자 여정 지도','text',['페르소나']),
       ('제주 축제 서비스를 이용하는 가상 페르소나','text',['페르소나'])]
def name(s): return unicodedata.normalize('NFC',unquote(s))
def rows(results):
    output=[]
    for result in results:
        info,score=result
        output.append(dict(file=name(info.file_name),sha256=info.file_hash,score=float(score),
                           source=result.source,document_score=getattr(result,'document_score',None),
                           image_score=getattr(result,'image_score',None)))
    return output
def expected_rank(output,expected):
    return next((i for i,r in enumerate(output,1) if any(part in r['file'] for part in expected)),None)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--english-diagnostic',action='store_true',
                        help='DeepL 번역 성공 결과가 아닌, 고정 영어 문장을 넣은 별도 민감도 진단')
    args=parser.parse_args()
    english_queries=[
        'cat','a lying cat','a cat with blue eyes',
        'primary keys and foreign keys in a relational database',
        'optimal substructure and overlapping subproblems in dynamic programming',
        'deep learning','pizza','panda','airplane',
        'Christianity and the poet Go Jung-hee',
        "Paul's thought and the understanding of the body in modern society",
        'persona and user journey map','task analysis in human computer interaction',
        'persona journey map','user journey map','a fictional persona using a Jeju festival service',
    ]
    english=dict(zip((q for q,_,_ in CASES+EXTRA),english_queries,strict=True))
    torch.set_num_threads(4)
    started=time.perf_counter()
    service=build_service()
    service.document_query_translator=None  # 이미지 번역 효과만 비교한다.
    print('MODELS_READY',flush=True)
    original_loader=service.loader.process_file
    loaded=0
    def load(path):
        nonlocal loaded
        chunks=original_loader(path)
        loaded+=1
        print(f'LOADED {loaded}: {name(Path(path).name)}',flush=True)
        return chunks
    service.loader.process_file=load
    try:
        documents,failures=service.analyze(ROOT/'test_esset')
        analysis_seconds=time.perf_counter()-started
        baseline_path=ROOT/'docs/records/2026-11-20/RAW_SIMILARITY_COMPARISON_2026-11-20.json'
        baseline=json.loads(baseline_path.read_text(encoding='utf-8')) if baseline_path.exists() else None
        if baseline:
            assert sorted(d.file_hash for d in documents)==sorted(r['sha256'] for r in baseline['corpus'])
        print(f'ANALYZED {len(documents)}; failures={len(failures)}; seconds={analysis_seconds:.1f}',flush=True)
        queries=[]
        count=len(documents)
        for query,kind,expected in CASES+EXTRA:
            service.image_query_translator=None
            before={mode:rows(service.search(query,top_k=count,mode=mode)) for mode in ('documents','images','hybrid')}
            translations=[]
            def translate(text):
                if translations: return translations[0]['translated']
                started=time.perf_counter()
                translated=english[text] if args.english_diagnostic else translate_ko_to_en(text)
                translations.append(dict(original=text,translated=translated,seconds=time.perf_counter()-started))
                return translated
            service.image_query_translator=translate
            after={mode:rows(service.search(query,top_k=count,mode=mode)) for mode in ('documents','images','hybrid')}
            assert before['documents']==after['documents'], '본문 검색 결과가 바뀌었습니다.'
            before_body={r['sha256']:r['document_score'] for r in before['hybrid']}
            after_body={r['sha256']:r['document_score'] for r in after['hybrid']}
            assert before_body==after_body, '통합검색의 본문 점수가 바뀌었습니다.'
            for r in after['hybrid']:
                if Path(r['file']).suffix.lower() in {'.jpg','.jpeg','.png','.webp'}:
                    assert r['document_score'] is None and r['score']==r['image_score']
                else: assert r['score']==max(s for s in (r['document_score'],r['image_score']) if s is not None)
            entry=dict(query=query,kind=kind,expected_name_parts=expected,translation=translations[0],body_unchanged=True,
                       before=before,after=after,
                       ranks={mode:dict(before=expected_rank(before[mode],expected),after=expected_rank(after[mode],expected)) for mode in before})
            queries.append(entry)
            output=dict(corpus=[dict(file=name(d.file_name),sha256=d.file_hash) for d in documents],
                        analyzed=len(documents),failures=[(p.name,e) for p,e in failures],
                        analysis_seconds=analysis_seconds,document_chunks=len(service.vector_index.chunk_metas['doc']),
                        image_chunks=len(service.vector_index.chunk_metas['img']),
                        translator=('manually fixed English queries; NOT actual DeepL translation outputs' if args.english_diagnostic else 'unmodified connection/translator.py, DeepL ko->en'),
                        english_diagnostic=args.english_diagnostic,
                        method='one corpus/index, original body query; translation reused only within each evaluation query',queries=queries)
            filename=('ENGLISH_QUERY_DIAGNOSTIC_2026-11-25.json' if args.english_diagnostic else 'TRANSLATION_COMPARISON_2026-11-25.json')
            destination=ROOT/'docs/records/2026-11-25'/filename
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(dict(query=query,translation=translations[0],ranks=entry['ranks'],
                                  hybrid_top3=after['hybrid'][:3]),ensure_ascii=False),flush=True)
        print(f'SAVED {filename}',flush=True)
    finally: service.session_directory.cleanup()

if __name__=='__main__': main()
