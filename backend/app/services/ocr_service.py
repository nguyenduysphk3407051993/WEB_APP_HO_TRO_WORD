"""OCR tài liệu/ảnh qua 9router, hỗ trợ xuất LaTeX hoặc nội dung Word."""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Optional

from PIL import Image

from app.config import settings
from app.services.api_key_pool import ApiKey, ApiKeyPool, get_pool
from app.services.ninerouter_client import create_vision_completion

logger = logging.getLogger(__name__)

PROMPT_SINGLE_FORMULA = """Ban la chuyen gia OCR cong thuc toan hoc. Hay trich xuat toan bo noi dung trong anh thanh ma LaTeX chuan.

QUY TAC:
1. Neu anh chi chua 1 cong thuc: tra ve cong thuc display trong cap \\[...\\], khong giai thich.
2. Neu anh co nhieu cong thuc/van ban: giu nguyen thu tu, dung $...$ cho inline math, \\[...\\] cho display math.
3. Tieng Viet giu nguyen dau, khong dich.
4. Dung cac lenh LaTeX chuan nhu \\frac, \\sqrt, \\int, \\sum, \\lim, \\sin, \\cos, \\log, \\ln.
5. Khong them markdown code fence.
6. Khong them phan giai thich.

CHI TRA VE NOI DUNG LATEX."""

PROMPT_FULL_PAGE = """Ban la chuyen gia OCR tai lieu khoa hoc. Hay trich xuat toan bo noi dung trang nay thanh LaTeX co cau truc.

QUY TAC:
1. Giu nguyen cau truc tai lieu: tieu de, doan van, danh sach, bang bieu neu co.
2. Cong thuc inline dung $...$, cong thuc display bat buoc dung \\[...\\].
3. Tieng Viet giu nguyen dau, khong dich.
4. Khong them \\documentclass, \\begin{document}, \\end{document}.
5. Khong them markdown code fence.
6. Khong giai thich, chi tra ve noi dung LaTeX.

CHI TRA VE NOI DUNG LATEX."""

PROMPT_WORD_SINGLE = """Ban la chuyen gia OCR tai lieu de chuyen sang Microsoft Word. Hay trich xuat noi dung trong anh thanh Markdown sach, toi uu de doi sang .docx.

QUY TAC:
1. Van ban thuong giu dang doan van Markdown.
2. Cong thuc inline dung $...$, cong thuc rieng dong bat buoc dung \\[...\\].
3. Neu anh chi co 1 cong thuc, chi tra ve \\[...\\].
4. Tieu de dung #, ## khi thuc su co tieu de.
5. Danh sach dung - hoac 1.
6. Bang ro rang thi dung bang Markdown.
7. Tieng Viet giu nguyen dau, khong dich.
8. Khong dua chu tieng Viet vao trong $...$ hoac \\[...\\]. Neu co chu giai thich tieng Viet gan cong thuc, tach ra ngoai cong thuc thanh van ban thuong.
9. Neu bat buoc phai co chu trong cong thuc, dung ASCII khong dau trong \\text{...} de MathType Toggle TeX khong loi.
10. Khong them code fence, khong giai thich, khong chen nhan xet.
11. Neu la cau trac nghiem co phuong an A., B., C., D. thi dat moi phuong an tren mot dong rieng.
12. Neu co cac y nho a., b., c., d. hoac a), b), c), d) thi dat moi y tren mot dong rieng.

CHI TRA VE NOI DUNG MARKDOWN."""

PROMPT_WORD_PAGE = """Ban la chuyen gia OCR tai lieu de chuyen sang Microsoft Word. Hay trich xuat toan bo noi dung trang nay thanh Markdown sach, toi uu de doi sang .docx.

QUY TAC:
1. Bao toan thu tu doc va cau truc tai lieu.
2. Tieu de dung #, ##, ### khi ro rang.
3. Doan van viet bang Markdown thuong.
4. Danh sach dung - hoac 1.
5. Bang ro rang thi dung bang Markdown.
6. Cong thuc inline dung $...$, cong thuc rieng dong bat buoc dung \\[...\\].
7. Tieng Viet giu nguyen dau, khong dich.
8. Khong dua chu tieng Viet vao trong $...$ hoac \\[...\\]. Neu co chu giai thich tieng Viet gan cong thuc, tach ra ngoai cong thuc thanh van ban thuong.
9. Neu bat buoc phai co chu trong cong thuc, dung ASCII khong dau trong \\text{...} de MathType Toggle TeX khong loi.
10. Khong them code fence, khong them loi mo dau/ket luan, khong giai thich.
11. Neu la cau trac nghiem co phuong an A., B., C., D. thi dat moi phuong an tren mot dong rieng.
12. Neu co cac y nho a., b., c., d. hoac a), b), c), d) thi dat moi y tren mot dong rieng.

CHI TRA VE NOI DUNG MARKDOWN."""


class OCRService:
    """OCR service dùng 9router qua API key pool."""

    def __init__(self, pool: Optional[ApiKeyPool] = None) -> None:
        self._pool = pool

    def _get_pool(self) -> ApiKeyPool:
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
    def _normalize_display_delimiters(text: str, *, wrap_bare: bool = False) -> str:
        """Chuan hoa display math ve duy nhat cap \\[...\\]."""
        text = re.sub(
            r"\$\$(.+?)\$\$",
            lambda match: f"\\[\n{match.group(1).strip()}\n\\]",
            text.strip(),
            flags=re.DOTALL,
        )
        if wrap_bare and text:
            bracket_match = re.fullmatch(r"\\\[(.+?)\\\]", text, re.DOTALL)
            if bracket_match:
                body = bracket_match.group(1).strip()
            else:
                inline_match = re.fullmatch(
                    r"(?:\\\((.+?)\\\)|(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$))",
                    text,
                    re.DOTALL,
                )
                body = (
                    inline_match.group(1) or inline_match.group(2)
                    if inline_match
                    else text
                ).strip()
            return f"\\[\n{body}\n\\]"
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

    async def _call_provider(
        self,
        key: ApiKey,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
    ) -> str:
        response = await create_vision_completion(
            api_key=key.key,
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt,
        )
        return self._strip_markdown_fence(response)

    async def _ocr_with_retry(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/png",
    ) -> str:
        pool = self._get_pool()
        last_exc: Optional[Exception] = None

        for attempt in range(settings.NINEROUTER_RETRY_ATTEMPTS):
            key = await pool.acquire()
            try:
                async with key.semaphore:
                    result = await self._call_provider(key, image_bytes, prompt, mime_type)
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
            f"OCR thất bại sau {settings.NINEROUTER_RETRY_ATTEMPTS} lần thử. Lỗi cuối: {last_exc}"
        )

    async def image_to_latex(self, image_bytes: bytes, mode: str = "single") -> str:
        prompt = self._select_latex_prompt(mode)
        result = await self._ocr_with_retry(
            self._normalize_image(image_bytes), prompt, "image/png"
        )
        return self._normalize_display_delimiters(result, wrap_bare=mode == "single")

    async def image_to_markdown(self, image_bytes: bytes, mode: str = "page") -> str:
        prompt = self._select_markdown_prompt(mode)
        result = await self._ocr_with_retry(
            self._normalize_image(image_bytes), prompt, "image/png"
        )
        return self._normalize_display_delimiters(result, wrap_bare=mode == "single")

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
                        text = self._normalize_display_delimiters(text)
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


ocr_service = OCRService()
