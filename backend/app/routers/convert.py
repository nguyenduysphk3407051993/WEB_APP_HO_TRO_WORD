"""Endpoint chuyển đổi: LaTeX ↔ MathType ↔ Word Equation."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.services.converter_service import converter_service
from app.services.docx_service import docx_service
from app.utils.file_utils import new_output_path, save_upload

router = APIRouter(prefix="/api/convert", tags=["Convert"])


class LatexInput(BaseModel):
    latex: str = Field(..., description="Mã LaTeX (có thể là 1 công thức hoặc cả tài liệu)")
    display: bool = Field(default=True, description="True = display math, False = inline")


class MathmlInput(BaseModel):
    mathml: str = Field(..., description="Chuỗi MathML (thẻ <math>...</math>)")


@router.post("/latex-to-mathml")
async def latex_to_mathml(payload: LatexInput) -> dict:
    """LaTeX → MathML (dán trực tiếp vào MathType)."""
    try:
        mathml = converter_service.latex_to_mathml(payload.latex, display=payload.display)
    except Exception as exc:
        raise HTTPException(400, f"Không chuyển được: {exc}") from exc
    return {"mathml": mathml}


@router.post("/latex-to-mathtype")
async def latex_to_mathtype(payload: LatexInput) -> dict:
    """LaTeX → payload MathType (MathML + HTML để copy thẳng vào MathType)."""
    try:
        result = converter_service.latex_to_mathtype_xml(payload.latex)
    except Exception as exc:
        raise HTTPException(400, f"Không chuyển được: {exc}") from exc
    return result


@router.post("/mathml-to-latex")
async def mathml_to_latex(payload: MathmlInput) -> dict:
    """MathML → LaTeX."""
    try:
        latex = converter_service.mathml_to_latex(payload.mathml)
    except Exception as exc:
        raise HTTPException(400, f"Không chuyển được: {exc}") from exc
    return {"latex": latex}


@router.post("/latex-to-docx")
async def latex_to_docx(payload: LatexInput) -> FileResponse:
    """LaTeX → file .docx có Word Equation (OMML)."""
    out = new_output_path(".docx")
    try:
        converter_service.latex_to_docx(payload.latex, out)
    except Exception as exc:
        raise HTTPException(400, f"Không chuyển được: {exc}") from exc
    return FileResponse(
        path=str(out),
        filename="output.docx",
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )


@router.post("/docx-to-latex")
async def docx_to_latex(file: UploadFile = File(...)) -> dict:
    """File .docx (Equation/MathType) → LaTeX."""
    path = await save_upload(file, settings.ALLOWED_DOCX_EXTENSIONS)
    has_ole = docx_service.has_mathtype_ole(path)
    try:
        latex = converter_service.docx_to_latex(path)
    except Exception as exc:
        raise HTTPException(400, f"Không chuyển được: {exc}") from exc
    return {
        "latex": latex,
        "warning": (
            "File có chứa MathType OLE binary cũ — phần này không chuyển được tự động. "
            "Hãy mở file trong Word, dùng MathType > Convert Equations → 'Office Math' "
            "rồi upload lại."
        ) if has_ole else None,
    }


@router.post("/docx-extract-equations")
async def docx_extract_equations(file: UploadFile = File(...)) -> dict:
    """Liệt kê công thức OMML trong file .docx (kèm cảnh báo nếu có OLE binary)."""
    path = await save_upload(file, settings.ALLOWED_DOCX_EXTENSIONS)
    equations = docx_service.extract_equations(path)
    return {"equations": equations, "total": len(equations)}
