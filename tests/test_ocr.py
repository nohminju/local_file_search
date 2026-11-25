
"""OCR 텍스트 추출과 신뢰도 필터링을 검증.
실제 OCR 모델 가중치는 사용하지 않는다.
"""

import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from file_encoder.ocr_extractor import OCRExtractor


class OCRExtractorTests(unittest.TestCase):

    def make_extractor(self):
        extractor = object.__new__(OCRExtractor)
        extractor.min_confidence = 0.3
        extractor.reader = Mock()
        return extractor

    def test_extract_korean_and_english(self):
        extractor = self.make_extractor()

        extractor.reader.readtext.return_value = [
            ([], '캡스톤 디자인', 0.95),
            ([], 'OpenCLIP', 0.98)
        ]

        image = Image.new('RGB', (100, 100))

        text = extractor.extract(image)

        self.assertEqual(
            text,
            '캡스톤 디자인\nOpenCLIP'
        )

    def test_low_confidence_text_is_removed(self):
        extractor = self.make_extractor()

        extractor.reader.readtext.return_value = [
            ([], '정상 텍스트', 0.95),
            ([], '잘못된 텍스트', 0.1)
        ]

        image = Image.new('RGB', (100, 100))

        self.assertEqual(
            extractor.extract(image),
            '정상 텍스트'
        )

    def test_empty_text_is_removed(self):
        extractor = self.make_extractor()

        extractor.reader.readtext.return_value = [
            ([], '   ', 0.95),
            ([], '정상 텍스트', 0.9)
        ]

        image = Image.new('RGB', (100, 100))

        self.assertEqual(
            extractor.extract(image),
            '정상 텍스트'
        )

    def test_no_text_returns_empty_string(self):
        extractor = self.make_extractor()
        extractor.reader.readtext.return_value = []

        image = Image.new('RGB', (100, 100))

        self.assertEqual(extractor.extract(image), '')

    def test_non_image_input_is_rejected(self):
        extractor = self.make_extractor()

        with self.assertRaises(TypeError):
            extractor.extract('photo.jpg')

    def test_grayscale_image_is_converted(self):
        extractor = self.make_extractor()
        extractor.reader.readtext.return_value = []

        image = Image.new('L', (100, 100))

        extractor.extract(image)

        image_array = (
            extractor.reader.readtext.call_args.args[0]
        )

        self.assertEqual(image_array.shape, (100, 100, 3))
        self.assertEqual(image_array.dtype, np.uint8)

    def test_rgb_image_is_converted_to_bgr(self):
        extractor = self.make_extractor()
        extractor.reader.readtext.return_value = []

        image = Image.new('RGB', (1, 1), (255, 0, 0))

        extractor.extract(image)

        image_array = (
            extractor.reader.readtext.call_args.args[0]
        )

        np.testing.assert_array_equal(
            image_array[0, 0],
            [0, 0, 255]
        )

    def test_invalid_confidence_is_rejected(self):
        for confidence in [-0.1, 1.1]:
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    OCRExtractor(min_confidence=confidence)

    @patch('file_encoder.ocr_extractor.easyocr.Reader')
    def test_reader_supports_korean_and_english(self, reader):
        OCRExtractor(gpu=False)

        reader.assert_called_once_with(
            ['ko', 'en'],
            gpu=False
        )


if __name__ == '__main__':
    unittest.main()