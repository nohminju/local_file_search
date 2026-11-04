import os
import urllib.parse
from dataclasses import dataclass
from typing import Generator, List, Optional
from PIL import Image


@dataclass
class ImageChunk:
    file_name: str
    file_path: str
    image: Optional[Image.Image]
    is_valid: bool


class ImageScanner:
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def scan_images(self) -> Generator[str, None, None]:
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.startswith('~$'):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    yield os.path.join(root, file)


class ImageLoader:
    def _get_clean_filename(self, file_path: str) -> str:
        raw_name = os.path.basename(file_path)
        return urllib.parse.unquote(raw_name)

    def load_image(self, file_path: str) -> Optional[ImageChunk]:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return None

        file_name = self._get_clean_filename(file_path)

        try:
            with Image.open(file_path) as img:
                img.verify()

            img = Image.open(file_path)
            pil_img = img.convert("RGB")

            return ImageChunk(
                file_name=file_name,
                file_path=file_path,
                image=pil_img,
                is_valid=True
            )
        except Exception:
            return ImageChunk(
                file_name=file_name,
                file_path=file_path,
                image=None,
                is_valid=False
            )

    def process_folder(self, root_dir: str) -> List[ImageChunk]:
        scanner = ImageScanner(root_dir)
        valid_chunks: List[ImageChunk] = []

        for path in scanner.scan_images():
            chunk = self.load_image(path)
            if chunk and chunk.is_valid:
                valid_chunks.append(chunk)

        return valid_chunks


if __name__ == "__main__":
    test_folder = "./test_images"
    loader = ImageLoader()
    results = loader.process_folder(test_folder)

    for item in results:
        print(f"[{item.file_name}] - 크기: {item.image.size}, 포맷: {item.image.format}")
