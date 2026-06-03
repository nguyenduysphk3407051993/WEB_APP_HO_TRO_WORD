"""OCR công thức toán dùng Gemini Vision API (qua key pool).

Hỗ trợ:
  - Ảnh đơn ─► LaTeX (toàn bộ công thức + văn bản nếu có)
  - PDF nhiều trang ─► dispatch song song lên các key trong pool
  - Tự retry với key khác khi 429/quota/invalid
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

from PIL import Image

from app.config import settings
from app.services.gemini_pool import ApiKey, GeminiKeyPool, get_pool

logger = logging.getLogger(__name__)

PROMPT_SINGLE_FORMULA = """Bạn là chuyên gia OCR công thức toán học. Hãy trích xuất TOÀN BỘ nội dung trong ảnh thành mã LaTeX chuẩn.

QUY TẮC:
1. Nếu ảnh chỉ chứa 1 công thức: trả về CHỈ mã LaTeX của công thức (không có $ bao quanh, không có giải thích).
2. Nếu ảnh có nhiều công thức/văn bản: giữ nguyên thứ tự, dùng $...$ cho inline math, $$...$$ cho display math.
3. Tiếng Việt giữ nguyên dấu, KHÔNG dịch.
4. Dùng các lệnh LaTeX chuẩn: \\frac, \\sqrt, \\int, \\sum, \\lim, \\sin, \\cos, \\log, \\ln, \\alpha, \\beta...
5. Ma trận dùng \\begin{pmatrix}...\\end{pmatrix} hoặc \\begin{bmatrix}.
6. Hệ phương trình dùng \\begin{cases}...\\end{cases}.
7. KHÔNG thêm markdown code fence (```latex...```).
8. KHÔNG thêm phần giải thích, KHÔNG ghi "Đây là LaTeX:".
9. Nếu có chỉ số trên/dưới phức tạp, dùng dấu {} bao rõ ràng.

CHỈ TRẢ VỀ MÃ LATEX, không gì khác."""

PROMPT_FULL_PAGE = """Bạn là chuyên gia OCR tài liệu khoa học. Hãy trích xuất TOÀN BỘ nội dung trang này thành LaTeX có cấu trúc.

QUY TẮC:
1. Giữ nguyên cấu trúc tài liệu: tiêu đề (\\section, \\subsection), đoạn văn, danh sách (\\begin{itemize}).
2. Công thức inline: $...$. Công thức display: \\[...\\] hoặc $$...$$.
3. Tiếng Việt giữ nguyên dấu, KHÔNG dịch.
4. Bảng biểu dùng \\begin{tabular}.
5. Số thứ tự bài/câu hỏi: giữ nguyên (ví dụ "Bài 1.", "Câu 2:").
6. KHÔNG thêm \\documentclass, \\begin{document}, \\end{document}.
7. KHÔNG thêm markdown code fence.
8. KHÔNG giải thích, chỉ trả về nội dung LaTeX.

CHỈ TRẢ VỀ NỘI DUNG LATEX."""


class GeminiOCRService:
    """OCR service dùng Gemini API qua key pool."""

    def __init__(self, pool: Optional[GeminiKeyPool] = None) -> None:
        self._pool = pool  # lazy lấy từ get_pool() nếu None

    def _get_pool(self) -> GeminiKeyPool:
        return self._pool or get_pool()

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        """Gemini đôi khi trả ```latex ... ``` — bóc ra."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # bỏ dòng đầu (``` hoặc ```latex) và dòng cuối (```)
            if len(lines) >= 2:
                lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
        return text

    async def _call_gemini(
        self,
        key: ApiKey,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
    ) -> str:
        """Gọi Gemini với 1 key cụ thể."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key.key)
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            ),
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
        )
        return self._strip_markdown_fence(response.text or "")

    async def _ocr_with_retry(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
    ) -> str:
        """Acquire key → call → on error: report + retry với key khác."""
        pool = self._get_pool()
        last_exc: Optional[Exception] = None

        for attempt in range(settings.GEMINI_RETRY_ATTEMPTS):
            key = await pool.acquire()
            try:
                async with key.semaphore:
                    result = await self._call_gemini(key, image_bytes, prompt, mime_type)
                await pool.report_success(key)
                logger.info("OCR thành công (attempt %d, key=%s)", attempt + 1, key.preview)
                return result
            except Exception as exc:
                last_exc = exc
                await pool.report_error(key, exc)
                logger.warning(
                    "OCR fail attempt %d (key=%s): %s — thử key khác",
                    attempt + 1, key.preview, str(exc)[:120],
                )
                continue

        raise RuntimeError(
            f"OCR thất bại sau {settings.GEMINI_RETRY_ATTEMPTS} lần thử. "
            f"Lỗi cuối: {last_exc}"
        )

    async def image_to_latex(
        self, image_bytes: bytes, mode: str = "single"
    ) -> str:
        """OCR 1 ảnh sang LaTeX.

        Args:
            mode: "single" (chỉ công thức) hoặc "page" (cả trang có cấu trúc).
        """
        prompt = PROMPT_FULL_PAGE if mode == "page" else PROMPT_SINGLE_FORMULA
        # Chuẩn hóa về PNG để Gemini nhận tốt nhất
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()
        return await self._ocr_with_retry(png_bytes, prompt, "image/png")

    async def pdf_to_latex(
        self,
        pdf_bytes: bytes,
        dpi: int = 200,
        mode: str = "page",
        max_concurrent_pages: int = 10,
    ) -> list[dict]:
        """OCR toàn bộ PDF song song.

        Mỗi trang được render → ảnh → dispatch lên 1 key trong pool.
        max_concurrent_pages giới hạn tổng số trang chạy đồng thời.
        """
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            # Render tất cả trang trước (CPU-bound, nhanh)
            pages_data: list[tuple[int, bytes]] = []
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                pages_data.append((page_index + 1, buf.getvalue()))

            # Dispatch song song lên pool
            sem = asyncio.Semaphore(max_concurrent_pages)
            prompt = PROMPT_FULL_PAGE if mode == "page" else PROMPT_SINGLE_FORMULA

            async def process_page(page_num: int, img_bytes: bytes) -> dict:
                async with sem:
                    try:
                        latex = await self._ocr_with_retry(img_bytes, prompt, "image/png")
                        return {"page": page_num, "latex": latex, "error": None}
                    except Exception as exc:
                        logger.exception("Lỗi OCR trang %d", page_num)
                        return {"page": page_num, "latex": "", "error": str(exc)}

            tasks = [process_page(n, b) for n, b in pages_data]
            results = await asyncio.gather(*tasks)
            results.sort(key=lambda r: r["page"])
            return results
        finally:
            doc.close()


ocr_service = GeminiOCRService()
