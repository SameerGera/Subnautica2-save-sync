"""Configuration management with Pydantic validation."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """Application configuration model."""

    minio_endpoint: str = Field(..., description="MinIO server URL")
    minio_access_key: str = Field(..., description="MinIO access key")
    minio_secret_key: str = Field(..., description="MinIO secret key")
    bucket_name: str = Field(..., description="MinIO bucket name")
    player_id: str = Field(..., description="Unique player identifier")
    game_executable_path: str = Field(..., description="Path to game executable")
    save_directory: str = Field(..., description="Path to save games directory")
    lock_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    max_lock_retries: int = Field(default=3, ge=1, le=10)

    @field_validator("minio_endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("game_executable_path")
    @classmethod
    def validate_executable(cls, v: str) -> str:
        if v and not os.path.exists(v):
            raise ValueError(f"Game executable not found: {v}")
        return v

    @field_validator("save_directory")
    @classmethod
    def validate_save_directory(cls, v: str) -> str:
        if v and not os.path.isdir(v):
            raise ValueError(f"Save directory not found: {v}")
        return v


def get_config_path() -> Path:
    """Get config file path relative to exe or script."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).parent.parent.parent
    return base_dir / "config" / "config.json"


def load_config() -> Config:
    """Load configuration from JSON file."""
    config_path = get_config_path()
    if not config_path.exists():
        return Config(
            minio_endpoint="http://localhost:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            bucket_name="subnautica2-saves",
            player_id="player1",
            game_executable_path="",
            save_directory="",
            lock_ttl_seconds=300,
            max_lock_retries=3
        )
    with open(config_path, "r") as f:
        data = json.load(f)
    return Config(**data)


def save_config(config: Config) -> None:
    """Save configuration to JSON file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2)