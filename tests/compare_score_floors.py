"""실제 모델 원본 점수를 재사용해 필터 하한만 바꿔 비교한다."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from types import SimpleNamespace
from unittest.mock import Mock
from connection.service import DocumentSearch


def main():
    report = json.loads((ROOT / 'docs/records/2026-11-20/TEXT_MODEL_COMPARISON_2026-11-20.json').read_text(encoding='utf-8'))
    infos = {d['file']: SimpleNamespace(file_id=i, file_path=d['file'], file_name=d['file'],
                                       file_hash=d['sha256']) for i, d in enumerate(report['corpus'], 1)}
    settings = []
    for doc_floor in (0.3, 0.4, 0.5):
        for img_floor in (0.15, 0.2, 0.25):
            cases = []
            for q in report['results']['candidate_sentence']:
                service = DocumentSearch(*([None] * 7), document_min_score=doc_floor, image_min_score=img_floor)
                service.file_ids = {name: info.file_id for name, info in infos.items()}
                service.search = Mock(side_effect=[[(infos[r['file']], r['score']) for r in q['raw_documents']],
                                                  [(infos[r['file']], r['score']) for r in q['raw_images']]])
                results = service.search_hybrid(q['query'], top_k=len(infos))
                expected = {info.file_hash for name, info in infos.items()
                            if any(part in name for part in q['expected_name_parts'])}
                rank = next((i for i, r in enumerate(results, 1) if r.file.file_hash in expected), None)
                cases.append(dict(query=q['query'], kind=q['kind'], expected_best_rank=rank,
                                  returned=len(results)))
            settings.append(dict(document_floor=doc_floor, image_floor=img_floor,
                                 top1=sum(c['expected_best_rank'] == 1 for c in cases),
                                 image_top1=sum(c['expected_best_rank'] == 1 for c in cases if c['kind'] == 'image'),
                                 text_top1=sum(c['expected_best_rank'] == 1 for c in cases if c['kind'] == 'text'),
                                 cases=cases))
    output = ROOT / 'docs/records/2026-11-20/SCORE_FLOOR_COMPARISON_2026-11-20.json'
    output.write_text(json.dumps(dict(method='Replay recorded real-model raw scores through current DocumentSearch.search_hybrid. Exploratory, not independent validation.',
                                      settings=settings), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for setting in settings:
        print(json.dumps({k: v for k, v in setting.items() if k != 'cases'}, ensure_ascii=False))


if __name__ == '__main__':
    raise SystemExit('이전 검색 방식의 비교 도구입니다. 저장된 JSON 또는 해당 Git 커밋을 참고하세요. 현재 재정렬 검증은 tests/compare_similarity_search.py를 실행하세요.')
