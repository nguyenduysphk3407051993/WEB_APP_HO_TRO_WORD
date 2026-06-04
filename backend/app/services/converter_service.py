"""Chuyen doi LaTeX <-> MathML <-> OMML va Markdown -> DOCX."""
from __future__ import annotations

from copy import deepcopy
import logging
import re
import unicodedata
from pathlib import Path

import pypandoc
from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn
from docx.shared import Cm, RGBColor
from docx.text.paragraph import Paragraph

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
_QUESTION_PREFIX_RE = re.compile(
    r"^\s*((?:Câu|Bài|Ví dụ)\s+\d+[A-Za-z]?(?:\s*[:.)-])?)",
    re.IGNORECASE,
)
_OPTION_PREFIX_RE = re.compile(r"^\s*([A-D])([.)])\s*(.+?)\s*$")
_SUBITEM_PREFIX_RE = re.compile(r"^\s*([a-d])([.)])\s*(.+?)\s*$")
_INLINE_STRUCTURE_RE = re.compile(
    r"(?<!\S)(?P<option>[A-D][.)])\s+|(?<!\S)(?P<subitem>[a-d][.)])\s+"
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
_QUESTION_PREFIX_COLOR = RGBColor(0x00, 0x70, 0xC0)
_OPTION_MARKER_INDENT = Cm(0.75)
_OPTION_TAB_STOP = Cm(1.35)
_SUBITEM_MARKER_INDENT = Cm(1.0)
_SUBITEM_TAB_STOP = Cm(1.65)


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
        self.postprocess_ocr_docx(output_path)
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
        self.postprocess_ocr_docx(output_path)
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

    def postprocess_ocr_docx(self, docx_path: Path) -> Path:
        """Hau xu ly DOCX OCR de dinh dang cau hoi, phuong an va y nho on dinh hon."""
        document = Document(docx_path)
        original_paragraphs = list(document.paragraphs)

        for paragraph in original_paragraphs:
            if not paragraph.text or not paragraph.text.strip():
                continue

            segments = self._explode_structured_paragraph(paragraph.text)
            current = paragraph

            if len(segments) > 1:
                self._set_paragraph_text(current, segments[0][1])
                self._apply_segment_format(current, segments[0][0])

                for kind, text in segments[1:]:
                    current = self._insert_paragraph_after(current, text)
                    self._apply_segment_format(current, kind)
                continue

            self._set_paragraph_text(current, segments[0][1])
            self._apply_segment_format(current, segments[0][0])

        document.save(docx_path)
        return docx_path

    @staticmethod
    def _explode_structured_paragraph(text: str) -> list[tuple[str, str]]:
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text).strip()
        if not text:
            return [("paragraph", "")]

        segments: list[tuple[str, str]] = []
        question_match = _QUESTION_PREFIX_RE.match(text)

        if question_match:
            first_marker = _INLINE_STRUCTURE_RE.search(text, question_match.end())
            if not first_marker:
                return [("question", text)]

            question_text = text[: first_marker.start()].strip()
            if question_text:
                segments.append(("question", question_text))
            text = text[first_marker.start() :].strip()

        markers = list(_INLINE_STRUCTURE_RE.finditer(text))
        if not markers:
            if segments:
                return segments
            if _OPTION_PREFIX_RE.match(text):
                return [("option", text)]
            if _SUBITEM_PREFIX_RE.match(text):
                return [("subitem", text)]
            return [("paragraph", text)]

        if not segments and markers[0].start() > 0:
            prefix_text = text[: markers[0].start()].strip()
            if prefix_text:
                segments.append(("paragraph", prefix_text))

        for index, marker in enumerate(markers):
            end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
            chunk = text[marker.start() : end].strip()
            if not chunk:
                continue
            kind = "option" if marker.group("option") else "subitem"
            segments.append((kind, chunk))

        return segments or [("paragraph", text)]

    def _apply_segment_format(self, paragraph: Paragraph, kind: str) -> None:
        if kind == "question":
            self._format_question_prefix(paragraph)
            return
        if kind == "option":
            self._format_choice_paragraph(paragraph, is_subitem=False)
            return
        if kind == "subitem":
            self._format_choice_paragraph(paragraph, is_subitem=True)

    def _format_question_prefix(self, paragraph: Paragraph) -> None:
        text = paragraph.text.strip()
        match = _QUESTION_PREFIX_RE.match(text)
        if not match:
            return

        prefix = match.group(1).strip()
        remainder = text[match.end() :].lstrip()
        self._clear_paragraph(paragraph)

        prefix_run = paragraph.add_run(prefix)
        prefix_run.bold = True
        prefix_run.font.color.rgb = _QUESTION_PREFIX_COLOR

        if remainder:
            paragraph.add_run(f" {remainder}")

    def _format_choice_paragraph(self, paragraph: Paragraph, *, is_subitem: bool) -> None:
        text = paragraph.text.strip()
        pattern = _SUBITEM_PREFIX_RE if is_subitem else _OPTION_PREFIX_RE
        match = pattern.match(text)
        if not match:
            return

        marker = "".join(match.groups()[:-1])
        content = match.group(len(match.groups())).strip()
        self._clear_paragraph(paragraph)

        paragraph.add_run(marker)
        paragraph.add_run("\t")
        paragraph.add_run(content)

        fmt = paragraph.paragraph_format
        marker_indent = _SUBITEM_MARKER_INDENT if is_subitem else _OPTION_MARKER_INDENT
        tab_stop = _SUBITEM_TAB_STOP if is_subitem else _OPTION_TAB_STOP
        fmt.left_indent = tab_stop
        fmt.first_line_indent = marker_indent - tab_stop
        self._reset_tab_stops(paragraph)
        fmt.tab_stops.add_tab_stop(
            tab_stop,
            WD_TAB_ALIGNMENT.LEFT,
            WD_TAB_LEADER.SPACES,
        )

    @staticmethod
    def _set_paragraph_text(paragraph: Paragraph, text: str) -> None:
        if paragraph.text == text:
            return
        paragraph.text = text

    @staticmethod
    def _clear_paragraph(paragraph: Paragraph) -> None:
        for child in list(paragraph._p):
            if child.tag == qn("w:pPr"):
                continue
            paragraph._p.remove(child)

    @staticmethod
    def _reset_tab_stops(paragraph: Paragraph) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        tabs = p_pr.find(qn("w:tabs"))
        if tabs is not None:
            p_pr.remove(tabs)

    @staticmethod
    def _insert_paragraph_after(paragraph: Paragraph, text: str) -> Paragraph:
        new_p = deepcopy(paragraph._p)
        for child in list(new_p):
            if child.tag != qn("w:pPr"):
                new_p.remove(child)
        paragraph._p.addnext(new_p)
        new_paragraph = Paragraph(new_p, paragraph._parent)
        if text:
            new_paragraph.add_run(text)
        return new_paragraph

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
