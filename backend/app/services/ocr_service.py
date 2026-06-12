"""OCR tài liệu/ảnh qua 9router hoặc Gemini, hỗ trợ xuất LaTeX hoặc nội dung Word."""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Optional

from PIL import Image

from app.config import settings
from app.services.api_key_pool import ApiKey, ApiKeyPool, get_gemini_pool, get_pool
from app.services import gemini_client as _gemini_client
from app.services.ninerouter_client import create_vision_completion, provider_config

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

PROMPT_TEXT_SINGLE = """Ban la chuyen gia OCR tai lieu giao duc Viet Nam. Hay trich xuat noi dung trong anh thanh van ban thuan theo cac quy tac sau.

QUY TAC:
1. TIEN TO CAU HOI: Cac cum tu "Cau N", "Bai N", "Vi du N" (N la so thu tu) PHAI viet CUNG DONG voi noi dung cau hoi, KHONG xuong dong. Vi du dung: "Cau 1. Tim x biet..." --- Vi du SAI: "Cau 1\\nTim x biet..."
2. PHUONG AN: Moi phuong an A, B, C, D tren MOT DONG RIENG. Bat dau bang "A. ", "B. ", "C. ", "D. "
3. CONG THUC INLINE (trong cau): boc trong $...$. Vi du: $x^2 + 1 = 0$
4. CONG THUC DISPLAY (rieng dong): boc trong \\[...\\]. Vi du: \\[ \\frac{x}{2} = 1 \\]
5. Tieng Viet giu nguyen dau, khong dich.
6. KHONG dung markdown (khong #, **, __, ---, code fence, v.v.).
7. KHONG them loi giai thich hay nhan xet.

CHI TRA VE NOI DUNG THUAN."""

PROMPT_TEXT_PAGE = """Ban la chuyen gia OCR tai lieu giao duc Viet Nam. Hay trich xuat toan bo noi dung trang nay thanh van ban thuan theo cac quy tac sau.

QUY TAC:
1. TIEN TO CAU HOI: Cac cum tu "Cau N", "Bai N", "Vi du N" (N la so thu tu) PHAI viet CUNG DONG voi noi dung cau hoi, KHONG xuong dong. Vi du dung: "Cau 1. Tim x biet..." --- Vi du SAI: "Cau 1\\nTim x biet..."
2. PHUONG AN: Moi phuong an A, B, C, D tren MOT DONG RIENG. Bat dau bang "A. ", "B. ", "C. ", "D. "
3. CONG THUC INLINE (trong cau): boc trong $...$. Vi du: Cho $x^2 - 4 = 0$, tim $x$.
4. CONG THUC DISPLAY (cong thuc rieng dong): boc trong \\[...\\]. Vi du: \\[ \\int_0^1 x^2\\,dx = \\frac{1}{3} \\]
5. Tieng Viet giu nguyen dau, khong dich.
6. KHONG dung markdown (khong #, **, __, ---, code fence, v.v.).
7. KHONG them loi mo dau, ket luan hay nhan xet.
8. Cac y nho a., b., c., d. hoac a), b), c), d) dat moi y tren mot dong rieng.

CHI TRA VE NOI DUNG THUAN."""

