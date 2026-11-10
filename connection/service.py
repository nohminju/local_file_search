"""로더·인코더·FAISS 검색 결과를 SQLite 파일 정보와 연결한다."""
def search_hybrid(self, query, top_k=5, k=60):
        query = query.strip()
        if not query or top_k <= 0:
            return []

        doc_results = self.search(query, top_k=top_k * 2, mode='documents')
        img_results = self.search(query, top_k=top_k * 2, mode='images')

        rrf_scores = {}
        info_map = {}

        for rank, (info, _) in enumerate(doc_results, start=1):
            file_id = info.file_id
            info_map[file_id] = info
            rrf_scores[file_id] = rrf_scores.get(file_id, 0.0) + (1.0 / (k + rank))

        for rank, (info, _) in enumerate(img_results, start=1):
            file_id = info.file_id
            info_map[file_id] = info
            rrf_scores[file_id] = rrf_scores.get(file_id, 0.0) + (1.0 / (k + rank))

        sorted_results = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)

        return [(info_map[file_id], score) for file_id, score in sorted_results[:top_k]]
