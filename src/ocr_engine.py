"""
ocr_engine.py — OCR engine wrapper using PaddleOCR PPStructureV3.

Semua model cache diarahkan ke persistent storage (/data di HF Spaces)
melalui modul storage.py sebelum PaddleOCR diinisialisasi.
"""

# ── MUST be first: redirect model cache BEFORE importing paddleocr ───────────
import os
from storage import ensure_dirs, get_env_overrides

ensure_dirs()
os.environ.update(get_env_overrides())
# ─────────────────────────────────────────────────────────────────────────────

from paddleocr import PPStructureV3
from typing import Union, Dict, Any
import numpy as np
import cv2


class OCREngine:
    def __init__(self, use_lite: bool = True):
        """
        use_lite=True  → mobile model, ~3-5x lebih cepat di CPU
        use_lite=False → server model, akurasi lebih tinggi
        """
        config = self._build_config(use_lite)
        self.pipeline = PPStructureV3(**config)

    def _build_config(self, use_lite: bool) -> dict:
        if use_lite:
            return {
                # Ganti ke model mobile — jauh lebih ringan
                "text_detection_model_name": "PP-OCRv5_mobile_det",
                "text_recognition_model_name": "PP-OCRv5_mobile_rec",
                # Disable komponen yang tidak relevan untuk invoice
                "use_doc_orientation_classify": False,  # invoice biasanya sudah lurus
                "use_doc_unwarping": False,              # skip dewarping
                "use_formula_recognition": False,        # tidak ada formula di invoice
                "use_chart_recognition": False,          # tidak ada chart di invoice
            }
        else:
            return {
                # Server model untuk akurasi max
                "use_formula_recognition": False,
                "use_chart_recognition": False,
            }

    def process_image(
        self,
        image: Union[str, np.ndarray],
        max_size: int = 1600
    ) -> Dict[str, Any]:
        """
        max_size: resize sisi terpanjang gambar ke nilai ini sebelum inference.
        Invoice biasanya teks besar, 1600px sudah sangat cukup.
        """
        if isinstance(image, str):
            image = cv2.imread(image)

        # Resize untuk mempercepat inference — ini impact terbesar kedua setelah model
        image = self._resize_if_needed(image, max_size)

        output = self.pipeline.predict(input=image)

        markdown_list = []
        markdown_images = []
        for res in output:
            md = res.markdown
            markdown_list.append(md)
            markdown_images.extend(md.get("markdown_images", {}).values())

        markdown_text = self.pipeline.concatenate_markdown_pages(markdown_list)
        return {
            "markdown_text": markdown_text,
            "images": markdown_images
        }

    def _resize_if_needed(self, image: np.ndarray, max_size: int) -> np.ndarray:
        h, w = image.shape[:2]
        longest = max(h, w)
        if longest <= max_size:
            return image
        scale = max_size / longest
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)