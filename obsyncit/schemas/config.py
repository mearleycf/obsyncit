"""Configuration Schema for ObsyncIt.

This module defines comprehensive configuration schemas for the ObsyncIt tool using
Pydantic models. It provides validation, type checking, and sensible defaults for
all configuration options.

The configuration is organized hierarchically:

1. Root Configuration (Config)
   - Contains all sub-configurations
   - Provides global settings

2. Logging (LoggingConfig)
   - Log file locations and formats
   - Rotation and retention policies
   - Compression settings

3. Backup Management (BackupConfig)
   - Backup storage and retention
   - Error handling preferences
   - Dry run support

4. Sync Settings (SyncConfig)
   - Core settings sync options
   - Plugin sync preferences
   - Theme and snippet handling
   - Operational controls

Example usage:
    >>> from obsyncit.schemas import Config
    >>> 
    >>> # Create config with defaults
    >>> config = Config()
    >>> 
    >>> # Create config with custom settings
    >>> config = Config(
    ...     sync={"dry_run": True, "ignore_errors": True},
    ...     backup={"max_backups": 10},
    ...     logging={"level": "DEBUG"}
    ... )
    >>> 
    >>> # Access settings
    >>> config.sync.dry_run
    True
    >>> config.backup.max_backups
    10

Configuration can also be loaded from TOML files:
    ```toml
    [sync]
    dry_run = true
    ignore_errors = true
    core_settings = true
    community_plugins = true

    [backup]
    max_backups = 10
    backup_dir = ".backups"

    [logging]
    level = "DEBUG"
    rotation = "1 day"
    retention = "1 week"
    ```
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LoggingConfig(BaseModel):
    """Logging configuration settings.
    
    This model defines how logging should be configured, including
    file locations, log levels, formats, and rotation policies.
    
    Attributes:
        log_dir: Directory where log files will be stored (default: ".logs")
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        format: strftime format string for log messages
        rotation: When to rotate files ("1 day", "1 week", "100 MB", etc.)
        retention: How long to keep old logs ("1 week", "1 month", etc.)
        compression: How to compress logs ("zip", "gz", "tar")
    
    Example:
        >>> config = LoggingConfig(
        ...     log_dir="logs",
        ...     level="DEBUG",
        ...     rotation="100 MB",
        ...     retention="1 month"
        ... )
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
            v: The rotation interval string. Can be time-based ("1 day", "1 week")
               or size-based ("100 MB", "1 GB").
            
        Returns:
            The validated rotation interval if valid
            
        Raises:
            ValueError: If format is invalid or if size/unit is malformed
        
        Examples:
            >>> LoggingConfig.validate_rotation("1 day")  # Valid
            '1 day'
            >>> LoggingConfig.validate_rotation("100 MB")  # Valid
            '100 MB'
            >>> LoggingConfig.validate_rotation("invalid")  # Raises ValueError
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
            v: The retention period string. Must be time-based (e.g., "1 day").
            
        Returns:
            The validated retention period if valid
            
        Raises:
            ValueError: If format is invalid
        
        Examples:
            >>> LoggingConfig.validate_retention("1 week")  # Valid
            '1 week'
            >>> LoggingConfig.validate_retention("invalid")  # Raises ValueError
        """
        if not any(unit in v.lower() for unit in ["day", "week", "month", "year"]):
            raise ValueError("Invalid retention format. Expected format: '1 day', '1 week', '1 month', '1 year'")
        return v


class BackupConfig(BaseModel):
    """Backup configuration settings.
    
    This model defines how backups should be handled, including
    storage location, retention policies, and error handling.
    
    Attributes:
        backup_dir: Directory where backups will be stored (default: ".backups")
        max_backups: Maximum number of backups to retain (default: 5)
        dry_run: Whether to simulate backup operations (default: False)
        ignore_errors: Whether to continue on non-critical errors (default: False)
    
    Example:
        >>> config = BackupConfig(
        ...     backup_dir="backups",
        ...     max_backups=10,
        ...     dry_run=True
        ... )
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
            v: The maximum number of backups to keep
            
        Returns:
            The validated maximum if valid
            
        Raises:
            ValueError: If value is negative
        
        Examples:
            >>> BackupConfig.validate_max_backups(5)  # Valid
            5
            >>> BackupConfig.validate_max_backups(-1)  # Raises ValueError
        """
        if v < 0:
            raise ValueError("Max backups must be non-negative")
        return v


class SyncConfig(BaseModel):
    """Sync configuration settings.
    
    This model defines what components of an Obsidian vault should
    be synchronized between instances, along with operational settings
    for how the sync should be performed.
    
    Attributes:
        core_settings: Sync core settings files (default: True)
        core_plugins: Sync core plugin settings (default: True)
        community_plugins: Sync community plugin data and settings (default: True)
        themes: Sync theme files (default: True)
        snippets: Sync CSS snippets (default: True)
        dry_run: Simulate sync operations (default: False)
        ignore_errors: Continue on non-critical errors (default: False)
    
    Files synced when core_settings is True:
        - app.json
        - appearance.json
        - hotkeys.json
        - types.json
        - templates.json
    
    Files synced when plugins enabled:
        - core-plugins.json
        - community-plugins.json
        - core-plugins-migration.json
        - plugins/ directory
        - icons/ directory
    
    Example:
        >>> config = SyncConfig(
        ...     core_settings=True,
        ...     community_plugins=True,
        ...     dry_run=True
        ... )
    """

    core_settings: bool = Field(
        default=True,
        description="Sync core settings (app.json, appearance.json, hotkeys.json, etc.)"
    )
    core_plugins: bool = Field(
        default=True,
        description="Sync core plugin settings"
    )
    community_plugins: bool = Field(
        default=True,
        description="Sync community plugin settings and data"
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
    sections into a single hierarchy. It provides a complete configuration
    for the ObsyncIt tool.
    
    Attributes:
        logging: Logging configuration settings
        backup: Backup configuration settings
        sync: Sync configuration settings
    
    Example:
        >>> config = Config(
        ...     sync={"dry_run": True},
        ...     backup={"max_backups": 10},
        ...     logging={"level": "DEBUG"}
        ... )
        >>> 
        >>> # Access nested settings
        >>> config.sync.dry_run
        True
        >>> config.logging.level
        'DEBUG'
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