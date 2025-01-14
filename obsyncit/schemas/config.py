"""
Configuration schema definitions using Pydantic models.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class GeneralConfig(BaseModel):
    """General configuration settings."""
    settings_dir: str = Field(
        default=".obsidian",
        description="Directory name for Obsidian settings"
    )
    backup_count: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of backups to keep"
    )


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    log_dir: str = Field(
        default="logs",
        description="Directory for log files"
    )
    rotation: str = Field(
        default="1 week",
        description="Log rotation interval (e.g., '1 week', '1 day')"
    )
    retention: str = Field(
        default="3 months",
        description="Log retention period"
    )
    compression: str = Field(
        default="zip",
        description="Log compression format"
    )
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log message format"
    )

    @field_validator("level")
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")
        return v.upper()


class SyncConfig(BaseModel):
    """Sync configuration settings."""
    core_settings_files: List[str] = Field(
        default=[
            "appearance.json",
            "app.json",
            "core-plugins.json",
            "community-plugins.json",
            "hotkeys.json"
        ],
        description="List of core settings files to sync"
    )
    settings_dirs: List[str] = Field(
        default=[
            "plugins",
            "themes",
            "snippets"
        ],
        description="List of settings directories to sync"
    )


class Config(BaseModel):
    """Root configuration model."""
    general: GeneralConfig
    logging: LoggingConfig
    sync: SyncConfig 