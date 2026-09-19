from typing import List, Optional
from dataclasses import dataclass
import io
from PIL import Image
import pymupdf as fitz
import pypdf
from app.core.config import settings
from app.core.logging import logger
from app.processors.image_preprocessor import ImagePreprocessor
from app.processors.ocr_engine import BaseOCRService, get_ocr_service


@dataclass
class PageData:
    page_number: int  # 1-indexed
    text: str
    is_scanned: bool
    ocr_confidence: float  # 0.0 - 1.0


class DocumentExtractor:
    """Extracts text and page structure from PDF documents and images."""

    def __init__(self, ocr_service: Optional[BaseOCRService] = None):
        self.ocr_service = ocr_service or get_ocr_service()

    def process_pdf(self, file_path: str) -> List[PageData]:
        """
        Processes a PDF document:
        1. Attempts native text extraction first.
        2. If a page has insufficient text (< 40 characters), renders page to image and runs OCR fallback.
        3. Preserves exact page numbers and boundaries.
        """
        pages: List[PageData] = []
        try:
            doc = fitz.open(file_path)
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page = doc[page_idx]
                native_text = page.get_text("text").strip()

                # Determine if page is digitally generated with valid selectable text
                is_scanned = len(native_text) < 40

                if not is_scanned:
                    pages.append(PageData(
                        page_number=page_num,
                        text=native_text,
                        is_scanned=False,
                        ocr_confidence=1.0
                    ))
                    logger.debug(f"Page {page_num}: Extracted {len(native_text)} chars natively")
                else:
                    logger.info(f"Page {page_num}: Low/no native text ({len(native_text)} chars). Triggering OCR fallback...")
                    # Render page to high-res image
                    pixmap = page.get_pixmap(dpi=settings.OCR_DPI)
                    img_bytes = pixmap.tobytes("png")
                    image = Image.open(io.BytesIO(img_bytes))

                    # Preprocess and run OCR
                    preprocessed_img = ImagePreprocessor.preprocess_for_ocr(image)
                    ocr_result = self.ocr_service.extract_text_from_image(preprocessed_img)

                    # If OCR produced text, use it; otherwise fallback to whatever native text existed
                    page_text = ocr_result.text if ocr_result.text.strip() else native_text
                    confidence = ocr_result.confidence if ocr_result.text.strip() else 0.4

                    pages.append(PageData(
                        page_number=page_num,
                        text=page_text,
                        is_scanned=True,
                        ocr_confidence=confidence
                    ))
                    logger.debug(f"Page {page_num} (OCR): Extracted {len(page_text)} chars with conf {confidence}")

            doc.close()
            return pages
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed for {file_path}: {e}. Trying pypdf fallback...")
            return self._pypdf_fallback(file_path)

    def _pypdf_fallback(self, file_path: str) -> List[PageData]:
        """Fallback extractor using standard pypdf."""
        pages: List[PageData] = []
        try:
            reader = pypdf.PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                text = page.extract_text() or ""
                pages.append(PageData(
                    page_number=page_num,
                    text=text.strip(),
                    is_scanned=len(text.strip()) < 40,
                    ocr_confidence=0.8 if len(text.strip()) >= 40 else 0.3
                ))
            return pages
        except Exception as e:
            logger.error(f"pypdf fallback also failed for {file_path}: {e}")
            raise RuntimeError(f"Failed to read PDF document: {e}")

    def process_image(self, file_path: str) -> List[PageData]:
        """
        Processes a standalone image file (JPG, JPEG, PNG):
        Preprocesses the image and runs OCR.
        """
        try:
            image = Image.open(file_path)
            preprocessed_img = ImagePreprocessor.preprocess_for_ocr(image)
            ocr_result = self.ocr_service.extract_text_from_image(preprocessed_img)

            return [
                PageData(
                    page_number=1,
                    text=ocr_result.text,
                    is_scanned=True,
                    ocr_confidence=ocr_result.confidence
                )
            ]
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            raise RuntimeError(f"Failed to read image file: {e}")
