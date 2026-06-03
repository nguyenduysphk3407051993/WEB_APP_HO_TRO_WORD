"""FastAPI entry: ứng dụng web chuyển đổi tài liệu (PDF/ảnh ↔ LaTeX ↔ MathType ↔ Word Equation)."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import convert, ocr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr.router)
app.include_router(convert.router)


@app.get("/api/health", tags=["Meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "docs": "/docs",
        "endpoints": {
            "ocr_image": "POST /api/ocr/image",
            "ocr_pdf": "POST /api/ocr/pdf",
            "latex_to_mathml": "POST /api/convert/latex-to-mathml",
            "latex_to_mathtype": "POST /api/convert/latex-to-mathtype",
            "mathml_to_latex": "POST /api/convert/mathml-to-latex",
            "latex_to_docx": "POST /api/convert/latex-to-docx",
            "docx_to_latex": "POST /api/convert/docx-to-latex",
            "docx_extract": "POST /api/convert/docx-extract-equations",
        },
    }
