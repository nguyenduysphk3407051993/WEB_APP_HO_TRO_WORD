from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Document Converter API"
    APP_VERSION: str = "2.1.0"

    UPLOAD_DIR: Path = Path("/app/data/uploads")
    OUTPUT_DIR: Path = Path("/app/data/outputs")
    KEYS_FILE: Path = Path("/app/data/keys.json")

    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    ALLOWED_PDF_EXTENSIONS: set[str] = {".pdf"}
    ALLOWED_DOCX_EXTENSIONS: set[str] = {".docx"}

    CORS_ORIGINS: list[str] = ["*"]

    # ============ Gemini API ============
    GEMINI_API_KEYS: str = ""  # fallback nếu chưa có file keys.json
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_MAX_CONCURRENT_PER_KEY: int = 3
    GEMINI_RETRY_ATTEMPTS: int = 3
    GEMINI_TIMEOUT_SECONDS: int = 120

    # ============ Admin ============
    # Mật khẩu để truy cập trang quản lý keys (BẮT BUỘC khi deploy public)
    ADMIN_PASSWORD: str = ""

    @property
    def gemini_keys_list(self) -> list[str]:
        return [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
