"""OCR tai lieu/anh bang Gemini, ho tro xuat LaTeX hoac noi dung cho Word."""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Optional

from PIL import Image

from app.config import settings
from app.services.gemini_pool import ApiKey, GeminiKeyPool, get_pool

logger = logging.getLogger(__name__)

PROMPT_SINGLE_FORMULA = """Ban la chuyen gia OCR cong thuc toan hoc. Hay trich xuat toan bo noi dung trong anh thanh ma LaTeX chuan.

QUY TAC:
1. Neu anh chi chua 1 cong thuc: tra ve CHI ma LaTeX cua cong thuc, khong co dau $ bao quanh, khong giai thich.
2. Neu anh co nhieu cong thuc/van ban: giu nguyen thu tu, dung $...$ cho inline math, $$...$$ cho display math.
3. Tieng Viet giu nguyen dau, khong dich.
4. Dung cac lenh LaTeX chuan nhu \\frac, \\sqrt, \\int, \\sum, \\lim, \\sin, \\cos, \\log, \\ln.
5. Khong them markdown code fence.
6. Khong them phan giai thich.

CHI TRA VE NOI DUNG LATEX."""

PROMPT_FULL_PAGE = """Ban la chuyen gia OCR tai lieu khoa hoc. Hay trich xuat toan bo noi dung trang nay thanh LaTeX co cau truc.

QUY TAC:
1. Giu nguyen cau truc tai lieu: tieu de, doan van, danh sach, bang bieu neu co.
2. Cong thuc inline dung $...$, cong thuc display dung $$...$$ hoac \\[...\\].
3. Tieng Viet giu nguyen dau, khong dich.
4. Khong them \\documentclass, \\begin{document}, \\end{document}.
5. Khong them markdown code fence.
6. Khong giai thich, chi tra ve noi dung LaTeX.

CHI TRA VE NOI DUNG LATEX."""

PROMPT_WORD_SINGLE = """Ban la chuyen gia OCR tai lieu de chuyen sang Microsoft Word. Hay trich xuat noi dung trong anh thanh Markdown sach, toi uu de doi sang .docx.

QUY TAC:
1. Van ban thuong giu dang doan van Markdown.
2. Cong thuc inline dung $...$, cong thuc rieng dong dung $$...$$.
3. Neu anh chi co 1 cong thuc, chi tra ve $$...$$.
4. Tieu de dung #, ## khi thuc su co tieu de.
5. Danh sach dung - hoac 1.
6. Bang ro rang thi dung bang Markdown.
7. Tieng Viet giu nguyen dau, khong dich.
8. Khong them code fence, khong giai thich, khong chen nhan xet.

CHI TRA VE NOI DUNG MARKDOWN."""

PROMPT_WORD_PAGE = """Ban la chuyen gia OCR tai lieu de chuyen sang Microsoft Word. Hay trich xuat toan bo noi dung trang nay thanh Markdown sach, toi uu de doi sang .docx.

QUY TAC:
1. Bao toan thu tu doc va cau truc tai lieu.
2. Tieu de dung #, ##, ### khi ro rang.
3. Doan van viet bang Markdown thuong.
4. Danh sach dung - hoac 1.
5. Bang ro rang thi dung bang Markdown.
6. Cong thuc inline dung $...$, cong thuc rieng dong dung $$...$$.
7. Tieng Viet giu nguyen dau, khong dich.
8. Khong them code fence, khong them loi mo dau/ket luan, khong giai thich.

CHI TRA VE NOI DUNG MARKDOWN."""


