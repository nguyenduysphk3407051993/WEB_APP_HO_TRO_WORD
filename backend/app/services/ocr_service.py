"""OCR tài liệu/ảnh qua 9router hoặc Gemini, hỗ trợ xuất LaTeX hoặc nội dung Word."""
from __future__ import annotations

import asyncio
import io
import logging
import re
from typing import Optional

import numpy as np
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

    # Nhận diện nhãn câu hỏi để chèn ảnh đúng vị trí
    _PDF_QUESTION_RE = re.compile(r"^\s*(?:Câu|Bài|Ví dụ)\s*0*(\d+)", re.IGNORECASE)
    _MD_QUESTION_RE = re.compile(
        r"^\s*[#>*\s]*(?:\*\*)?\s*(?:Câu|Bài|Ví dụ)\s*0*(\d+)", re.IGNORECASE
    )

    # Ngưỡng nhận diện hình vẽ thật (đơn vị point, 1pt ≈ 0.353mm)
    _FIG_MIN_W = 45.0       # hình hẹp hơn → là mảnh công thức/ký hiệu
    _FIG_MIN_H = 38.0       # thấp hơn → dòng công thức/gạch phân số (công thức ≤ ~35pt)
    _FIG_MIN_PATHS = 3      # tam giác = 3 đường; cluster ít nét hơn → ký hiệu lẻ
    _FIG_MAX_W_RATIO = 0.92  # rộng hơn 92% bề ngang trang → dải/bảng full-width
    _FIG_MAX_AREA_RATIO = 0.75  # lớn hơn 75% diện tích trang → scan nguyên trang

    @staticmethod
    def _cluster_rects(rects: list, margin: float = 6.0) -> list:
        """Gộp các rect gần nhau / chồng lấp thành (vùng_tổng_hợp, số_nét)."""
        import fitz
        if not rects:
            return []
        expanded = [fitz.Rect(r.x0 - margin, r.y0 - margin, r.x1 + margin, r.y1 + margin) for r in rects]
        used = [False] * len(expanded)
        clusters = []
        for i, r in enumerate(expanded):
            if used[i]:
                continue
            cluster = fitz.Rect(r)
            used[i] = True
            count = 1
            changed = True
            while changed:
                changed = False
                for j, r2 in enumerate(expanded):
                    if used[j]:
                        continue
                    if cluster.intersects(r2):
                        cluster |= r2
                        used[j] = True
                        count += 1
                        changed = True
            clusters.append((cluster, count))
        return clusters

    def _is_real_figure(self, rect, page_rect) -> bool:
        """Phân biệt hình vẽ thật với công thức / scan nguyên trang / bảng full-width."""
        pw = page_rect.width
        parea = page_rect.width * page_rect.height
        if rect.width < self._FIG_MIN_W or rect.height < self._FIG_MIN_H:
            return False  # mảnh công thức / ký hiệu nhỏ
        if rect.width > self._FIG_MAX_W_RATIO * pw:
            return False  # dải scan / bảng chiếm gần hết bề ngang
        if rect.width * rect.height > self._FIG_MAX_AREA_RATIO * parea:
            return False  # ảnh scan nguyên trang
        # Dải ngang thấp & rộng → dòng công thức (căn lồng, phân số nhiều tầng),
        # không phải hình. Hình vẽ thật thường vuông hoặc cao (h ≥ 60 hoặc w/h ≤ 2).
        if rect.height < 60 and (rect.width / rect.height) > 2.0:
            return False
        return True

    @classmethod
    def _detect_page_questions(cls, page) -> list[tuple[int, float]]:
        """Tìm các nhãn 'Câu/Bài/Ví dụ N' trên trang kèm toạ độ y (đầu khối).
        Trả về list (số_câu, y0) đã sắp theo y tăng dần."""
        out: list[tuple[int, float]] = []
        try:
            for block in page.get_text("blocks"):
                text = block[4] if len(block) > 4 else ""
                y0 = float(block[1])
                for line in str(text).splitlines():
                    m = cls._PDF_QUESTION_RE.match(line)
                    if m:
                        out.append((int(m.group(1)), y0))
                        break
        except Exception:
            pass
        out.sort(key=lambda t: t[1])
        return out

    @staticmethod
    def _figure_owner(fig_top: float, questions: list[tuple[int, float]]) -> int | None:
        """Câu nào sở hữu hình: câu có nhãn nằm ngay trên (gần nhất) hình."""
        if not questions:
            return None
        owner = None
        for num, y0 in questions:  # đã sắp theo y tăng dần
            if y0 <= fig_top + 12:  # nhãn câu nằm tại/trên đỉnh hình
                owner = num
            else:
                break
        if owner is None:
            owner = questions[0][0]  # hình nằm trên câu đầu → gán câu đầu
        return owner

    @staticmethod
    def _merge_boxes(boxes: list, gap: int = 25) -> list:
        """Gộp các bbox chồng/gần nhau (cách ≤ gap) thành một."""
        boxes = [list(b) for b in boxes]
        changed = True
        while changed:
            changed = False
            out: list = []
            while boxes:
                a = boxes.pop()
                merged = False
                for o in out:
                    if (a[0] <= o[2] + gap and o[0] <= a[2] + gap
                            and a[1] <= o[3] + gap and o[1] <= a[3] + gap):
                        o[0], o[1] = min(o[0], a[0]), min(o[1], a[1])
                        o[2], o[3] = max(o[2], a[2]), max(o[3], a[3])
                        changed = True
                        merged = True
                        break
                if not merged:
                    out.append(a)
            boxes = out
        return boxes

    @classmethod
    def _detect_figures_in_array(cls, gray) -> list:
        """Phát hiện vùng HÌNH VẼ trên ảnh trang (numpy) — dùng cho trang scan.
        Ý tưởng: hình vẽ có ĐƯỜNG THẲNG DÀI (cạnh, trục), chữ thì không.
        Trả về list (x0, y0, x1, y1) theo pixel của ảnh đầu vào."""
        from scipy import ndimage

        H, W = gray.shape
        ink = gray < 160
        if int(ink.sum()) < 50:
            return []

        # Giữ pixel thuộc đoạn thẳng ngang/dọc dài >= T (mở hình thái)
        T = max(30, W // 38)
        gh = ndimage.binary_opening(ink, structure=np.ones((1, T), dtype=bool))
        gv = ndimage.binary_opening(ink, structure=np.ones((T, 1), dtype=bool))
        graphic = gh | gv
        if not graphic.any():
            return []

        # Nối các nét đường thành khối, gắn nhãn
        dil = ndimage.binary_dilation(graphic, iterations=max(6, W // 140))
        lbl, n = ndimage.label(dil)
        if n == 0:
            return []

        min_w, min_h = max(60, W // 28), max(60, H // 35)
        raw: list = []
        for sl in ndimage.find_objects(lbl):
            if sl is None:
                continue
            y0, y1 = sl[0].start, sl[0].stop
            x0, x1 = sl[1].start, sl[1].stop
            w, h = x1 - x0, y1 - y0
            if w < min_w or h < min_h:
                continue
            if w > 0.92 * W:            # full-width → bảng / dòng kẻ
                continue
            if w * h > 0.6 * W * H:     # gần cả trang
                continue
            raw.append([x0, y0, x1, y1])

        figures: list = []
        for x0, y0, x1, y1 in cls._merge_boxes(raw, gap=25):
            sub_g = int(graphic[y0:y1, x0:x1].sum())
            sub_i = int(ink[y0:y1, x0:x1].sum())
            if sub_i <= 0:
                continue
            # Chữ trong khung → đường thẳng dài KHÔNG chiếm đa số ink → loại
            if sub_g / sub_i < 0.45 or (y1 - y0) < 60:
                continue
            # Bảng/lưới → nhiều đường ngang VÀ dọc đều đặn → loại
            bw, bh = x1 - x0, y1 - y0
            h_rows = gh[y0:y1, x0:x1].sum(axis=1) > 0.30 * bw
            v_cols = gv[y0:y1, x0:x1].sum(axis=0) > 0.30 * bh
            h_lines = ndimage.label(h_rows)[1]
            v_lines = ndimage.label(v_cols)[1]
            if h_lines >= 6 and v_lines >= 4:
                continue
            figures.append((x0, y0, x1, y1))
        return figures

    def _extract_scanned_figures(
        self, page, page_num: int, output_images_dir: Path
    ) -> list[dict]:
        """Render trang scan ra bitmap, phát hiện & crop hình vẽ chìm trong ảnh."""
        import fitz

        zoom = max(2.0, min(4.0, 1700.0 / page.rect.width))
        pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
        gray = np.asarray(img.convert("L"))

        results: list[dict] = []
        boxes = self._detect_figures_in_array(gray)
        pad = max(4, pm.width // 100)
        for idx, (x0, y0, x1, y1) in enumerate(boxes):
            cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
            cx1, cy1 = min(pm.width, x1 + pad), min(pm.height, y1 + pad)
            crop = img.crop((cx0, cy0, cx1, cy1))
            img_name = f"page_{page_num}_fig_{idx + 1}.png"
            crop.save(output_images_dir / img_name)
            y_frac = ((y0 + y1) / 2.0) / pm.height
            results.append(
                {"path": f"images/{img_name}", "question": None, "y_frac": y_frac}
            )
        return results

    def extract_pdf_images(
        self, pdf_bytes: bytes, output_images_dir: Path
    ) -> dict[int, list[dict]]:
        """Crop đúng hình vẽ (hình học, đồ thị, biểu đồ) trong PDF.
        - PDF số: tách hình từ đối tượng vector/ảnh nhúng (get_drawings/get_image_info)
        - PDF scan: render trang → phân tích ảnh tìm vùng hình (đường thẳng dài)
        Xác định câu sở hữu (PDF số theo toạ độ text; scan theo vị trí dọc).
        Trả về {page_num: [{'path', 'question': N|None, 'y_frac'?}, ...]}"""
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        output_images_dir.mkdir(parents=True, exist_ok=True)
        extracted: dict[int, list[dict]] = {}
        mat = fitz.Matrix(2.0, 2.0)  # 2× resolution để giữ nét
        pad = 4.0  # đệm để không cắt mất nhãn điểm A,B,C / trục toạ độ

        try:
            for page_index in range(len(doc)):
                page_num = page_index + 1
                page = doc.load_page(page_index)
                page_rect = page.rect
                questions = self._detect_page_questions(page)
                regions: list = []

                # ── Ảnh raster đặt trên trang (ảnh thật, không phải scan/công thức) ──
                try:
                    for info in page.get_image_info(xrefs=True):
                        bbox = info.get("bbox")
                        if not bbox:
                            continue
                        r = fitz.Rect(bbox)
                        if self._is_real_figure(r, page_rect):
                            regions.append(r)
                except Exception:
                    pass

                # ── Hình vector (hình học, đồ thị): cluster các nét gần nhau ──
                try:
                    vec_rects = []
                    for d in page.get_drawings():
                        r = d.get("rect")
                        if not r:
                            continue
                        rr = fitz.Rect(r)
                        # Giữ cả đường thẳng ngang/dọc (w=0 hoặc h=0) — chỉ bỏ điểm.
                        # is_empty coi line là rỗng nên KHÔNG dùng ở đây.
                        if rr.width <= 0 and rr.height <= 0:
                            continue
                        vec_rects.append(rr)
                    for cluster, count in self._cluster_rects(vec_rects, margin=6):
                        if count >= self._FIG_MIN_PATHS and self._is_real_figure(cluster, page_rect):
                            regions.append(cluster)
                except Exception:
                    pass

                page_images: list[dict] = []
                for idx, rect in enumerate(regions):
                    try:
                        owner = self._figure_owner(rect.y0, questions)
                        rect = fitz.Rect(
                            rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad
                        ) & page_rect
                        if rect.is_empty:
                            continue
                        pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
                        img_name = f"page_{page_num}_img_{idx + 1}.png"
                        (output_images_dir / img_name).write_bytes(pix.tobytes("png"))
                        page_images.append({"path": f"images/{img_name}", "question": owner})
                    except Exception as exc:
                        logger.warning("Loi render vung hinh trang %d idx %d: %s", page_num, idx, exc)

                # Không có hình từ đối tượng PDF → có thể là trang scan:
                # phân tích chính ảnh render để tìm hình vẽ chìm trong bitmap.
                if not page_images:
                    try:
                        page_images = self._extract_scanned_figures(
                            page, page_num, output_images_dir
                        )
                    except Exception as exc:
                        logger.warning("Loi phat hien hinh trang scan %d: %s", page_num, exc)

                if page_images:
                    extracted[page_num] = page_images
        finally:
            doc.close()

        return extracted

    @staticmethod
    def _img_md(path: str) -> str:
        return f"![Hinh minh hoa]({path})"

    @classmethod
    def _embed_images_by_question(cls, text: str, figures: list) -> str:
        """Chèn ảnh ngay sau khối câu hỏi sở hữu nó (cuối khối, trước câu kế tiếp).
        Ảnh không xác định được câu → dồn xuống cuối trang."""
        # Chuẩn hoá: chấp nhận cả list[str] lẫn list[dict]
        norm = [
            ({"path": f, "question": None} if isinstance(f, str) else f)
            for f in figures
        ]
        lines = text.split("\n")

        # Vị trí dòng bắt đầu mỗi số câu (lần xuất hiện đầu), theo thứ tự xuất hiện
        q_first: dict[int, int] = {}
        starts: list[int] = []
        q_order: list[int] = []  # số câu theo thứ tự dọc
        for i, line in enumerate(lines):
            m = cls._MD_QUESTION_RE.match(line)
            if m:
                num = int(m.group(1))
                if num not in q_first:
                    q_first[num] = i
                    q_order.append(num)
                starts.append(i)

        def block_end(num) -> int | None:
            idx = q_first.get(num)
            if idx is None:
                return None
            after = [s for s in starts if s > idx]
            return min(after) if after else len(lines)

        def owner_by_yfrac(yf: float):
            # Trang scan không có toạ độ câu → gán theo vị trí dọc tương đối
            if not q_order:
                return None
            k = int(yf * len(q_order))
            k = max(0, min(len(q_order) - 1, k))
            return q_order[k]

        inserts: dict[int, list[str]] = {}
        tail: list[str] = []
        for fig in norm:
            md = cls._img_md(fig.get("path"))
            q = fig.get("question")
            if q is None and fig.get("y_frac") is not None:
                q = owner_by_yfrac(float(fig["y_frac"]))
            end = block_end(q) if q is not None else None
            if end is None:
                tail.append(md)
            else:
                inserts.setdefault(end, []).append(md)

        out: list[str] = []
        for i, line in enumerate(lines):
            for md in inserts.get(i, []):
                out.extend(["", md, ""])
            out.append(line)
        for md in inserts.get(len(lines), []):
            out.extend(["", md])
        for md in tail:
            out.extend(["", md])
        return "\n".join(out)

    def combine_markdown_pages(
        self,
        pages: list[dict],
        extracted_images: dict[int, list[dict]] | None = None,
    ) -> str:
        chunks: list[str] = []
        images = extracted_images or {}

        for page in sorted(pages, key=lambda item: item["page"]):
            page_num = page.get("page")
            text = (page.get("markdown") or "").strip()
            page_imgs = images.get(page_num, [])

            if text:
                # Chèn ảnh đúng vị trí câu hỏi (thay vì dồn cuối trang)
                chunks.append(
                    self._embed_images_by_question(text, page_imgs) if page_imgs else text
                )
            else:
                error_text = (page.get("error") or "Khong ro loi").strip()
                if page_imgs:
                    imgs_md = "\n\n".join(
                        self._img_md(f if isinstance(f, str) else f.get("path"))
                        for f in page_imgs
                    )
                    chunks.append(f"*Trang {page_num} chi co hinh anh:*\n\n{imgs_md}")
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
