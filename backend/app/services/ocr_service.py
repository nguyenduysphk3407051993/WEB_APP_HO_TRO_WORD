"""OCR công thức toán: ảnh/PDF → LaTeX."""
from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class OCRService:
    """Wrapper quanh pix2tex để OCR công thức toán sang LaTeX.

    Model được lazy-load lần đầu sử dụng để giảm thời gian khởi động server.
    """

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from pix2tex.cli import LatexOCR
            logger.info("Đang tải model pix2tex...")
            self._model = LatexOCR()
            logger.info("Model pix2tex sẵn sàng.")
        return self._model

    def image_to_latex(self, image_bytes: bytes) -> str:
        """Chuyển 1 ảnh chứa công thức sang LaTeX."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        model = self._get_model()
        latex = model(img)
        return latex.strip()

    def pil_to_latex(self, img: Image.Image) -> str:
        model = self._get_model()
        return model(img.convert("RGB")).strip()

    def pdf_to_latex(self, pdf_bytes: bytes, dpi: int = 200) -> list[dict]:
        """Chuyển PDF nhiều trang sang danh sách kết quả LaTeX theo trang.

        Mỗi trang được render thành ảnh rồi OCR. Trả về list các dict
        {page: int, latex: str}.
        """
        import fitz  # PyMuPDF

        results: list[dict] = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                try:
                    latex = self.pil_to_latex(img)
                except Exception as exc:  # pragma: no cover - log và tiếp tục
                    logger.exception("Lỗi OCR trang %d", page_index + 1)
                    latex = f"% Lỗi OCR trang {page_index + 1}: {exc}"
                results.append({"page": page_index + 1, "latex": latex})
        finally:
            doc.close()
        return results

    def pdf_region_to_latex(
        self,
        pdf_bytes: bytes,
        page_number: int,
        bbox: tuple[float, float, float, float],
        dpi: int = 220,
    ) -> str:
        """OCR một vùng (bbox theo tỉ lệ 0-1) trên 1 trang PDF."""
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = doc.load_page(page_number - 1)
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            x0, y0, x1, y1 = bbox
            w, h = img.size
            crop = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
            return self.pil_to_latex(crop)
        finally:
            doc.close()


ocr_service = OCRService()
