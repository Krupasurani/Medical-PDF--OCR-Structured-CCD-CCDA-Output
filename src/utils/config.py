"""Configuration management"""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # API Keys
    gemini_api_key: str

    # Optional Settings
    debug: bool = False
    max_file_size_mb: int = 50
    max_page_count: int = 100
    log_level: str = "INFO"
    log_phi: bool = False  # Never log patient names

    # OCR Configuration
    ocr_confidence_threshold: float = 0.70
    ocr_timeout_seconds: int = 30

    # Structuring Configuration
    structuring_timeout_seconds: int = 120

    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_file_size_mb * 1024 * 1024


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config
