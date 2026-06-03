"""Xử lý file .docx: trích xuất công thức (OMML/MathType) và tạo docx mới có công thức."""
from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path
from typing import Iterable

from lxml import etree

logger = logging.getLogger(__name__)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "o": "urn:schemas-microsoft-com:office:office",
}

# XSLT chuẩn của Microsoft chuyển OMML → MathML thường nằm trong gói Office
# (OMML2MML.XSL). Để chạy hoàn toàn nhúng, ta dùng pandoc cho việc chuyển đổi
# nội dung text + công thức.


class DocxService:
    """Đọc/ghi .docx tập trung vào công thức toán."""

    def extract_equations(self, docx_path: Path) -> list[dict]:
        """Liệt kê các công thức OMML có trong .docx.

        Trả về list dict: {index, omml_xml, plain_text}.
        Công thức MathType OLE binary cũ sẽ được phát hiện và đánh dấu
        không hỗ trợ trực tiếp.
        """
        results: list[dict] = []
        with zipfile.ZipFile(docx_path) as z:
            try:
                document_xml = z.read("word/document.xml")
            except KeyError as exc:  # pragma: no cover
                raise ValueError("File .docx không hợp lệ (thiếu document.xml)") from exc

            tree = etree.fromstring(document_xml)

            for idx, om in enumerate(tree.iter(f"{{{NS['m']}}}oMath"), start=1):
                xml_str = etree.tostring(om, pretty_print=True).decode("utf-8")
                plain = "".join(om.itertext())
                results.append({"index": idx, "omml_xml": xml_str, "plain_text": plain})

            for idx, om in enumerate(tree.iter(f"{{{NS['m']}}}oMathPara"), start=1):
                xml_str = etree.tostring(om, pretty_print=True).decode("utf-8")
                plain = "".join(om.itertext())
                results.append(
                    {"index": f"para-{idx}", "omml_xml": xml_str, "plain_text": plain}
                )

            ole_count = 0
            for obj in tree.iter(f"{{{NS['w']}}}object"):
                ole_count += 1
            if ole_count:
                results.append(
                    {
                        "index": "_warning",
                        "omml_xml": "",
                        "plain_text": (
                            f"Phát hiện {ole_count} đối tượng MathType OLE binary. "
                            "Chuyển sang OMML trong Word (Convert Equations) trước khi xử lý."
                        ),
                    }
                )

        return results

    def has_mathtype_ole(self, docx_path: Path) -> bool:
        """Kiểm tra docx có chứa MathType OLE binary cũ hay không."""
        with zipfile.ZipFile(docx_path) as z:
            try:
                doc = z.read("word/document.xml")
            except KeyError:
                return False
            return b"<w:object" in doc or b"OLEObject" in doc

    def list_embedded_files(self, docx_path: Path) -> list[str]:
        """Liệt kê các file nhúng (thường nằm trong word/embeddings/)."""
        with zipfile.ZipFile(docx_path) as z:
            return [n for n in z.namelist() if n.startswith("word/embeddings/")]


docx_service = DocxService()
