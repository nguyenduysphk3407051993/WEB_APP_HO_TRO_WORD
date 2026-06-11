"""FastAPI entry cho web app chuyển đổi tài liệu với 9router."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, convert, ocr
from app.services.api_key_pool import ApiKeyPool, get_pool, init_pool, init_gemini_pool
from app.services.ninerouter_client import provider_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 9router pool
    keys_from_file = ApiKeyPool.load_keys_from_file(settings.KEYS_FILE)
    keys = keys_from_file or settings.ninerouter_keys_list
    source = "file" if keys_from_file else ("env" if keys else "none")
    init_pool(
        keys,
        max_concurrent_per_key=settings.NINEROUTER_MAX_CONCURRENT_PER_KEY,
        persist_path=settings.KEYS_FILE,
    )
    if keys:
        logger.info("9router pool san sang: %d key tu %s.", len(keys), source)
    else:
        logger.warning("9router pool rong - vao /admin de them key.")

    # Gemini pool
    gemini_keys_from_file = ApiKeyPool.load_keys_from_file(settings.GEMINI_KEYS_FILE)
    gemini_keys = gemini_keys_from_file or settings.gemini_keys_list
    gemini_source = "file" if gemini_keys_from_file else ("env" if gemini_keys else "none")
    init_gemini_pool(
        gemini_keys,
        max_concurrent_per_key=settings.GEMINI_MAX_CONCURRENT_PER_KEY,
        persist_path=settings.GEMINI_KEYS_FILE,
    )
    if gemini_keys:
        logger.info("Gemini pool san sang: %d key tu %s.", len(gemini_keys), gemini_source)
    else:
        logger.warning("Gemini pool rong - vao /admin de them key.")

    logger.info("Provider hien tai: %s / model: %s", provider_config.provider, provider_config.model)

    if not settings.ADMIN_PASSWORD:
        logger.warning("ADMIN_PASSWORD chua set - trang quan ly key se bi khoa.")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr.router)
app.include_router(convert.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["Meta"])
def health() -> dict:
    from app.services.api_key_pool import get_gemini_pool
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "provider": provider_config.provider,
        "model": provider_config.model,
        "ninerouter_keys": get_pool().stats()["total"],
        "gemini_keys": get_gemini_pool().stats()["total"],
    }


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "ocr_image_latex": "POST /api/ocr/image",
            "ocr_image_docx": "POST /api/ocr/image-to-docx",
            "ocr_pdf_latex": "POST /api/ocr/pdf",
            "ocr_pdf_docx": "POST /api/ocr/pdf-to-docx",
            "ocr_download_docx": "GET /api/ocr/download/{file_name}",
            "latex_to_mathtype": "POST /api/convert/latex-to-mathtype",
            "latex_to_docx": "POST /api/convert/latex-to-docx",
            "docx_to_latex": "POST /api/convert/docx-to-latex",
            "keys_stats": "GET /api/admin/keys/stats",
        },
    }
