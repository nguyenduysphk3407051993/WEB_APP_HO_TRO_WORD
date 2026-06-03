"""Chuyển đổi LaTeX ↔ MathML (MathType) ↔ OMML (Word Equation).

Sơ đồ chuyển đổi:

    PDF/Ảnh ──pix2tex──► LaTeX
       LaTeX ◄──pandoc──► MathML (MathType dán trực tiếp)
       LaTeX ◄──pandoc──► OMML  (Word Equation, qua file .docx)
"""
from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path

import pypandoc

logger = logging.getLogger(__name__)

_MATHML_TAG_RE = re.compile(r"<math\b[^>]*>.*?</math>", re.DOTALL | re.IGNORECASE)


class ConverterService:
    """Bộ chuyển đổi 2 chiều cho LaTeX / MathML / OMML."""

    def latex_to_mathml(self, latex: str, display: bool = True) -> str:
        """Trả về chuỗi MathML (thẻ <math>) — dùng để dán vào MathType.

        MathType 7+ chấp nhận MathML khi paste, sẽ tự convert thành công thức
        biên tập được. Trên Windows: copy MathML → mở MathType → Edit > Paste.
        """
        wrapper = f"$$\n{latex}\n$$" if display else f"${latex}$"
        html = pypandoc.convert_text(
            wrapper,
            "html",
            format="latex",
            extra_args=["--mathml"],
        )
        match = _MATHML_TAG_RE.search(html)
        if not match:
            raise ValueError("Không trích xuất được MathML từ LaTeX đã cho.")
        mathml = match.group(0)
        if 'xmlns="http://www.w3.org/1998/Math/MathML"' not in mathml:
            mathml = mathml.replace(
                "<math",
                '<math xmlns="http://www.w3.org/1998/Math/MathML"',
                1,
            )
        return mathml

    def mathml_to_latex(self, mathml: str) -> str:
        """MathML → LaTeX (đi qua HTML wrapper vì pandoc không nhận mathml trực tiếp)."""
        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
            f"<body><p>{mathml}</p></body></html>"
        )
        latex = pypandoc.convert_text(html, "latex", format="html")
        latex = latex.strip()
        latex = re.sub(r"^\\\[", "", latex)
        latex = re.sub(r"\\\]$", "", latex)
        latex = re.sub(r"^\$+", "", latex)
        latex = re.sub(r"\$+$", "", latex)
        return latex.strip()

    def latex_to_docx(
        self,
        latex_content: str,
        output_path: Path,
        as_full_document: bool = False,
    ) -> Path:
        """Chuyển LaTeX sang file .docx có công thức OMML (Word Equation).

        Khi mở trong Word, các công thức là native Equation và có thể chỉnh
        sửa. MathType (nếu cài) cũng tự nhận diện và chuyển sang dạng MathType.
        """
        if not as_full_document:
            latex_doc = (
                "\\documentclass{article}\n"
                "\\usepackage{amsmath,amssymb,amsfonts}\n"
                "\\begin{document}\n"
                f"{latex_content}\n"
                "\\end{document}\n"
            )
        else:
            latex_doc = latex_content

        output_path.parent.mkdir(parents=True, exist_ok=True)
        pypandoc.convert_text(
            latex_doc,
            "docx",
            format="latex",
            outputfile=str(output_path),
            extra_args=["--mathml"],
        )
        return output_path

    def docx_to_latex(self, docx_path: Path) -> str:
        """File .docx (chứa OMML/Equation) → LaTeX.

        Lưu ý: MathType OLE binary cũ (object emf) pandoc không đọc được. Nếu
        cần, hãy mở file trong Word mới (>=2016) và chuyển MathType → OMML
        bằng MathType menu 'Convert Equations' trước khi upload.
        """
        latex = pypandoc.convert_file(
            str(docx_path),
            "latex",
            extra_args=["--wrap=preserve"],
        )
        return latex

    def latex_to_mathtype_xml(self, latex: str) -> dict:
        """Chuẩn bị nội dung để paste vào MathType.

        Trả về cả MathML và một đoạn HTML có sẵn xmlns để có thể copy
        toàn bộ trực tiếp vào MathType (chế độ Edit > Paste).
        """
        mathml = self.latex_to_mathml(latex, display=True)
        copy_payload = (
            "<html><body>"
            f"{mathml}"
            "</body></html>"
        )
        return {"mathml": mathml, "html_payload": copy_payload}


converter_service = ConverterService()