PROMPT_EXAM_LATEX = """Ban la chuyen gia OCR tai lieu thi cu Viet Nam.
Hay trich xuat noi dung tu anh va chuyen sang dinh dang LaTeX bai tap theo chuan giao duc Viet Nam.

QUY TAC DINH DANG:
1. Moi cau hoi trac nghiem dung moi truong \\begin{ex}...\\end{ex}
2. Truoc moi cau them dong nhan dang: %%%=============EX_N=============%%% (N la so thu tu lien tuc)
3. Phuong an dung lenh \\choice tren 4 dong rieng: \\choice\\n{A}\\n{B}\\n{\\\\True C}\\n{D} voi phuong an dung co \\True phia truoc; neu khong biet dap an dung thi de nguyen (khong \\True)
4. Neu co loi giai trong anh, dua vao \\loigiai{...}; neu khong co, bo qua
5. Cong thuc inline boc trong $...$, cong thuc display boc trong \\[...\\]
6. So thap phan dung {,} ngan phan nguyen va phan thap phan: $1{,}5$ thay vi $1.5$
7. Tieu de bai, cau dan, boi canh giu nguyen truoc cau hoi dau tien
8. Cau hoi dung/sai (True/False 4 y): dung \\choiceTF{a}{b}{c}{d} voi y dung co \\True
9. Tieng Viet giu nguyen dau, khong dich
10. Khong them \\documentclass, \\begin{document}, \\usepackage, code fence, giai thich

VI DU DAU RA:
%%%=============EX_1=============%%%
\\begin{ex}%[ID]
Noi dung cau hoi trac nghiem...
\\choice
{Phuong an A}
{Phuong an B}
{\\True Phuong an C dung}
{Phuong an D}
\\end{ex}

CHI TRA VE CODE LATEX THUAN."""


