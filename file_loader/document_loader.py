import os
import io
import urllib.parse
from dataclasses import dataclass
from typing import Generator, List, Optional
from PIL import Image
from pypdf import PdfReader
from pptx import Presentation

#추출된 문서/이미지 데이터 단위를 저장하는 데이터 클래스
@dataclass
class DocumentChunk:
    file_name: str
    file_path: str
    page_number: int
    text: str
    chunk_type: str
    image: Optional[Image.Image] = None

class DocumentScanner:
    #지원하는 파일 확장자 목록 (이외의 HWP, TXT 등은 탐색에서 자동 제외)
    SUPPORTED_EXTENSIONS = {'.pdf', '.pptx', '.jpg', '.jpeg', '.png', '.webp'}

    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def scan_files(self) -> Generator[str, None, None]:
        # 지정된 디렉토리와 하위 폴더를 순회하며 파일 목록을 수집
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                #열려있는 임시 파일(~$로 시작)은 읽기 시 에러를 유발하므로 수집에서 제외 (예외 처리)
                if file.startswith('~$'):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    yield os.path.join(root, file)

class DocumentLoader:
    def _get_clean_filename(self, file_path: str) -> str:
        # URL 인코딩된 형태의 파일명을 사람이 읽기 쉬운 원래의 문자열로 디코딩
        raw_name = os.path.basename(file_path)
        return urllib.parse.unquote(raw_name)

    def load_image(self, file_path: str) -> List[DocumentChunk]:
        # 단일 이미지 파일을 불러와 통합 검색을 위해 RGB 모드로 변환 후 청크 리스트로 반환
        file_name = self._get_clean_filename(file_path)
        try:
            with Image.open(file_path) as img:
                pil_img = img.convert("RGB")
                return [DocumentChunk(
                    file_name=file_name,
                    file_path=file_path,
                    page_number=1,
                    text="",
                    chunk_type="image",
                    image=pil_img
                )]
        except Exception:
            # 💡 손상된 이미지 파일 접근 시 프로그램 강제 종료를 막기 위해 빈 리스트 반환
            return []

    def load_pdf(self, file_path: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        file_name = self._get_clean_filename(file_path)

        try:
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages, start=1):
                # 1. PDF 텍스트 추출 파트
                try:
                    text = page.extract_text() or ""
                    clean_text = text.strip()
                    # 추출된 텍스트가 유효한 경우에만 청크로 저장
                    if clean_text:
                        chunks.append(DocumentChunk(
                            file_name=file_name,
                            file_path=file_path,
                            page_number=page_idx,
                            text=clean_text,
                            chunk_type="pdf"
                        ))
                except Exception:
                    pass # 텍스트 추출 실패 시 무시하고 다음 파트로 진행

                # 2. PDF 내부 삽입 이미지 추출 파트
                try:
                    for image_file in page.images:
                        try:
                            image = Image.open(
                                io.BytesIO(image_file.data)
                            ).convert("RGB")

                            # 해상도가 너무 작은 이미지(노이즈, 아이콘 등)는 검색 품질을 저하시키므로 필터링 (100x100 픽셀 기준)
                            if image.width < 100 or image.height < 100:
                                continue

                            chunks.append(DocumentChunk(
                                file_name=file_name,
                                file_path=file_path,
                                page_number=page_idx,
                                text="",
                                chunk_type="image",
                                image=image
                            ))
                        except Exception:
                            continue
                except Exception:
                    pass

        except Exception:
            return [] # 문서 전체가 손상되어 읽을 수 없는 경우에 대한 최종 예외 처리

        return chunks

    def load_pptx(self, file_path: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        file_name = self._get_clean_filename(file_path)

        try:
            prs = Presentation(file_path)
            for slide_idx, slide in enumerate(prs.slides, start=1):
                slide_texts: List[str] = []
                extracted_images = []

                # 슬라이드 내의 모든 객체(Shape)를 순회하며 텍스트와 이미지를 각각 분류하여 추출
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        # 텍스트 박스인 경우 단락(paragraph)별로 텍스트를 모음
                        for paragraph in shape.text_frame.paragraphs:
                            line = paragraph.text.strip()
                            if line:
                                slide_texts.append(line)
                    elif shape.has_table:
                        # 표(Table) 객체인 경우 각 행/열의 셀을 순회하며 텍스트 추출
                        for row in shape.table.rows:
                            for cell in row.cells:
                                cell_text = cell.text.strip()
                                if cell_text:
                                    slide_texts.append(cell_text)
                    elif shape.shape_type == 13:
                        # 객체 타입이 13(그림/이미지)인 경우, 이미지 바이너리 데이터를 RGB 모드로 변환하여 추출
                        try:
                            image_bytes = shape.image.blob
                            extracted_images.append(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
                        except Exception:
                            pass

                # 한 슬라이드에서 수집한 텍스트들을 모두 연결하여 하나의 텍스트 청크로 병합
                combined_text = "\n".join(slide_texts).strip()
                if combined_text:
                    chunks.append(DocumentChunk(
                        file_name=file_name,
                        file_path=file_path,
                        page_number=slide_idx,
                        text=combined_text,
                        chunk_type="pptx"
                    ))

                # 추출된 이미지들은 분리하여 각각 개별 청크로 생성
                for image in extracted_images:
                    chunks.append(DocumentChunk(
                        file_name=file_name,
                        file_path=file_path,
                        page_number=slide_idx,
                        text="",
                        chunk_type="image",
                        image=image
                    ))

        except Exception:
            return []

        return chunks

    def process_file(self, file_path: str) -> List[DocumentChunk]:
        # 파일이 삭제되었거나 내용이 비어있는(0 byte) 경우를 사전 차단 (예외 처리)
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return []

        # 확장자에 맞춰 적절한 전용 로더(loader) 함수를 호출하여 처리 (라우팅 역할)
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self.load_pdf(file_path)
        elif ext == '.pptx':
            return self.load_pptx(file_path)
        elif ext in {'.jpg', '.jpeg', '.png', '.webp'}:
            return self.load_image(file_path)
        
        return []
