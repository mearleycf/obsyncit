"""
JSON schema validation for Obsidian settings files.

This module provides data validation and schema definitions for Obsidian
settings files and configuration files.
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