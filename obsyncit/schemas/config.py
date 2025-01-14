"""
Configuration schema for ObsyncIt.

This module defines the configuration schema for the ObsyncIt tool,
validating user-provided configuration files.
"""

from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Logging configuration settings."""

    log_dir: str = Field(
        default=".logs",
        description="Directory to store log files"
    )
    level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        description="Log message format"
    )
    rotation: str = Field(
        default="1 day",
        description="Log file rotation interval"
    )
    retention: str = Field(
        default="1 week",
        description="Log file retention period"
    )
    compression: str = Field(
        default="zip",
        description="Log file compression format"
    )


class BackupConfig(BaseModel):
    """Backup configuration settings."""

    backup_dir: str = Field(
        default=".backups",
        description="Directory to store backups"
    )
    max_backups: int = Field(
        default=5,
        description="Maximum number of backups to keep"
    )


class SyncConfig(BaseModel):
    """Sync configuration settings."""

    core_settings: bool = Field(
        default=True,
        description="Sync core settings (app.json, appearance.json, hotkeys.json)"
    )
    core_plugins: bool = Field(
        default=True,
        description="Sync core plugin settings"
    )
    community_plugins: bool = Field(
        default=True,
        description="Sync community plugin settings"
    )
    themes: bool = Field(
        default=True,
        description="Sync themes"
    )
    snippets: bool = Field(
        default=True,
        description="Sync snippets"
    )


class Config(BaseModel):
    """Main configuration schema."""

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    backup: BackupConfig = Field(
        default_factory=BackupConfig,
        description="Backup configuration"
    )
    sync: SyncConfig = Field(
        default_factory=SyncConfig,
        description="Sync configuration"
    )