class GeminiOCRService:
    """OCR service dung Gemini API qua key pool."""

    def __init__(self, pool: Optional[GeminiKeyPool] = None) -> None:
        self._pool = pool

    def _get_pool(self) -> GeminiKeyPool:
        return self._pool or get_pool()

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
        return text

    @staticmethod
    def _select_latex_prompt(mode: str) -> str:
        return PROMPT_FULL_PAGE if mode == "page" else PROMPT_SINGLE_FORMULA

    @staticmethod
    def _select_markdown_prompt(mode: str) -> str:
        return PROMPT_WORD_PAGE if mode == "page" else PROMPT_WORD_SINGLE

    @staticmethod
    def _normalize_image(image_bytes: bytes) -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    @staticmethod
    def extract_formulas(text: str, page: int | None = None) -> list[dict]:
        """Tach cac cong thuc LaTeX tu noi dung OCR Markdown/LaTeX."""
        if not text:
            return []

        pattern = re.compile(
            r"(?P<block_dollar>\$\$(?P<block_dollar_body>.+?)\$\$)"
            r"|(?P<block_bracket>\\\[(?P<block_bracket_body>.+?)\\\])"
            r"|(?P<inline_paren>\\\((?P<inline_paren_body>.+?)\\\))"
            r"|(?P<inline_dollar>(?<!\$)\$(?!\$)(?P<inline_dollar_body>.+?)(?<!\$)\$(?!\$))",
            re.DOTALL,
        )

        formulas: list[dict] = []
        for index, match in enumerate(pattern.finditer(text), start=1):
            body = (
                match.group("block_dollar_body")
                or match.group("block_bracket_body")
                or match.group("inline_paren_body")
                or match.group("inline_dollar_body")
                or ""
            ).strip()
            if not body:
                continue

            is_display = bool(
                match.group("block_dollar") or match.group("block_bracket")
            )
            formulas.append(
                {
                    "page": page,
                    "order": index,
                    "latex": body,
                    "display": is_display,
                }
            )
        return formulas

    async def _call_gemini(
        self,
        key: ApiKey,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
    ) -> str:
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
        pool = self._get_pool()
        last_exc: Optional[Exception] = None

        for attempt in range(settings.GEMINI_RETRY_ATTEMPTS):
            key = await pool.acquire()
            try:
                async with key.semaphore:
                    result = await self._call_gemini(key, image_bytes, prompt, mime_type)
                await pool.report_success(key)
                logger.info("OCR thanh cong (attempt %d, key=%s)", attempt + 1, key.preview)
                return result
            except Exception as exc:
                last_exc = exc
                await pool.report_error(key, exc)
                logger.warning(
                    "OCR fail attempt %d (key=%s): %s",
                    attempt + 1,
                    key.preview,
                    str(exc)[:160],
                )

        raise RuntimeError(
            f"OCR that bai sau {settings.GEMINI_RETRY_ATTEMPTS} lan thu. Loi cuoi: {last_exc}"
        )

    async def image_to_latex(self, image_bytes: bytes, mode: str = "single") -> str:
        prompt = self._select_latex_prompt(mode)
        return await self._ocr_with_retry(self._normalize_image(image_bytes), prompt, "image/png")

    async def image_to_markdown(self, image_bytes: bytes, mode: str = "page") -> str:
        prompt = self._select_markdown_prompt(mode)
        return await self._ocr_with_retry(self._normalize_image(image_bytes), prompt, "image/png")

    async def pdf_to_latex(
        self,
        pdf_bytes: bytes,
        dpi: int = 200,
        mode: str = "page",
        max_concurrent_pages: int = 10,
    ) -> list[dict]:
        prompt = self._select_latex_prompt(mode)
        return await self._pdf_to_text_pages(
            pdf_bytes,
            prompt=prompt,
            field_name="latex",
            dpi=dpi,
            max_concurrent_pages=max_concurrent_pages,
        )

    async def pdf_to_markdown_pages(
        self,
        pdf_bytes: bytes,
        dpi: int = 200,
        mode: str = "page",
        max_concurrent_pages: int = 10,
    ) -> list[dict]:
        prompt = self._select_markdown_prompt(mode)
        return await self._pdf_to_text_pages(
            pdf_bytes,
            prompt=prompt,
            field_name="markdown",
            dpi=dpi,
            max_concurrent_pages=max_concurrent_pages,
        )

    async def _pdf_to_text_pages(
        self,
        pdf_bytes: bytes,
        *,
        prompt: str,
        field_name: str,
        dpi: int = 200,
        max_concurrent_pages: int = 10,
    ) -> list[dict]:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pages_data: list[tuple[int, bytes]] = []

            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                pages_data.append((page_index + 1, buf.getvalue()))

            sem = asyncio.Semaphore(max_concurrent_pages)

            async def process_page(page_num: int, img_bytes: bytes) -> dict:
                async with sem:
                    try:
                        text = await self._ocr_with_retry(img_bytes, prompt, "image/png")
                        return {"page": page_num, field_name: text, "error": None}
                    except Exception as exc:
                        logger.exception("Loi OCR trang %d", page_num)
                        return {"page": page_num, field_name: "", "error": str(exc)}

            tasks = [process_page(page_num, img_bytes) for page_num, img_bytes in pages_data]
            results = await asyncio.gather(*tasks)
            results.sort(key=lambda item: item["page"])
            return results
        finally:
            doc.close()

    def combine_markdown_pages(self, pages: list[dict]) -> str:
        chunks: list[str] = []

        for page in sorted(pages, key=lambda item: item["page"]):
            if page.get("markdown"):
                chunks.append(page["markdown"].strip())
            else:
                error_text = (page.get("error") or "Khong ro loi").strip()
                chunks.append(
                    f"**Khong the OCR trang {page['page']}**\n\n"
                    f"> {error_text[:300]}"
                )

        content = "\n\n\\newpage\n\n".join(chunk for chunk in chunks if chunk.strip()).strip()
        if not content:
            raise ValueError("Khong trich xuat duoc noi dung nao tu PDF.")
        return content


ocr_service = GeminiOCRService()
