"""
JSON Schema Validation for Obsidian Settings

This module provides data validation and schema definitions for both Obsidian vault
settings files and ObsyncIt configuration files. It handles validation of:

Vault Settings:
- Core settings files (app.json, appearance.json, etc.)
- Plugin settings (core-plugins.json, community-plugins.json)
- Theme configurations
- Template settings
- Type definitions
- Migration configurations

Configuration:
- Main configuration (Config)
- Logging settings (LoggingConfig)
- Backup policies (BackupConfig)
- Sync options (SyncConfig)

All schemas use Pydantic for validation, providing:
- Type checking and coercion
- Default values
- Validation rules and constraints
- Helpful error messages

Basic Example:
    >>> from obsyncit.schemas import Config
    >>> 
    >>> # Create config with defaults
    >>> config = Config()
    >>> print(f"Max backups: {config.backup.max_backups}")
    >>> print(f"Log level: {config.logging.level}")
    >>> 
    >>> # Create config with custom settings
    >>> config = Config(
    ...     sync={"dry_run": True, "ignore_errors": True},
    ...     backup={"max_backups": 5, "backup_dir": "backups"},
    ...     logging={"level": "DEBUG", "rotation": "1 day"}
    ... )
    >>> 
    >>> # Access nested settings
    >>> print(f"Dry run: {config.sync.dry_run}")
    >>> print(f"Backup dir: {config.backup.backup_dir}")

Advanced Configuration:
    >>> # Configure specific components
    >>> from obsyncit.schemas import LoggingConfig, BackupConfig, SyncConfig
    >>> 
    >>> # Logging configuration
    >>> logging_config = LoggingConfig(
    ...     log_dir="logs",
    ...     level="DEBUG",
    ...     rotation="100 MB",
    ...     retention="1 week",
    ...     compression="zip"
    ... )
    >>> 
    >>> # Backup configuration
    >>> backup_config = BackupConfig(
    ...     backup_dir="backups",
    ...     max_backups=10,
    ...     dry_run=True
    ... )
    >>> 
    >>> # Sync configuration
    >>> sync_config = SyncConfig(
    ...     core_settings=True,
    ...     community_plugins=True,
    ...     themes=True,
    ...     dry_run=True
    ... )
    >>> 
    >>> # Create complete config
    >>> config = Config(
    ...     logging=logging_config,
    ...     backup=backup_config,
    ...     sync=sync_config
    ... )

Validating Obsidian Settings:
    >>> from obsyncit.schemas import SCHEMA_MAP
    >>> import json
    >>> 
    >>> # Load settings file
    >>> with open("appearance.json") as f:
    ...     settings_data = json.load(f)
    >>> 
    >>> # Get schema and validate
    >>> schema = SCHEMA_MAP["appearance.json"]
    >>> try:
    ...     validated_data = schema.model_validate(settings_data)
    ...     print("Settings are valid")
    ... except Exception as e:
    ...     print(f"Validation error: {e}")
    >>> 
    >>> # Access validated settings
    >>> print(f"Theme: {validated_data.theme}")
    >>> print(f"Font size: {validated_data.baseFontSize}")

Error Handling:
    >>> from pydantic import ValidationError
    >>> 
    >>> try:
    ...     config = Config(
    ...         logging={"level": "INVALID"},
    ...         backup={"max_backups": -1}
    ...     )
    ... except ValidationError as e:
    ...     print("Configuration errors:")
    ...     for error in e.errors():
    ...         print(f"- {error['loc']}: {error['msg']}")
"""

from obsyncit.schemas.config import (
    Config,
    LoggingConfig,
    BackupConfig,
    SyncConfig,
)
from obsyncit.schemas.obsidian import SCHEMA_MAP

__all__ = [
    # Configuration schemas
    'Config',
    'LoggingConfig',
    'BackupConfig',
    'SyncConfig',
    
    # Obsidian schemas
    'SCHEMA_MAP',
]