class OCRService:
    """OCR service dùng 9router hoặc Gemini qua API key pool."""

    def __init__(self, pool: Optional[ApiKeyPool] = None) -> None:
        self._pool = pool

    def _get_pool(self) -> ApiKeyPool:
        if provider_config.provider == "gemini":
            return get_gemini_pool()
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
    def _select_text_prompt(mode: str) -> str:
        return PROMPT_TEXT_PAGE if mode == "page" else PROMPT_TEXT_SINGLE

    @staticmethod
    def _select_exam_latex_prompt(mode: str) -> str:  # noqa: ARG004
        return PROMPT_EXAM_LATEX

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
        if provider_config.provider == "gemini":
            response = await _gemini_client.create_vision_completion(
                api_key=key.key,
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=prompt,
                model=provider_config.model,
            )
        else:
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
        retry_attempts = (
            settings.GEMINI_RETRY_ATTEMPTS
            if provider_config.provider == "gemini"
            else settings.NINEROUTER_RETRY_ATTEMPTS
        )
        last_exc: Optional[Exception] = None

        for attempt in range(retry_attempts):
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
            f"OCR thất bại sau {retry_attempts} lần thử. Lỗi cuối: {last_exc}"
        )

    @staticmethod
    def normalize_plain_text(text: str) -> str:
        """Chuẩn hoá văn bản thuần sau OCR:
        - Gộp 'Câu/Bài/Ví dụ N' đứng riêng dòng vào dòng tiếp theo
        - Tách phương án A/B/C/D nội tuyến ra từng dòng riêng
        - Chuẩn hoá $$...$$ → \\[...\\]
        - Thu gọn dòng trống thừa
        """
        _standalone_prefix = re.compile(
            r"^((?:C[aâ]u|B[aà]i|V[ií][\s\xa0]+d[uụ])\s+\d+[A-Za-z]?(?:\s*[:.)\-])?)\s*$",
            re.IGNORECASE | re.UNICODE,
        )
        _inline_options = re.compile(r"(?<=\S)\s{2,}(?=[A-D][.)])")
        _dollar_block = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)

        lines = text.splitlines()
        merged: list[str] = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if _standalone_prefix.fullmatch(stripped):
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    merged.append(f"{stripped} {lines[j].strip()}")
                    i = j + 1
                    continue
            merged.append(lines[i].rstrip())
            i += 1

        exploded: list[str] = []
        for line in merged:
            parts = _inline_options.split(line)
            if len(parts) > 1:
                exploded.extend(p.strip() for p in parts if p.strip())
            else:
                exploded.append(line)

        result = "\n".join(exploded)
        result = _dollar_block.sub(
            lambda m: f"\\[{m.group(1).strip()}\\]", result
        )
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    async def image_to_text(self, image_bytes: bytes, mode: str = "page") -> str:
        prompt = self._select_text_prompt(mode)
        result = await self._ocr_with_retry(
            self._normalize_image(image_bytes), prompt, "image/png"
        )
        return self.normalize_plain_text(self._strip_markdown_fence(result))

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

    async def pdf_to_text_pages(
        self,
        pdf_bytes: bytes,
        dpi: int = 200,
        mode: str = "page",
        max_concurrent_pages: int = 10,
    ) -> list[dict]:
        prompt = self._select_text_prompt(mode)
        return await self._pdf_to_text_pages(
            pdf_bytes,
            prompt=prompt,
            field_name="text",
            normalizer=self.normalize_plain_text,
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
        normalizer=None,
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
                        if normalizer is not None:
                            text = normalizer(self._strip_markdown_fence(text))
                        else:
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

    async def image_to_exam_latex(self, image_bytes: bytes, mode: str = "page") -> str:
        prompt = self._select_exam_latex_prompt(mode)
        result = await self._ocr_with_retry(
            self._normalize_image(image_bytes), prompt, "image/png"
        )
        return self._strip_markdown_fence(result)

    async def pdf_to_exam_latex_pages(
        self,
        pdf_bytes: bytes,
        dpi: int = 200,
        mode: str = "page",
        max_concurrent_pages: int = 10,
    ) -> list[dict]:
        prompt = self._select_exam_latex_prompt(mode)
        return await self._pdf_to_text_pages(
            pdf_bytes,
            prompt=prompt,
            field_name="latex",
            dpi=dpi,
            max_concurrent_pages=max_concurrent_pages,
        )

    def extract_pdf_images(
        self, pdf_bytes: bytes, output_images_dir: Path
    ) -> dict[int, list[str]]:
        """Trích xuất bytes gốc của ảnh nhúng trong PDF (theo skill exam-docx-creator).
        Trả về {page_num: ['images/page_X_img_Y.ext', ...]}"""
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        output_images_dir.mkdir(parents=True, exist_ok=True)
        extracted: dict[int, list[str]] = {}

        try:
            for page_index in range(len(doc)):
                page_num = page_index + 1
                page = doc.load_page(page_index)
                image_list = page.get_images(full=True)
                page_images: list[str] = []

                for img_idx, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Bỏ qua ảnh quá nhỏ (icon, vạch phân cách, trang trí)
                        if len(image_bytes) < 2048:
                            continue

                        img_name = f"page_{page_num}_img_{img_idx + 1}.{image_ext}"
                        (output_images_dir / img_name).write_bytes(image_bytes)
                        page_images.append(f"images/{img_name}")
                    except Exception as exc:
                        logger.warning(
                            "Loi trich xuat anh xref %s trang %d: %s",
                            img[0], page_num, exc,
                        )

                if page_images:
                    extracted[page_num] = page_images
        finally:
            doc.close()

        return extracted

    def combine_markdown_pages(
        self,
        pages: list[dict],
        extracted_images: dict[int, list[str]] | None = None,
    ) -> str:
        chunks: list[str] = []
        images = extracted_images or {}

        for page in sorted(pages, key=lambda item: item["page"]):
            page_num = page.get("page")
            text = (page.get("markdown") or "").strip()

            # Nhúng ảnh trích xuất vào cuối nội dung trang
            page_imgs = images.get(page_num, [])
            img_md = (
                "\n\n" + "\n\n".join(f"![Hinh minh hoa]({p})" for p in page_imgs)
                if page_imgs else ""
            )

            if text:
                chunks.append(text + img_md)
            else:
                error_text = (page.get("error") or "Khong ro loi").strip()
                if img_md:
                    chunks.append(f"*Trang {page_num} chi co hinh anh:*{img_md}")
                else:
                    chunks.append(
                        f"**Khong the OCR trang {page_num}**\n\n"
                        f"> {error_text[:300]}"
                    )

        content = "\n\n\\newpage\n\n".join(chunk for chunk in chunks if chunk.strip()).strip()
        if not content:
            raise ValueError("Khong trich xuat duoc noi dung nao tu PDF.")
        return content


ocr_service = OCRService()
