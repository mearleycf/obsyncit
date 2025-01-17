"""Obsidian-specific schema definitions and validation.

This module contains data models and validation logic for Obsidian-specific concepts
like vaults, settings, and plugins.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

@dataclass
class ObsidianSettings:
    """Represents Obsidian vault settings."""
    
    basePath: Path
    """Base path of the Obsidian vault"""
    
    configDir: Path
    """Path to the .obsidian configuration directory"""
    
    pluginDir: Optional[Path] = None
    """Path to the plugins directory, if it exists"""
    
    themeDir: Optional[Path] = None
    """Path to the themes directory, if it exists"""
    
    snippetDir: Optional[Path] = None
    """Path to the snippets directory, if it exists"""

    def __post_init__(self):
        """Convert string paths to Path objects and validate existence."""
        if isinstance(self.basePath, str):
            self.basePath = Path(self.basePath).resolve()
        if isinstance(self.configDir, str):
            self.configDir = Path(self.configDir).resolve()
        if self.pluginDir and isinstance(self.pluginDir, str):
            self.pluginDir = Path(self.pluginDir).resolve()
        if self.themeDir and isinstance(self.themeDir, str):
            self.themeDir = Path(self.themeDir).resolve()
        if self.snippetDir and isinstance(self.snippetDir, str):
            self.snippetDir = Path(self.snippetDir).resolve()

    def validate(self) -> bool:
        """Validate that the Obsidian settings are complete and correct.
        
        Returns:
            bool: True if settings are valid, False otherwise
        """
        if not self.basePath.exists() or not self.basePath.is_dir():
            return False
        if not self.configDir.exists() or not self.configDir.is_dir():
            return False
        return True

    @property
    def settings_file(self) -> Optional[Path]:
        """Get the path to the main settings file.
        
        Returns:
            Optional[Path]: Path to app.json if it exists, None otherwise
        """
        settings = self.configDir / "app.json"
        return settings if settings.exists() else None

@dataclass
class Plugin:
    """Represents an Obsidian plugin."""
    
    id: str
    """Unique identifier of the plugin"""
    
    name: str
    """Display name of the plugin"""
    
    version: str
    """Plugin version"""
    
    minAppVersion: str
    """Minimum required Obsidian version"""
    
    enabled: bool = False
    """Whether the plugin is enabled"""

@dataclass
class Theme:
    """Represents an Obsidian theme."""
    
    name: str
    """Theme name"""
    
    author: str
    """Theme author"""
    
    version: str
    """Theme version"""
    
    minAppVersion: str
    """Minimum required Obsidian version"""
    
    enabled: bool = False
    """Whether the theme is enabled"""

@dataclass
class VaultMetadata:
    """Represents metadata about an Obsidian vault."""
    
    path: Path
    """Path to the vault"""
    
    settings: ObsidianSettings
    """Vault settings"""
    
    plugins: Dict[str, Plugin]
    """Installed plugins"""
    
    themes: Dict[str, Theme]
    """Installed themes"""
    
    snippets: List[Path]
    """CSS snippets"""

    def __post_init__(self):
        """Convert string paths to Path objects."""
        if isinstance(self.path, str):
            self.path = Path(self.path).resolve()

class AppSettings(BaseModel):
    """Schema for app.json settings."""
    model_config = ConfigDict(extra='allow')

class AppearanceSettings(BaseModel):
    """Schema for appearance.json settings."""
    model_config = ConfigDict(extra='allow')

class HotkeysSettings(BaseModel):
    """Schema for hotkeys.json settings."""
    model_config = ConfigDict(extra='allow')

# Map of file names to their schema classes
SCHEMA_MAP: Dict[str, Any] = {
    'app.json': AppSettings,
    'appearance.json': AppearanceSettings,
    'hotkeys.json': HotkeysSettings,
}
