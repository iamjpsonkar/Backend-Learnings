"""
api/app/settings.py — Application settings via environment variables
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    labs_dir: str = "/labs"
    db_path: str = "/app/data/lab_platform.db"
    ui_port: int = 3001

    # MinIO settings (for labs that upload artifacts)
    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str = "labadmin"
    minio_secret_key: str = "labpassword123"

    # Lab runner timeout in seconds
    lab_runner_timeout: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
