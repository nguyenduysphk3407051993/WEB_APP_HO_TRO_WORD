from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Document Converter API"
    APP_VERSION: str = "2.1.0"

    UPLOAD_DIR: Path = Path("/app/data/uploads")
    OUTPUT_DIR: Path = Path("/app/data/outputs")
    KEYS_FILE: Path = Path("/app/data/keys.json")
    PROVIDER_CONFIG_FILE: Path = Path("/app/data/provider.json")

    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    ALLOWED_PDF_EXTENSIONS: set[str] = {".pdf"}
    ALLOWED_DOCX_EXTENSIONS: set[str] = {".docx"}

    CORS_ORIGINS: list[str] = ["*"]

    # ============ 9router API (OpenAI-compatible) ============
    NINEROUTER_API_KEY: str = ""
    NINEROUTER_API_KEYS: str = ""
    NINEROUTER_BASE_URL: str = "https://9router.edutechnd.org/v1"
    NINEROUTER_MODEL: str = "cx/gpt-5.5"
    NINEROUTER_MAX_CONCURRENT_PER_KEY: int = 3
    NINEROUTER_RETRY_ATTEMPTS: int = 3
    NINEROUTER_TIMEOUT_SECONDS: int = 180
    NINEROUTER_MAX_TOKENS: int = 16384

    # ============ Admin ============
    # Mật khẩu để truy cập trang quản lý keys (BẮT BUỘC khi deploy public)
    ADMIN_PASSWORD: str = ""

    @property
    def ninerouter_keys_list(self) -> list[str]:
        raw_keys = [self.NINEROUTER_API_KEY, *self.NINEROUTER_API_KEYS.split(",")]
        return list(dict.fromkeys(k.strip() for k in raw_keys if k.strip()))

    class Config:
        env_file = ".env"


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
