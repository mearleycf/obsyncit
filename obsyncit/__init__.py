"""
ObsyncIt - Obsidian Settings Sync Tool
"""

from obsyncit.sync import SyncManager as ObsidianSettingsSync
from obsyncit.schemas import SCHEMA_MAP

__version__ = "0.1.0"

__all__ = ["ObsidianSettingsSync", "SCHEMA_MAP"]
