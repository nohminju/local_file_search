import unittest

from similarity.temporary_image_similarity import search_images


class TemporaryImageSimilarityTests(unittest.TestCase):
    def test_normalizes_ranks_and_keeps_best_image_per_file(self):
        images = [(1, [0, 100]), (2, [3, 4]), (1, [7, 0]), (3, [-2, 0])]
        results = search_images([5, 0], images, top_k=2)
        self.assertEqual([file_id for file_id, score in results], [1, 2])
        self.assertAlmostEqual(results[0][1], 1.0)
        self.assertAlmostEqual(results[1][1], 0.6)

    def test_rejects_different_dimensions(self):
        with self.assertRaises(ValueError):
            search_images([1, 0], [(1, [1, 0, 0])])

    def test_skips_zero_images_and_rejects_zero_query(self):
        self.assertEqual(search_images([1, 0], [(1, [0, 0])]), [])
        with self.assertRaises(ValueError):
            search_images([0, 0], [(1, [1, 0])])

    def test_empty_index_and_no_results_requested(self):
        self.assertEqual(search_images([1, 0], []), [])
        self.assertEqual(search_images([1, 0], [(1, [1, 0])], top_k=0), [])
