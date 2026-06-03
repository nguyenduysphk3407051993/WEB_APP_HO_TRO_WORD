from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Document Converter API"
    APP_VERSION: str = "1.0.0"

    UPLOAD_DIR: Path = Path("/app/data/uploads")
    OUTPUT_DIR: Path = Path("/app/data/outputs")

    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    ALLOWED_PDF_EXTENSIONS: set[str] = {".pdf"}
    ALLOWED_DOCX_EXTENSIONS: set[str] = {".docx"}

    CORS_ORIGINS: list[str] = ["*"]

    USE_GPU: bool = False

    class Config:
        env_file = ".env"


settings = Settings()

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
