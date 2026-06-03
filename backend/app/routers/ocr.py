"""Endpoint OCR ảnh / PDF → LaTeX (qua Gemini key pool)."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.services.ocr_service import ocr_service
from app.utils.file_utils import validate_extension

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


@router.post("/image")
async def ocr_image(
    file: UploadFile = File(...),
    mode: str = Form("single", description='"single" = chỉ công thức, "page" = cả trang có cấu trúc'),
) -> dict:
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File quá lớn.")
    try:
        latex = await ocr_service.image_to_latex(content, mode=mode)
    except Exception as exc:
        raise HTTPException(500, f"Lỗi OCR: {exc}") from exc
    return {"latex": latex, "mode": mode}


@router.post("/pdf")
async def ocr_pdf(
    file: UploadFile = File(...),
    dpi: int = Form(200),
    mode: str = Form("page"),
    max_concurrent: int = Form(10, description="Số trang xử lý song song"),
) -> dict:
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File quá lớn.")
    try:
        results = await ocr_service.pdf_to_latex(
            content, dpi=dpi, mode=mode, max_concurrent_pages=max_concurrent
        )
    except Exception as exc:
        raise HTTPException(500, f"Lỗi OCR PDF: {exc}") from exc
    return {
        "pages": results,
        "total": len(results),
        "errors": sum(1 for r in results if r.get("error")),
    }
