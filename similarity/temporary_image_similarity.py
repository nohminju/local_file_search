"""임시 구현된 이미지 유사도 검색. 담당자 구현을 받으면 이 함수를 교체한다."""
import numpy as np


def search_images(query_vector, image_vectors, top_k=5):
    # 1. 검색 문장 벡터를 숫자 배열로 준비한다.
    # 이미지와 문장은 반드시 같은 OpenCLIP 모델·가중치로 만들어야 한다.
    query = np.asarray(query_vector, dtype=float)
    query_length = np.linalg.norm(query)
    if query.ndim != 1 or not np.isfinite(query_length) or query_length == 0:
        raise ValueError("검색 벡터는 길이가 0이 아닌 유효한 1차원 배열이어야 합니다.")

    # 2. 파일별 가장 높은 점수를 보관한다. PPTX에 이미지가 여러 개여도
    # 같은 파일이 결과에 여러 번 나오지 않도록 파일 번호를 열쇠로 쓴다.
    best_scores = {}
    for file_id, image_vector in image_vectors:
        image = np.asarray(image_vector, dtype=float)
        if image.shape != query.shape:
            raise ValueError("이미지와 검색 문장 벡터의 차원이 다릅니다.")
        image_length = np.linalg.norm(image)
        if not np.isfinite(image_length) or image_length == 0:
            continue

        # 3. 내적을 두 벡터 길이로 나누면 코사인 유사도가 된다.
        # 방향이 비슷할수록 높은 점수다. 점수는 확률이 아니다.
        score = float(np.dot(query, image) / (query_length * image_length))
        if file_id not in best_scores or score > best_scores[file_id]:
            best_scores[file_id] = score

    # 4. (파일 번호, 점수)를 점수가 높은 순서로 정렬하고 top_k개만 반환한다.
    return sorted(best_scores.items(), key=lambda item: item[1], reverse=True)[:max(0, top_k)]
