from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from connection.service import DocumentSearch


class RawSimilarityTests(unittest.TestCase):
    def setUp(self):
        self.service=DocumentSearch(*([None]*7))

    def file(self,i,path,hash=None):
        return SimpleNamespace(file_id=i,file_path=path,file_name=path,file_hash=hash)

    def search(self,docs,images,top_k=5):
        self.service.search=Mock(side_effect=[docs,images])
        return self.service.search_hybrid('query',top_k=top_k)

    def test_image_files_can_use_ocr_score(self):
        for suffix in ('.jpg','.JPEG','.png','.webp'):
            with self.subTest(suffix=suffix):
                photo=self.file(1,'/cat'+suffix)
                result=self.search([(photo,0.99)],[(photo,0.26)])[0]
                self.assertEqual((result.score,result.source),(0.99,'documents'))
                self.assertEqual(result.document_score,0.99)
                self.assertEqual(result.image_score,0.26)

    def test_image_score_can_be_stronger_than_ocr(self):
        photo=self.file(1,'/cat.jpg')
        result=self.search([(photo,0.2)],[(photo,0.8)])[0]
        self.assertEqual((result.score,result.source),(0.8,'images'))
        self.assertEqual(result.document_score,0.2)
        self.assertEqual(result.image_score,0.8)

    def test_image_without_ocr_uses_only_image_score(self):
        photo=self.file(1,'/cat.jpg')
        result=self.search([],[(photo,0.26)])[0]
        self.assertEqual((result.score,result.source),(0.26,'images'))
        self.assertIsNone(result.document_score)
        self.assertEqual(result.image_score,0.26)

    def test_pdf_and_pptx_take_maximum_not_sum(self):
        for suffix in ('.pdf','.PPTX'):
            with self.subTest(suffix=suffix):
                doc=self.file(1,'/lesson'+suffix)
                result=self.search([(doc,0.7)],[(doc,0.3)])[0]
                self.assertEqual((result.score,result.source),(0.7,'documents'))
                self.assertEqual((result.document_score,result.image_score),(0.7,0.3))

    def test_document_image_can_be_stronger_than_body(self):
        doc=self.file(1,'/scanned.pdf')
        result=self.search([(doc,0.2)],[(doc,0.8)])[0]
        self.assertEqual((result.score,result.source),(0.8,'images'))

    def test_single_modality_documents_are_kept(self):
        body=self.file(1,'/text.pdf')
        scan=self.file(2,'/scan.pdf')
        results=self.search([(body,0.7)],[(scan,0.6)])
        self.assertEqual([r.file.file_id for r in results],[1,2])
        self.assertIsNone(results[0].image_score)
        self.assertIsNone(results[1].document_score)

    def test_two_modalities_do_not_outvote_one_stronger_match(self):
        photo=self.file(1,'/cat.jpg')
        weak=self.file(2,'/unrelated.pdf')
        results=self.search([(weak,0.22)],[(photo,0.26),(weak,0.21)])
        self.assertEqual([r.file.file_id for r in results],[1,2])
        self.assertEqual(results[1].score,0.22)

    def test_precise_body_document_beats_weaker_dual_match(self):
        exact=self.file(1,'/exact.pdf')
        weak=self.file(2,'/weak.pptx')
        results=self.search([(exact,0.88),(weak,0.55)],[(weak,0.3)])
        self.assertEqual([r.file.file_id for r in results],[1,2])

    def test_direct_raw_comparison_has_no_margin_normalization(self):
        doc=self.file(1,'/doc.pdf')
        photo=self.file(2,'/photo.jpg')
        results=self.search([(doc,0.43)],[(photo,0.28)])
        self.assertEqual([r.file.file_id for r in results],[1,2])
        self.assertEqual([r.score for r in results],[0.43,0.28])

    def test_zero_and_negative_scores_are_not_thresholded(self):
        a,b,c=self.file(1,'/a.pdf'),self.file(2,'/b.jpg'),self.file(3,'/c.pdf')
        results=self.search([(a,-0.2),(c,0.)],[(b,-0.1)])
        self.assertEqual([r.score for r in results],[0.,-0.1,-0.2])

    def test_nonfinite_values_are_invalid_not_relevance_filtered(self):
        docs=[(self.file(i,f'/{i}.pdf'),score) for i,score in enumerate([float('nan'),float('inf'),-0.1])]
        results=self.search(docs,[])
        self.assertEqual([r.score for r in results],[-0.1])

    def test_path_ties_are_stable_and_duplicate_content_is_merged(self):
        a,b,c=self.file(1,'/a.pdf','same'),self.file(2,'/b.pdf','same'),self.file(3,'/c.jpg','other')
        results=self.search([(b,0.8),(a,0.8)],[(c,0.7)])
        self.assertEqual([r.file.file_id for r in results],[1,3])

    def test_repeated_hits_in_one_channel_keep_the_maximum(self):
        doc=self.file(1,'/a.pdf')
        result=self.search([(doc,0.8),(doc,0.3)],[])[0]
        self.assertEqual(result.score,0.8)

    def test_higher_body_image_tie_prefers_body_label_without_extra_score(self):
        doc=self.file(1,'/a.pdf')
        result=self.search([(doc,0.8)],[(doc,0.8)])[0]
        self.assertEqual((result.score,result.source),(0.8,'documents'))

    def test_all_file_candidates_are_read_before_final_limit(self):
        self.service.file_ids={str(i):i for i in range(20)}
        a=self.file(1,'/a.pdf')
        self.search([(a,0.5)],[],top_k=2)
        self.assertTrue(all(call.kwargs['top_k']==20 for call in self.service.search.call_args_list))

    def test_missing_hash_does_not_merge_unrelated_files(self):
        a,b=self.file(1,'/a.pdf'),self.file(2,'/b.pdf')
        self.assertEqual(len(self.search([(a,0.5),(b,0.4)],[])),2)

    def test_empty_query_and_invalid_limit_do_not_search(self):
        self.service.search=Mock()
        self.assertEqual(self.service.search_hybrid(' '),[])
        self.assertEqual(self.service.search_hybrid('q',top_k=0),[])
        self.service.search.assert_not_called()