"""
JSON schema validation for Obsidian settings files.
"""

from obsyncit.schemas.config import Config, LoggingConfig
from obsyncit.schemas.obsidian import SCHEMA_MAP

__all__ = ['Config', 'LoggingConfig', 'SCHEMA_MAP']
