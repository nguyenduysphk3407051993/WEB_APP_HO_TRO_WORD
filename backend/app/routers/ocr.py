"""Endpoint OCR: ảnh / PDF → LaTeX."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.services.ocr_service import ocr_service
from app.utils.file_utils import validate_extension

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


@router.post("/image")
async def ocr_image(file: UploadFile = File(...)) -> dict:
    """Upload 1 ảnh chứa công thức → LaTeX."""
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File quá lớn.")
    try:
        latex = ocr_service.image_to_latex(content)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(500, f"Lỗi OCR: {exc}") from exc
    return {"latex": latex}


@router.post("/pdf")
async def ocr_pdf(file: UploadFile = File(...), dpi: int = 200) -> dict:
    """Upload 1 PDF → LaTeX cho từng trang."""
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File quá lớn.")
    try:
        results = ocr_service.pdf_to_latex(content, dpi=dpi)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(500, f"Lỗi OCR PDF: {exc}") from exc
    return {"pages": results, "total": len(results)}
