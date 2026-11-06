"""동일 이미지·한국어 검색어로 두 이미지 검색 모델을 각각 평가한다.

앱·팀원 모듈은 가져오거나 수정하지 않는다. 실행 예:
  python tests/image_model_comparison.py --model current
  python tests/image_model_comparison.py --model siglip2
이미지는 로컬 study/image_search_check_2026-11-03/images에 있어야 한다.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    'current': ('xlm-roberta-base-ViT-B-32', 'laion5b_s13b_b90k'),
    'siglip2': ('ViT-B-16-SigLIP2', 'webli'),
}
FILES = ['Test1.jpg', 'Test2.jpg', 'Test3.jpg', 'beach.jpg', 'road.png', 'seal.jpg', 'zebra.png']
# 이미지를 눈으로 확인한 뒤, 모델 결과를 보기 전에 고정한 정답이다.
CASES = [
    ('고양이', FILES[:3]),
    ('파란 눈을 가진 고양이', ['Test1.jpg', 'Test3.jpg']),
    ('하얀 털과 갈색 무늬가 있는 고양이', FILES[:3]),
    ('하품하는 고양이', ['Test2.jpg']),
    ('배를 드러내고 누운 고양이', ['Test2.jpg']),
    ('고양이 얼굴을 가까이 찍은 사진', ['Test3.jpg']),
    ('모래사장에 의자가 놓인 해변', ['beach.jpg']),
    ('푸른 바다가 보이는 해변', ['beach.jpg']),
    ('바닷가 모래사장', ['beach.jpg']),
    ('길게 뻗은 도로', ['road.png']),
    ('차선이 있는 아스팔트 도로', ['road.png']),
    ('초원 사이로 난 길', ['road.png']),
    ('물개', ['seal.jpg']),
    ('눈 위에 앉아 있는 물개', ['seal.jpg']),
    ('검은색 물개 사진', ['seal.jpg']),
    ('얼룩말', ['zebra.png']),
    ('검고 흰 줄무늬가 있는 얼룩말', ['zebra.png']),
    ('얼룩말 옆모습', ['zebra.png']),
    ('강아지', []),
    ('비행기', []),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, required=True)
    parser.add_argument('--images', type=Path, default=ROOT / 'study/image_search_check_2026-11-03/images')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if args.repeats < 1 or args.threads < 1:
        parser.error('repeats와 threads는 1 이상이어야 한다.')
    output = args.output or ROOT / f'study/image_model_comparison_2026-11-06_{args.model}.json'
    import faiss
    import numpy as np
    import open_clip
    import torch
    from PIL import Image, ImageOps

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    faiss.omp_set_num_threads(args.threads)
    images, manifest = [], []
    for filename in FILES:
        path = args.images / filename
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            images.append(image)
            manifest.append({'file': filename, 'size': image.size,
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    model_name, pretrained = MODELS[args.model]
    result = {
        'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'model': model_name, 'pretrained': pretrained, 'device': 'cpu', 'dtype': 'float32',
        'threads': args.threads, 'repeats': args.repeats, 'seed': 0,
        'python': platform.python_version(), 'platform': platform.platform(),
        'cpu': platform.processor(), 'logical_cpus': os.cpu_count(),
        'versions': {p: importlib.metadata.version(p) for p in
                     ('torch', 'open_clip_torch', 'transformers', 'faiss-cpu', 'Pillow')},
        'images': manifest, 'cases': [{'query': q, 'relevant': relevant} for q, relevant in CASES],
        'protocol': 'CPU FP32; batch=1; model-native preprocessing/tokenizer; raw Korean queries; '
                    'L2-normalized embeddings; FAISS IndexFlatIP; one image/query warmup; '
                    '3 shuffled timed query rounds by default; preload images; exclude file IO, '
                    'download, model setup, warmup, DB and GUI from inference timings. '
                    'Absent queries are excluded from quality metrics; no rejection threshold.',
    }
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    save()
    try:
        print('LOAD_START', args.model, flush=True)
        start = time.perf_counter()
        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device='cpu', precision='fp32')
        tokenizer = open_clip.get_tokenizer(model_name)
        model.eval()
        result['setup_seconds_including_any_download'] = time.perf_counter() - start
        result['parameter_count'] = sum(p.numel() for p in model.parameters())
        result['image_size'] = model.visual.image_size
        print('LOAD_DONE', args.model, flush=True)

        @torch.inference_mode()
        def encode_image(image):
            return model.encode_image(preprocess(image).unsqueeze(0), normalize=True).float().cpu().numpy()

        @torch.inference_mode()
        def encode_query(query):
            return model.encode_text(tokenizer([query]), normalize=True).float().cpu().numpy()

        encode_image(images[0])
        encode_query(CASES[0][0])
        image_times, image_rounds = [], []
        vectors = []
        for repeat in range(args.repeats):
            round_times = []
            for image in images:
                start = time.perf_counter()
                vector = encode_image(image)
                elapsed = time.perf_counter() - start
                round_times.append(elapsed)
                if repeat == 0:
                    vectors.append(vector)
            image_times.extend(round_times)
            image_rounds.append(sum(round_times))
            print('IMAGE_ROUND_DONE', args.model, repeat + 1, flush=True)
        matrix = np.ascontiguousarray(np.concatenate(vectors), dtype=np.float32)
        assert np.isfinite(matrix).all()
        result['embedding_dim'] = int(matrix.shape[1])
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        query_times = [[] for _ in CASES]
        rankings = [None] * len(CASES)
        for repeat in range(args.repeats):
            order = list(range(len(CASES)))
            random.Random(repeat).shuffle(order)
            for i in order:
                start = time.perf_counter()
                query = encode_query(CASES[i][0])
                scores, indices = index.search(query, len(FILES))
                query_times[i].append(time.perf_counter() - start)
                if repeat == 0:
                    rankings[i] = [{'file': FILES[int(j)], 'cosine': float(s)}
                                   for j, s in zip(indices[0], scores[0])]
            print('QUERY_ROUND_DONE', args.model, repeat + 1, flush=True)
        positive = []
        for (query, relevant), ranking, timings in zip(CASES, rankings, query_times):
            names = [item['file'] for item in ranking]
            row = {'query': query, 'relevant': relevant, 'ranking': ranking,
                   'latency_ms': [1000 * t for t in timings]}
            if relevant:
                rank = min(names.index(name) + 1 for name in relevant)
                row.update(hit_at_1=float(rank == 1), hit_at_5=float(rank <= 5),
                           reciprocal_rank=1 / rank,
                           recall_at_3=len(set(names[:3]) & set(relevant)) / len(relevant))
                positive.append(row)
            result.setdefault('queries', []).append(row)
        result['quality'] = {key: statistics.mean(row[key] for row in positive)
                             for key in ('hit_at_1', 'hit_at_5', 'reciprocal_rank', 'recall_at_3')}
        result['quality']['positive_queries'] = len(positive)
        latencies = [1000 * t for timings in query_times for t in timings]
        result['timing'] = {
            'image_ms_per_image_median': 1000 * statistics.median(image_times),
            'image_round_seconds': image_rounds,
            'image_7_total_seconds_median': statistics.median(image_rounds),
            'query_ms_median': statistics.median(latencies),
            'query_ms_p95': float(np.percentile(latencies, 95)),
            'image_sample_count': len(image_times), 'query_sample_count': len(latencies),
        }
        result['status'] = 'complete'
        save()
        print('RESULT', json.dumps({'model': args.model, 'quality': result['quality'],
                                  'timing': result['timing']}, ensure_ascii=True), flush=True)
    except Exception as error:
        result.update(status='failed', error=f'{type(error).__name__}: {error}')
        save()
        raise


if __name__ == '__main__':
    main()
