"""FastAPI entry: web app chuyển đổi tài liệu với Gemini API pool."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, convert, ocr
from app.services.gemini_pool import GeminiKeyPool, init_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ưu tiên load từ file persistent, fallback về env
    keys_from_file = GeminiKeyPool.load_keys_from_file(settings.KEYS_FILE)
    keys = keys_from_file or settings.gemini_keys_list
    source = "file" if keys_from_file else ("env" if keys else "none")

    # Luôn init pool — kể cả khi rỗng — để API admin có thể thêm key lúc runtime
    init_pool(
        keys,
        max_concurrent_per_key=settings.GEMINI_MAX_CONCURRENT_PER_KEY,
        persist_path=settings.KEYS_FILE,
    )
    if keys:
        logger.info("Pool sẵn sàng: %d key từ %s (model=%s).",
                    len(keys), source, settings.GEMINI_MODEL)
    else:
        logger.warning("⚠ Pool rỗng — vào /admin trên web để thêm key.")

    if not settings.ADMIN_PASSWORD:
        logger.warning("⚠ ADMIN_PASSWORD chưa set — trang quản lý key sẽ bị khoá.")
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
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_keys": len(settings.gemini_keys_list),
    }


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "ocr_image": "POST /api/ocr/image",
            "ocr_pdf": "POST /api/ocr/pdf",
            "latex_to_mathtype": "POST /api/convert/latex-to-mathtype",
            "latex_to_docx": "POST /api/convert/latex-to-docx",
            "docx_to_latex": "POST /api/convert/docx-to-latex",
            "keys_stats": "GET /api/admin/keys/stats",
        },
    }
