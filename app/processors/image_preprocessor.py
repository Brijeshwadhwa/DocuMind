import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2
from app.core.logging import logger


class ImagePreprocessor:
    """Preprocesses images and scanned PDF pages to optimize OCR recognition."""

    @staticmethod
    def pil_to_cv2(image: Image.Image) -> np.ndarray:
        """Convert a PIL Image to an OpenCV BGR/Grayscale numpy array."""
        arr = np.array(image)
        if len(arr.shape) == 2:  # Grayscale
            return arr
        elif arr.shape[2] == 4:  # RGBA
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        else:  # RGB
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    @staticmethod
    def cv2_to_pil(cv_img: np.ndarray) -> Image.Image:
        """Convert an OpenCV numpy array back to PIL Image."""
        if len(cv_img.shape) == 2:
            return Image.fromarray(cv_img)
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    @classmethod
    def deskew(cls, cv_img: np.ndarray) -> np.ndarray:
        """Detect and correct document skew angle."""
        try:
            gray = cv_img if len(cv_img.shape) == 2 else cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            # Invert colors so text is white on black
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            # Find all text pixels
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 100:
                return cv_img

            # Compute minimum area bounding box
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]

            # Determine true skew angle
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Only rotate if skew is non-trivial but not extreme (e.g. 0.5 to 30 degrees)
            if 0.5 < abs(angle) < 30.0:
                (h, w) = cv_img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    cv_img,
                    M,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                logger.debug(f"Image deskewed by {angle:.2f} degrees")
                return rotated
        except Exception as e:
            logger.debug(f"Deskew skipped: {str(e)}")
        return cv_img

    @classmethod
    def preprocess_for_ocr(cls, image: Image.Image) -> Image.Image:
        """
        Complete preprocessing pipeline:
        1. Grayscale conversion
        2. Upscaling if dimensions are small
        3. Deskewing
        4. Noise reduction
        5. Adaptive contrast & thresholding
        """
        try:
            # 1. Ensure minimum resolution for OCR (at least ~1500px width for standard letter/A4)
            w, h = image.size
            if w < 1200 or h < 1200:
                scale_factor = max(1200 / max(w, 1), 1200 / max(h, 1))
                new_size = (int(w * scale_factor), int(h * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # 2. Convert to OpenCV representation
            cv_img = cls.pil_to_cv2(image)

            # 3. Grayscale
            if len(cv_img.shape) == 3:
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv_img

            # 4. Deskew
            deskewed = cls.deskew(gray)

            # 5. Denoise with bilateral filter (preserves edges of text glyphs)
            denoised = cv2.bilateralFilter(deskewed, 9, 75, 75)

            # 6. Adaptive thresholding (Otsu's binarization)
            _, binary = cv2.threshold(
                denoised,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            res = cls.cv2_to_pil(binary)
            if hasattr(image, "info"):
                res.info.update(image.info)
            if hasattr(image, "text"):
                res.text = getattr(res, "text", {})
                res.text.update(image.text)
            return res
        except Exception as e:
            logger.warning(f"Image preprocessing warning, returning enhanced PIL image: {e}")
            # Graceful PIL fallback: grayscale + sharpen + contrast
            gray_pil = image.convert("L")
            enhanced = ImageEnhance.Contrast(gray_pil).enhance(1.8)
            res = enhanced.filter(ImageFilter.SHARPEN)
            if hasattr(image, "info"):
                res.info.update(image.info)
            if hasattr(image, "text"):
                res.text = getattr(res, "text", {})
                res.text.update(image.text)
            return res
