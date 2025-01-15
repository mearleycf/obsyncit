"""
Configuration schema for ObsyncIt.

This module defines the configuration schema for the ObsyncIt tool,
validating user-provided configuration files.
"""

from enum import Enum
from pathlib import Path
from typing import Union
from pydantic import BaseModel, Field, validator


class LogLevel(str, Enum):
    """
    Enumeration of valid logging levels.
    
    Levels in order of increasing severity:
    - DEBUG: Detailed information for debugging
    - INFO: General operational information
    - WARNING: Indicate a potential problem
    - ERROR: A more serious problem
    - CRITICAL: Program may not be able to continue
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CompressionFormat(str, Enum):
    """
    Enumeration of supported log compression formats.
    
    Available formats:
    - zip: Standard ZIP compression
    - gz: Gzip compression
    - tar: TAR archive (no compression)
    - tar.gz: TAR archive with Gzip compression
    """
    ZIP = "zip"
    GZIP = "gz"
    TAR = "tar"
    TAR_GZ = "tar.gz"


class LoggingConfig(BaseModel):
    """
    Logging configuration settings.
    
    This class defines the logging behavior for the application, including:
    - Log file location and organization
    - Logging level and message format
    - File rotation and retention policies
    
    Example Configuration:
        ```toml
        [logging]
        # Store logs in the .logs directory
        log_dir = ".logs"
        # Show all messages at INFO level and above
        level = "INFO"
        # Custom format with timestamp, level, and message
        format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
        # Create new log file daily
        rotation = "1 day"
        # Keep logs for one week
        retention = "1 week"
        # Compress old logs using zip
        compression = "zip"
        ```
    
    Format Placeholders:
        The format string supports various placeholders:
        - {time}: Timestamp (with format specifier)
        - {level}: Log level
        - {message}: Log message
        - {name}: Logger name
        - {function}: Function name
        - {line}: Line number
        - {file}: File name
    
    Time Format Examples:
        - YYYY-MM-DD: 2024-02-20
        - HH:mm:ss: 14:30:45
        - DD/MM/YY: 20/02/24
        - HH:mm: 14:30
    """

    log_dir: Union[str, Path] = Field(
        default=".logs",
        description="Directory to store log files. Can be relative or absolute path."
    )
    
    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level determining which messages are recorded."
    )
    
    format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        description="Format string for log messages with placeholders."
    )
    
    rotation: str = Field(
        default="1 day",
        description="When to start new log file (e.g., '1 day', '100 MB', '1 week')."
    )
    
    retention: str = Field(
        default="1 week",
        description="How long to keep old log files (e.g., '1 week', '1 month', '1 year')."
    )
    
    compression: CompressionFormat = Field(
        default=CompressionFormat.ZIP,
        description="Compression format for rotated log files."
    )

    @validator("log_dir")
    def validate_log_dir(cls, v: Union[str, Path]) -> Path:
        """
        Validate and convert log directory path.
        
        Ensures the log directory path is:
        1. Converted to a Path object
        2. Absolute path or made absolute
        3. Parent directory exists or is creatable
        
        Args:
            v: Log directory path as string or Path

        Returns:
            Path: Validated and converted path

        Raises:
            ValueError: If path is invalid or parent directory is not accessible
        """
        path = Path(v)
        if not path.is_absolute():
            path = Path.cwd() / path
        
        # Check if parent directory exists and is accessible
        parent = path.parent
        if parent != Path.cwd() and not parent.exists():
            raise ValueError(
                f"Parent directory does not exist: {parent}. "
                "Please create it first or use a different path."
            )
        
        return path

    @validator("rotation", "retention")
    def validate_time_period(cls, v: str) -> str:
        """
        Validate time period strings.
        
        Valid formats:
        - Time units: "X day(s)", "X week(s)", "X month(s)", "X year(s)"
        - Size units: "X MB", "X GB"
        
        Args:
            v: Time period string

        Returns:
            str: Validated time period

        Raises:
            ValueError: If format is invalid
        """
        parts = v.split()
        if len(parts) != 2:
            raise ValueError(
                "Invalid time period format. "
                "Use format: '<number> <unit>' (e.g., '1 day', '100 MB')"
            )
        
        amount, unit = parts
        try:
            float(amount)
        except ValueError:
            raise ValueError(f"Invalid amount: {amount}. Must be a number.")
        
        valid_units = {
            "day", "days", "week", "weeks", "month", "months", "year", "years",
            "MB", "GB"
        }
        if unit not in valid_units:
            raise ValueError(
                f"Invalid unit: {unit}. "
                f"Must be one of: {', '.join(sorted(valid_units))}"
            )
        
        return v


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
