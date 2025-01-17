"""Configuration schema for ObsyncIt.

This module defines the configuration schema for the ObsyncIt tool,
validating user-provided configuration files using Pydantic models.

The configuration is hierarchical, with separate sections for:
- Logging configuration
- Backup management
- Sync preferences

Each section is defined as a Pydantic model with validation and defaults.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LoggingConfig(BaseModel):
    """Logging configuration settings.
    
    This model defines how logging should be configured, including
    file locations, log levels, formats, and rotation policies.
    
    Attributes:
        log_dir: Directory where log files will be stored
        level: Logging level to use
        format: Format string for log messages
        rotation: When to rotate log files
        retention: How long to keep old log files
        compression: How to compress rotated logs
    """

    log_dir: str = Field(
        default=".logs",
        description="Directory to store log files"
    )
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
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
    compression: Literal["zip", "gz", "tar"] = Field(
        default="zip",
        description="Log file compression format"
    )

    @field_validator('rotation')
    def validate_rotation(cls, v: str) -> str:
        """Validate the rotation interval format.
        
        Args:
            v: The rotation interval string
            
        Returns:
            The validated rotation interval
            
        Raises:
            ValueError: If the format is invalid
        """
        # Accept time-based rotation (e.g., "1 day", "1 week")
        if any(unit in v.lower() for unit in ["day", "week", "month", "year"]):
            return v
        
        # Accept size-based rotation (e.g., "100 MB", "1 GB")
        if any(unit in v.upper() for unit in ["B", "KB", "MB", "GB"]):
            try:
                size, unit = v.split()
                float(size)  # Validate size is a number
                return v
            except ValueError:
                raise ValueError("Invalid size format. Expected format: '100 MB', '1 GB', etc.")
        
        raise ValueError("Invalid rotation format. Expected time-based (e.g., '1 day') or size-based (e.g., '100 MB')")

    @field_validator('retention')
    def validate_retention(cls, v: str) -> str:
        """Validate the retention period format.
        
        Args:
            v: The retention period string
            
        Returns:
            The validated retention period
            
        Raises:
            ValueError: If the format is invalid
        """
        if not any(unit in v.lower() for unit in ["day", "week", "month", "year"]):
            raise ValueError("Invalid retention format. Expected format: '1 day', '1 week', '1 month', '1 year'")
        return v


class BackupConfig(BaseModel):
    """Backup configuration settings.
    
    This model defines how backups should be handled, including
    storage location and retention policies.
    
    Attributes:
        backup_dir: Directory where backups will be stored
        max_backups: Maximum number of backups to retain
        dry_run: Whether to simulate backup operations
        ignore_errors: Whether to continue on non-critical errors
    """

    backup_dir: str = Field(
        default=".backups",
        description="Directory to store backups"
    )
    max_backups: int = Field(
        default=5,
        description="Maximum number of backups to keep",
        ge=1
    )
    dry_run: bool = Field(
        default=False,
        description="Simulate backup operations without making changes"
    )
    ignore_errors: bool = Field(
        default=False,
        description="Continue on non-critical errors"
    )

    @field_validator('max_backups')
    def validate_max_backups(cls, v: int) -> int:
        """Validate the maximum number of backups.
        
        Args:
            v: The maximum number of backups
            
        Returns:
            The validated maximum
            
        Raises:
            ValueError: If the value is less than 1
        """
        if v < 0:
            raise ValueError("Max backups must be non-negative")
        return v


class SyncConfig(BaseModel):
    """Sync configuration settings.
    
    This model defines what components of an Obsidian vault should
    be synchronized between instances.
    
    Attributes:
        core_settings: Whether to sync core Obsidian settings
        core_plugins: Whether to sync core plugin settings
        community_plugins: Whether to sync community plugin settings
        themes: Whether to sync themes
        snippets: Whether to sync CSS snippets
        dry_run: Whether to simulate sync operations
        ignore_errors: Whether to continue on non-critical errors
    """

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
    dry_run: bool = Field(
        default=False,
        description="Simulate sync operations without making changes"
    )
    ignore_errors: bool = Field(
        default=False,
        description="Continue on non-critical errors"
    )


class Config(BaseModel):
    """Main configuration schema.
    
    This is the root configuration model that combines all other configuration
    sections into a single hierarchy.
    
    Attributes:
        logging: Logging configuration settings
        backup: Backup configuration settings
        sync: Sync configuration settings
    """

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

    model_config = ConfigDict(
        extra='allow'
    )
