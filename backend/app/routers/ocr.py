"""Endpoint OCR anh/PDF -> LaTeX hoac Word (.docx) kem cong thuc LaTeX/MathML."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.services.converter_service import converter_service
from app.services.ocr_service import ocr_service
from app.utils.file_utils import new_output_path, validate_extension

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _validate_mode(mode: str) -> str:
    if mode not in {"single", "page"}:
        raise HTTPException(400, 'Mode khong hop le. Chi nhan "single" hoac "page".')
    return mode


def _build_download_name(filename: str | None, fallback: str) -> str:
    stem = Path(filename or fallback).stem or fallback
    return f"{stem}.docx"


def _build_download_url(output_path: Path) -> str:
    return f"/api/ocr/download/{output_path.name}"


def _validate_output_name(file_name: str) -> Path:
    candidate = Path(file_name).name
    if candidate != file_name or not candidate.endswith(".docx"):
        raise HTTPException(400, "Ten file khong hop le.")

    target = settings.OUTPUT_DIR / candidate
    if not target.exists():
        raise HTTPException(404, "Khong tim thay file ket qua.")
    return target


def _serialize_formula(
    *,
    formula_id: int,
    page: int | None,
    order: int,
    latex: str,
    display: bool,
) -> dict:
    mathml = None
    mathml_error = None
    raw_latex = latex.strip()
    latex = converter_service.sanitize_toggle_tex_latex(raw_latex)
    latex_source = _format_latex_source(latex, display=display)
    try:
        mathml = converter_service.latex_to_mathml(latex, display=display)
    except Exception as exc:  # pragma: no cover - phu thuoc tung cong thuc dau vao
        mathml_error = str(exc)

    return {
        "id": formula_id,
        "page": page,
        "order": order,
        "latex": latex,
        "raw_latex": raw_latex,
        "latex_source": latex_source,
        "display": display,
        "mathml": mathml,
        "mathml_error": mathml_error,
    }


def _format_latex_source(latex: str, *, display: bool) -> str:
    latex = latex.strip()
    if display:
        return f"\\[\n{latex}\n\\]"
    return f"${latex}$"


def _build_latex_output(formulas: list[dict]) -> str:
    return "\n\n".join(
        formula.get("latex_source") or _format_latex_source(
            formula.get("latex", ""),
            display=bool(formula.get("display")),
        )
        for formula in formulas
        if formula.get("latex")
    )


def _build_formula_catalog(page_entries: list[dict], content_field: str) -> tuple[list[dict], list[dict]]:
    formulas: list[dict] = []
    pages: list[dict] = []
    formula_id = 1

    for page_entry in page_entries:
        page_num = page_entry.get("page")
        text = page_entry.get(content_field, "") or ""
        extracted = ocr_service.extract_formulas(text, page=page_num)
        page_formula_ids: list[int] = []

        for item in extracted:
            serialized = _serialize_formula(
                formula_id=formula_id,
                page=item.get("page"),
                order=item["order"],
                latex=item["latex"],
                display=item["display"],
            )
            formulas.append(serialized)
            page_formula_ids.append(formula_id)
            formula_id += 1

        pages.append(
            {
                "page": page_num,
                "formula_count": len(extracted),
                "formula_ids": page_formula_ids,
                "error": page_entry.get("error"),
            }
        )

    return formulas, pages


def _build_docx_payload(
    *,
    source_type: str,
    mode: str,
    output_path: Path,
    filename: str,
    formulas: list[dict],
    pages: list[dict],
) -> dict:
    return {
        "source_type": source_type,
        "mode": mode,
        "filename": filename,
        "download_url": _build_download_url(output_path),
        "total_formulas": len(formulas),
        "latex_output": _build_latex_output(formulas),
        "docx_formula_format": "toggle_tex_latex",
        "pages": pages,
        "formulas": formulas,
        "errors": sum(1 for page in pages if page.get("error")),
    }


@router.get("/download/{file_name}")
async def download_output(file_name: str) -> FileResponse:
    target = _validate_output_name(file_name)
    return FileResponse(
        target,
        filename=target.name,
        media_type=DOCX_MIME,
    )


@router.post("/image")
async def ocr_image(
    file: UploadFile = File(...),
    mode: str = Form("single", description='"single" = chi cong thuc, "page" = ca trang'),
) -> dict:
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")
    try:
        latex = await ocr_service.image_to_latex(content, mode=mode)
    except Exception as exc:
        raise HTTPException(500, f"Loi OCR: {exc}") from exc
    return {"latex": latex, "mode": mode}


@router.post("/image-to-docx")
async def ocr_image_to_docx(
    file: UploadFile = File(...),
    mode: str = Form("page", description='"single" = 1 cong thuc, "page" = ca trang'),
) -> dict:
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")

    out = new_output_path(".docx")
    download_name = _build_download_name(file.filename, "image-to-word")
    try:
        markdown = await ocr_service.image_to_markdown(content, mode=mode)
        converter_service.markdown_to_toggle_tex_docx(markdown, out)
        formulas, pages = _build_formula_catalog(
            [{"page": 1, "markdown": markdown, "error": None}],
            "markdown",
        )
    except Exception as exc:
        raise HTTPException(500, f"Loi tao Word tu anh: {exc}") from exc

    return _build_docx_payload(
        source_type="image",
        mode=mode,
        output_path=out,
        filename=download_name,
        formulas=formulas,
        pages=pages,
    )


@router.post("/pdf")
async def ocr_pdf(
    file: UploadFile = File(...),
    dpi: int = Form(200),
    mode: str = Form("page"),
    max_concurrent: int = Form(10, description="So trang xu ly song song"),
) -> dict:
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")
    try:
        results = await ocr_service.pdf_to_latex(
            content, dpi=dpi, mode=mode, max_concurrent_pages=max_concurrent
        )
    except Exception as exc:
        raise HTTPException(500, f"Loi OCR PDF: {exc}") from exc
    return {
        "pages": results,
        "total": len(results),
        "errors": sum(1 for item in results if item.get("error")),
    }


@router.post("/image-to-text")
async def ocr_image_to_text(
    file: UploadFile = File(...),
    mode: str = Form("page", description='"single" = 1 cong thuc, "page" = ca trang'),
) -> dict:
    """OCR anh thanh van ban thuan: Cau/Bai N cung dong, A-D xuong dong, cong thuc $...$."""
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")
    try:
        text = await ocr_service.image_to_text(content, mode=mode)
    except Exception as exc:
        raise HTTPException(500, f"Loi OCR: {exc}") from exc
    return {"text": text, "mode": mode}


@router.post("/pdf-to-text")
async def ocr_pdf_to_text(
    file: UploadFile = File(...),
    dpi: int = Form(200),
    mode: str = Form("page"),
    max_concurrent: int = Form(10, description="So trang xu ly song song"),
) -> dict:
    """OCR PDF thanh van ban thuan theo tung trang."""
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")
    try:
        results = await ocr_service.pdf_to_text_pages(
            content, dpi=dpi, mode=mode, max_concurrent_pages=max_concurrent
        )
    except Exception as exc:
        raise HTTPException(500, f"Loi OCR PDF: {exc}") from exc
    return {
        "pages": results,
        "total": len(results),
        "errors": sum(1 for item in results if item.get("error")),
    }


@router.post("/pdf-to-docx")
async def ocr_pdf_to_docx(
    file: UploadFile = File(...),
    dpi: int = Form(200),
    mode: str = Form("page"),
    max_concurrent: int = Form(10, description="So trang xu ly song song"),
) -> dict:
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")

    out = new_output_path(".docx")
    download_name = _build_download_name(file.filename, "pdf-to-word")
    try:
        pages_data = await ocr_service.pdf_to_markdown_pages(
            content,
            dpi=dpi,
            mode=mode,
            max_concurrent_pages=max_concurrent,
        )
        markdown = ocr_service.combine_markdown_pages(pages_data)
        converter_service.markdown_to_toggle_tex_docx(markdown, out)
        formulas, pages = _build_formula_catalog(pages_data, "markdown")
    except Exception as exc:
        raise HTTPException(500, f"Loi tao Word tu PDF: {exc}") from exc

    return _build_docx_payload(
        source_type="pdf",
        mode=mode,
        output_path=out,
        filename=download_name,
        formulas=formulas,
        pages=pages,
    )


@router.post("/image-to-exam-latex")
async def ocr_image_to_exam_latex(
    file: UploadFile = File(...),
    mode: str = Form("page", description='"single" = 1 cau, "page" = ca trang'),
) -> dict:
    """OCR anh thanh LaTeX thi cu: \\begin{ex}...\\choice...\\end{ex}."""
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")
    try:
        latex = await ocr_service.image_to_exam_latex(content, mode=mode)
    except Exception as exc:
        raise HTTPException(500, f"Loi OCR: {exc}") from exc
    return {"latex": latex, "mode": mode}


@router.post("/pdf-to-exam-latex")
async def ocr_pdf_to_exam_latex(
    file: UploadFile = File(...),
    dpi: int = Form(200),
    mode: str = Form("page"),
    max_concurrent: int = Form(10, description="So trang xu ly song song"),
) -> dict:
    """OCR PDF thanh LaTeX thi cu theo tung trang."""
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")
    try:
        results = await ocr_service.pdf_to_exam_latex_pages(
            content, dpi=dpi, mode=mode, max_concurrent_pages=max_concurrent
        )
    except Exception as exc:
        raise HTTPException(500, f"Loi OCR PDF: {exc}") from exc
    return {
        "pages": results,
        "total": len(results),
        "errors": sum(1 for item in results if item.get("error")),
    }


@router.post("/image-to-equation")
async def ocr_image_to_equation(
    file: UploadFile = File(...),
    mode: str = Form("page", description='"single" = 1 cong thuc, "page" = ca trang'),
) -> dict:
    """OCR anh thanh Word voi cong thuc OMML (equation thuc su, khong phai Toggle TeX)."""
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_IMAGE_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")

    out = new_output_path(".docx")
    download_name = _build_download_name(file.filename, "image-to-equation")
    try:
        markdown = await ocr_service.image_to_markdown(content, mode=mode)
        converter_service.markdown_to_docx(markdown, out)
        formulas, pages = _build_formula_catalog(
            [{"page": 1, "markdown": markdown, "error": None}], "markdown"
        )
    except Exception as exc:
        raise HTTPException(500, f"Loi tao Word Equation tu anh: {exc}") from exc

    return _build_docx_payload(
        source_type="image",
        mode=mode,
        output_path=out,
        filename=download_name,
        formulas=formulas,
        pages=pages,
    )


@router.post("/pdf-to-equation")
async def ocr_pdf_to_equation(
    file: UploadFile = File(...),
    dpi: int = Form(200),
    mode: str = Form("page"),
    max_concurrent: int = Form(10, description="So trang xu ly song song"),
) -> dict:
    """OCR PDF thanh Word voi cong thuc OMML (equation thuc su, khong phai Toggle TeX)."""
    mode = _validate_mode(mode)
    validate_extension(file.filename or "", settings.ALLOWED_PDF_EXTENSIONS)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File qua lon.")

    out = new_output_path(".docx")
    download_name = _build_download_name(file.filename, "pdf-to-equation")
    try:
        pages_data = await ocr_service.pdf_to_markdown_pages(
            content, dpi=dpi, mode=mode, max_concurrent_pages=max_concurrent
        )
        markdown = ocr_service.combine_markdown_pages(pages_data)
        converter_service.markdown_to_docx(markdown, out)
        formulas, pages = _build_formula_catalog(pages_data, "markdown")
    except Exception as exc:
        raise HTTPException(500, f"Loi tao Word Equation tu PDF: {exc}") from exc

    return _build_docx_payload(
        source_type="pdf",
        mode=mode,
        output_path=out,
        filename=download_name,
        formulas=formulas,
        pages=pages,
    )
