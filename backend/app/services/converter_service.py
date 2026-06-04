"""Chuyen doi LaTeX <-> MathML <-> OMML va Markdown -> DOCX."""
from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import pypandoc

logger = logging.getLogger(__name__)

_MATHML_TAG_RE = re.compile(r"<math\b[^>]*>.*?</math>", re.DOTALL | re.IGNORECASE)
_MARKDOWN_DOCX_FORMAT = (
    "markdown+raw_tex+tex_math_dollars+pipe_tables+grid_tables"
)
_MARKDOWN_TOGGLE_TEX_DOCX_FORMAT = (
    "markdown-raw_tex-tex_math_dollars-tex_math_single_backslash-"
    "tex_math_double_backslash+pipe_tables+grid_tables"
)
_DISPLAY_BRACKET_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)
_INLINE_PAREN_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_DOLLAR_BLOCK_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_DOLLAR_INLINE_RE = re.compile(
    r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)",
    re.DOTALL,
)
_UNICODE_TEX_REPLACEMENTS = {
    "≤": r"\le ",
    "≥": r"\ge ",
    "≠": r"\ne ",
    "≈": r"\approx ",
    "×": r"\times ",
    "÷": r"\div ",
    "·": r"\cdot ",
    "±": r"\pm ",
    "∞": r"\infty ",
    "∈": r"\in ",
    "∉": r"\notin ",
    "⊂": r"\subset ",
    "⊆": r"\subseteq ",
    "∪": r"\cup ",
    "∩": r"\cap ",
    "∀": r"\forall ",
    "∃": r"\exists ",
    "→": r"\to ",
    "⇒": r"\Rightarrow ",
    "⇔": r"\Leftrightarrow ",
    "∑": r"\sum ",
    "∫": r"\int ",
    "√": r"\sqrt ",
    "π": r"\pi ",
    "α": r"\alpha ",
    "β": r"\beta ",
    "γ": r"\gamma ",
    "δ": r"\delta ",
    "Δ": r"\Delta ",
    "θ": r"\theta ",
    "λ": r"\lambda ",
    "μ": r"\mu ",
    "Ω": r"\Omega ",
    "–": "-",
    "—": "-",
    "−": "-",
}


class ConverterService:
    """Bo chuyen doi 2 chieu cho LaTeX / MathML / OMML."""

    def latex_to_mathml(self, latex: str, display: bool = True) -> str:
        """Tra ve chuoi MathML (<math>) de dan vao MathType."""
        wrapper = f"$$\n{latex}\n$$" if display else f"${latex}$"
        html = pypandoc.convert_text(
            wrapper,
            "html",
            format="latex",
            extra_args=["--mathml"],
        )
        match = _MATHML_TAG_RE.search(html)
        if not match:
            raise ValueError("Khong trich xuat duoc MathML tu LaTeX da cho.")
        mathml = match.group(0)
        if 'xmlns="http://www.w3.org/1998/Math/MathML"' not in mathml:
            mathml = mathml.replace(
                "<math",
                '<math xmlns="http://www.w3.org/1998/Math/MathML"',
                1,
            )
        return mathml

    def mathml_to_latex(self, mathml: str) -> str:
        """MathML -> LaTeX (di qua HTML wrapper)."""
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
        """Chuyen LaTeX sang file .docx co cong thuc OMML."""
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

    def markdown_to_docx(self, markdown_content: str, output_path: Path) -> Path:
        """Chuyen Markdown co cong thuc $...$/$$...$$ sang DOCX."""
        payload = markdown_content.strip() or " "
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pypandoc.convert_text(
            payload,
            "docx",
            format=_MARKDOWN_DOCX_FORMAT,
            outputfile=str(output_path),
            extra_args=["--wrap=preserve"],
        )
        return output_path

    def markdown_to_toggle_tex_docx(
        self,
        markdown_content: str,
        output_path: Path,
    ) -> Path:
        """Chuyen Markdown sang DOCX, giu cong thuc o dang TeX text cho MathType Toggle TeX."""
        payload = self._normalize_toggle_tex_markdown(markdown_content.strip() or " ")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pypandoc.convert_text(
            payload,
            "docx",
            format=_MARKDOWN_TOGGLE_TEX_DOCX_FORMAT,
            outputfile=str(output_path),
            extra_args=["--wrap=preserve"],
        )
        return output_path

    @staticmethod
    def _normalize_toggle_tex_markdown(markdown_content: str) -> str:
        """Dua delimiter ve $...$/$$...$$ va lam sach TeX cho MathType Toggle TeX."""
        markdown_content = _DOLLAR_BLOCK_RE.sub(
            lambda match: f"$$\n{ConverterService.sanitize_toggle_tex_latex(match.group(1))}\n$$",
            markdown_content,
        )
        markdown_content = _DISPLAY_BRACKET_RE.sub(
            lambda match: f"$$\n{ConverterService.sanitize_toggle_tex_latex(match.group(1))}\n$$",
            markdown_content,
        )
        markdown_content = _INLINE_PAREN_RE.sub(
            lambda match: f"${ConverterService.sanitize_toggle_tex_latex(match.group(1))}$",
            markdown_content,
        )
        markdown_content = _DOLLAR_INLINE_RE.sub(
            lambda match: f"${ConverterService.sanitize_toggle_tex_latex(match.group(1))}$",
            markdown_content,
        )
        return markdown_content

    @staticmethod
    def sanitize_toggle_tex_latex(latex: str) -> str:
        """Loai Unicode/tieng Viet trong vung TeX de MathType Toggle TeX on dinh hon."""
        latex = latex.strip()
        for source, replacement in _UNICODE_TEX_REPLACEMENTS.items():
            latex = latex.replace(source, replacement)

        latex = latex.replace("đ", "d").replace("Đ", "D")
        latex = unicodedata.normalize("NFKD", latex)
        latex = "".join(char for char in latex if not unicodedata.combining(char))
        latex = latex.encode("ascii", "ignore").decode("ascii")
        latex = re.sub(r"[ \t]+", " ", latex)
        latex = re.sub(r"\s*\n\s*", "\n", latex)
        return latex.strip()

    def docx_to_latex(self, docx_path: Path) -> str:
        """File .docx (chua OMML/Equation) -> LaTeX."""
        latex = pypandoc.convert_file(
            str(docx_path),
            "latex",
            extra_args=["--wrap=preserve"],
        )
        return latex

    def latex_to_mathtype_xml(self, latex: str) -> dict:
        """Chuan bi noi dung de paste vao MathType."""
        mathml = self.latex_to_mathml(latex, display=True)
        copy_payload = "<html><body>" f"{mathml}" "</body></html>"
        return {"mathml": mathml, "html_payload": copy_payload}


converter_service = ConverterService()
