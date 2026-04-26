"""
OCR service — converts prescription images to raw text.
Printed text: Tesseract 5.
Handwritten text: TrOCR (transformer-based, lazy-loaded).
Preprocessing: OpenCV pipeline to maximise OCR accuracy.
"""
import cv2
import numpy as np
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Karan\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
from PIL import Image
from pathlib import Path
from dataclasses import dataclass
import structlog, io, base64

log = structlog.get_logger()

@dataclass
class OCRResult:
    text: str
    confidence: float        # 0.0 – 1.0 average word confidence
    method: str              # "tesseract" | "trocr"
    is_handwritten: bool


class OCRService:
    _trocr_model = None
    _trocr_processor = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def process_image(self, image_bytes: bytes, force_handwritten: bool = False) -> OCRResult:
        """
        Entry point. Accepts raw image bytes.
        Auto-detects handwriting vs print unless force_handwritten=True.
        """
        img_array = self._bytes_to_cv2(image_bytes)
        preprocessed = self._preprocess(img_array)

        is_handwritten = force_handwritten or self._detect_handwriting(preprocessed)

        if is_handwritten:
            return self._run_trocr(preprocessed)
        else:
            return self._run_tesseract(preprocessed)

    # ------------------------------------------------------------------ #
    # Preprocessing                                                        #
    # ------------------------------------------------------------------ #

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Standard preprocessing pipeline:
        grayscale → denoise → binarise → deskew → upscale if needed.
        """
        # 1. Grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 2. Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # 3. Adaptive threshold (binarise) — handles uneven lighting
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # 4. Deskew via Hough transform
        deskewed = self._deskew(binary)

        # 5. Upscale if resolution is too low (target ≥ 300 DPI equivalent)
        h, w = deskewed.shape
        if w < 1000:
            scale = 1000 / w
            deskewed = cv2.resize(
                deskewed, None, fx=scale, fy=scale,
                interpolation=cv2.INTER_CUBIC
            )

        return deskewed

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Detect and correct rotation up to ±15 degrees."""
        coords = np.column_stack(np.where(img > 0))
        if len(coords) < 100:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5:
            return img
        h, w = img.shape
        centre = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(centre, angle, 1.0)
        return cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _detect_handwriting(self, img: np.ndarray) -> bool:
        """
        Heuristic: printed text has uniform stroke width.
        High variance in connected component sizes → likely handwritten.
        """
        _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary)
        if n_labels < 10:
            return False
        widths = stats[1:, cv2.CC_STAT_WIDTH]
        heights = stats[1:, cv2.CC_STAT_HEIGHT]
        cv = (np.std(widths) / (np.mean(widths) + 1e-6))
        return float(cv) > 0.8

    # ------------------------------------------------------------------ #
    # Tesseract (printed)                                                  #
    # ------------------------------------------------------------------ #

    def _run_tesseract(self, img: np.ndarray) -> OCRResult:
        pil_img = Image.fromarray(img)
        config = "--oem 3 --psm 6"   # assume uniform block of text
        data = pytesseract.image_to_data(
            pil_img, config=config,
            output_type=pytesseract.Output.DICT
        )
        text = pytesseract.image_to_string(pil_img, config=config)

        # Average confidence (ignore -1 values for non-word tokens)
        confs = [c for c in data["conf"] if c != -1]
        avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0

        log.info("ocr.tesseract", chars=len(text), confidence=round(avg_conf, 3))
        return OCRResult(
            text=text.strip(),
            confidence=avg_conf,
            method="tesseract",
            is_handwritten=False,
        )

    # ------------------------------------------------------------------ #
    # TrOCR (handwritten) — lazy-loaded to avoid startup cost             #
    # ------------------------------------------------------------------ #

    def _run_trocr(self, img: np.ndarray) -> OCRResult:
        self._load_trocr()
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        import torch

        pil_img = Image.fromarray(img).convert("RGB")
        pixel_values = self._trocr_processor(
            pil_img, return_tensors="pt"
        ).pixel_values

        with torch.no_grad():
            ids = self._trocr_model.generate(pixel_values)

        text = self._trocr_processor.batch_decode(ids, skip_special_tokens=True)[0]
        log.info("ocr.trocr", chars=len(text))
        return OCRResult(
            text=text.strip(),
            confidence=0.7,      # TrOCR doesn't expose token-level confidence
            method="trocr",
            is_handwritten=True,
        )

    def _load_trocr(self):
        if self._trocr_model is not None:
            return
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        log.info("ocr.loading_trocr")
        self._trocr_processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        self._trocr_model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        log.info("ocr.trocr_loaded")

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _bytes_to_cv2(self, data: bytes) -> np.ndarray:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image — unsupported format or corrupted file.")
        return img


ocr_service = OCRService()
