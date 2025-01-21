"""Obsidian-specific Schema Definitions and Validation.

This module contains comprehensive data models and validation logic for all Obsidian-specific
concepts including vaults, settings, plugins, themes, and metadata. It provides:

1. Core Settings Models
   - App settings (app.json)
   - Appearance settings (appearance.json)
   - Hotkey configurations (hotkeys.json)
   - Types and templates
   - Core plugin settings

2. Plugin Management
   - Community plugin metadata
   - Plugin settings validation
   - Version compatibility checking
   - Plugin resources (icons, etc.)

3. Theme Handling
   - Theme metadata validation
   - CSS snippet management
   - Resource management

4. Vault Structure
   - Directory structure validation
   - Settings organization
   - Path resolution and validation

Example usage:
    >>> from obsyncit.schemas.obsidian import ObsidianSettings, Plugin
    >>> 
    >>> # Create settings object
    >>> settings = ObsidianSettings(
    ...     basePath="/path/to/vault",
    ...     configDir="/path/to/vault/.obsidian"
    ... )
    >>> 
    >>> # Validate settings
    >>> if settings.validate():
    ...     print(f"Valid vault at {settings.basePath}")
    >>> 
    >>> # Work with plugins
    >>> plugin = Plugin(
    ...     id="my-plugin",
    ...     name="My Plugin",
    ...     version="1.0.0",
    ...     minAppVersion="0.15.0"
    ... )
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict


@dataclass
class ObsidianSettings:
    """Represents Obsidian vault settings and structure.
    
    This class manages the structure and validation of an Obsidian vault's
    settings directory (.obsidian), including paths to various components
    like plugins, themes, and snippets.

    Attributes:
        basePath: Root path of the Obsidian vault
        configDir: Path to the .obsidian configuration directory
        pluginDir: Optional path to the plugins directory
        themeDir: Optional path to the themes directory
        snippetDir: Optional path to the snippets directory
    
    Properties:
        settings_file: Path to app.json if it exists
        has_plugins: Whether the plugins directory exists
        has_themes: Whether the themes directory exists
        has_snippets: Whether the snippets directory exists
    
    Example:
        >>> settings = ObsidianSettings(
        ...     basePath="/path/to/vault",
        ...     configDir="/path/to/vault/.obsidian",
        ...     pluginDir="/path/to/vault/.obsidian/plugins"
        ... )
        >>> if settings.validate():
        ...     print("Valid vault")
    """
    
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
    
    iconDir: Optional[Path] = None
    """Path to the plugin icons directory, if it exists"""

    def __post_init__(self):
        """Convert string paths to Path objects and validate existence.
        
        This method ensures all paths are Path objects and resolves them
        to their absolute paths. It handles both string and Path inputs.
        """
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
        if self.iconDir and isinstance(self.iconDir, str):
            self.iconDir = Path(self.iconDir).resolve()

    def validate(self) -> bool:
        """Validate that the Obsidian settings are complete and correct.
        
        This method checks that:
        1. The base path exists and is a directory
        2. The .obsidian directory exists
        3. Required settings files are present
        4. Optional directories are valid if present
        
        Returns:
            bool: True if settings are valid, False otherwise
        """
        if not self.basePath.exists() or not self.basePath.is_dir():
            return False
        if not self.configDir.exists() or not self.configDir.is_dir():
            return False
        
        # Check optional directories if they're specified
        if self.pluginDir and not self.pluginDir.exists():
            return False
        if self.themeDir and not self.themeDir.exists():
            return False
        if self.snippetDir and not self.snippetDir.exists():
            return False
        if self.iconDir and not self.iconDir.exists():
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

    @property
    def has_plugins(self) -> bool:
        """Check if the plugins directory exists and is valid.
        
        Returns:
            bool: True if plugins directory exists and is valid
        """
        return bool(self.pluginDir and self.pluginDir.exists() and self.pluginDir.is_dir())

    @property
    def has_themes(self) -> bool:
        """Check if the themes directory exists and is valid.
        
        Returns:
            bool: True if themes directory exists and is valid
        """
        return bool(self.themeDir and self.themeDir.exists() and self.themeDir.is_dir())

    @property
    def has_snippets(self) -> bool:
        """Check if the snippets directory exists and is valid.
        
        Returns:
            bool: True if snippets directory exists and is valid
        """
        return bool(self.snippetDir and self.snippetDir.exists() and self.snippetDir.is_dir())

    @property
    def has_icons(self) -> bool:
        """Check if the plugin icons directory exists and is valid.
        
        Returns:
            bool: True if icons directory exists and is valid
        """
        return bool(self.iconDir and self.iconDir.exists() and self.iconDir.is_dir())


@dataclass
class Plugin:
    """Represents an Obsidian plugin with its metadata and settings.
    
    This class manages plugin metadata, version compatibility, and settings.
    It handles both core plugins and community plugins.

    Attributes:
        id: Unique identifier of the plugin
        name: Display name of the plugin
        version: Plugin version string
        minAppVersion: Minimum required Obsidian version
        enabled: Whether the plugin is enabled
        hasSettings: Whether the plugin has a settings file
        hasData: Whether the plugin has a data directory
        hasIcons: Whether the plugin has custom icons
    """
    
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
    
    hasSettings: bool = False
    """Whether the plugin has a settings file"""
    
    hasData: bool = False
    """Whether the plugin has a data directory"""
    
    hasIcons: bool = False
    """Whether the plugin has custom icons"""


@dataclass
class Theme:
    """Represents an Obsidian theme with its metadata and resources.
    
    This class manages theme metadata, version compatibility, and resources
    like CSS files and assets. It provides a structured way to handle
    theme-related operations and validation.

    The class handles various theme components:
    1. Core Theme Files
       - manifest.json (metadata)
       - theme.css (main theme file)
       - Additional CSS files

    2. Resource Management
       - Asset files (images, fonts)
       - CSS snippets
       - Custom stylesheets

    3. Version Compatibility
       - Theme version tracking
       - Minimum app version requirements
       - Update management

    Attributes:
        name: Theme name (must be unique within a vault)
        author: Theme author or maintainer
        version: Theme version in semver format (e.g., "1.0.0")
        minAppVersion: Minimum required Obsidian version
        enabled: Whether the theme is currently active
        hasCustomCss: Whether the theme includes custom CSS beyond theme.css
        hasSnippets: Whether the theme includes CSS snippets
        hasAssets: Whether the theme includes assets like images or fonts

    Example:
        >>> # Create a basic theme
        >>> theme = Theme(
        ...     name="Minimal",
        ...     author="kepano",
        ...     version="6.2.3",
        ...     minAppVersion="0.15.0"
        ... )
        >>> 
        >>> # Theme with additional resources
        >>> theme = Theme(
        ...     name="Custom Theme",
        ...     author="user",
        ...     version="1.0.0",
        ...     minAppVersion="0.15.0",
        ...     hasCustomCss=True,
        ...     hasSnippets=True,
        ...     hasAssets=True
        ... )

    Note:
        - Theme names must be unique within a vault
        - Version strings should follow semantic versioning
        - Custom CSS files should be in the theme directory
        - Assets should be in an 'assets' subdirectory
        - Snippets should be in the vault's snippets directory
    """
    
    name: str
    """Theme name (must be unique within a vault)"""
    
    author: str
    """Theme author or maintainer"""
    
    version: str
    """Theme version in semver format (e.g., "1.0.0")"""
    
    minAppVersion: str
    """Minimum required Obsidian version"""
    
    enabled: bool = False
    """Whether the theme is currently active"""
    
    hasCustomCss: bool = False
    """Whether the theme includes custom CSS beyond theme.css"""
    
    hasSnippets: bool = False
    """Whether the theme includes CSS snippets"""
    
    hasAssets: bool = False
    """Whether the theme includes assets (images, fonts, etc.)"""


@dataclass
class VaultMetadata:
    """Represents comprehensive metadata about an Obsidian vault.
    
    This class provides a complete view of a vault's contents and settings,
    including plugins, themes, and snippets. It serves as a central point
    for accessing and managing all vault-related information.

    The class organizes vault metadata into several categories:

    1. Core Settings
       - Vault path and configuration
       - Settings directory structure
       - Basic vault information

    2. Plugin Management
       - Installed plugins (core and community)
       - Plugin settings and data
       - Plugin compatibility information
       - Resource management (icons, etc.)

    3. Theme Management
       - Installed themes
       - Theme settings and customizations
       - CSS snippets and assets
       - Theme compatibility tracking

    4. Resource Tracking
       - CSS snippets
       - Custom assets
       - Template files
       - Configuration backups

    Attributes:
        path: Path to the vault (resolved to absolute path)
        settings: Vault settings object (ObsidianSettings instance)
        plugins: Dictionary of installed plugins by ID (Plugin instances)
        themes: Dictionary of installed themes by name (Theme instances)
        snippets: List of CSS snippet paths (resolved Path objects)

    Example:
        >>> # Create basic vault metadata
        >>> metadata = VaultMetadata(
        ...     path=Path("~/Documents/MyVault"),
        ...     settings=ObsidianSettings(...),
        ...     plugins={},
        ...     themes={},
        ...     snippets=[]
        ... )
        >>> 
        >>> # Access vault components
        >>> print(f"Vault: {metadata.path.name}")
        >>> print(f"Plugins: {len(metadata.plugins)}")
        >>> print(f"Themes: {len(metadata.themes)}")
        >>> print(f"Snippets: {len(metadata.snippets)}")
        >>> 
        >>> # Check specific components
        >>> if "minimal" in metadata.themes:
        ...     theme = metadata.themes["minimal"]
        ...     print(f"Theme version: {theme.version}")
        >>> 
        >>> if "dataview" in metadata.plugins:
        ...     plugin = metadata.plugins["dataview"]
        ...     print(f"Plugin enabled: {plugin.enabled}")

    Note:
        - All paths are resolved to absolute paths
        - Plugin IDs must be unique
        - Theme names must be unique
        - Snippets are tracked by their file paths
        - The settings object validates vault structure
    """
    
    path: Path
    """Path to the vault (resolved to absolute path)"""
    
    settings: ObsidianSettings
    """Vault settings object (ObsidianSettings instance)"""
    
    plugins: Dict[str, Plugin]
    """Dictionary of installed plugins by ID (Plugin instances)"""
    
    themes: Dict[str, Theme]
    """Dictionary of installed themes by name (Theme instances)"""
    
    snippets: List[Path]
    """List of CSS snippet paths (resolved Path objects)"""

    def __post_init__(self):
        """Convert string paths to Path objects and resolve them.
        
        This method ensures that:
        1. The vault path is a resolved Path object
        2. All snippet paths are resolved Path objects
        3. The settings object is properly initialized
        
        Note:
            This is called automatically after instance creation
        """
        if isinstance(self.path, str):
            self.path = Path(self.path).resolve()


class AppSettings(BaseModel):
    """Schema for app.json settings.
    
    This model validates the main Obsidian settings file (app.json).
    It allows any valid JSON fields while providing type checking
    for known fields.

    The app.json file contains core application settings including:
    1. Interface Settings
       - Window size and position
       - Sidebar configuration
       - Tab behavior
       - File explorer settings

    2. Editor Settings
       - Font settings
       - Line numbers
       - Spellcheck
       - Auto-formatting

    3. File Handling
       - Default locations
       - Attachment handling
       - File extensions
       - Link behavior

    4. Search Settings
       - Search options
       - Indexing preferences
       - Filter settings

    Example:
        >>> # Create settings with defaults
        >>> settings = AppSettings()
        >>> 
        >>> # Create settings with custom values
        >>> settings = AppSettings(
        ...     alwaysUpdateLinks=True,
        ...     attachmentFolderPath="assets",
        ...     defaultViewMode="source",
        ...     foldHeading=True,
        ...     showLineNumber=True
        ... )
        >>> 
        >>> # Access settings
        >>> print(f"View mode: {settings.defaultViewMode}")
        >>> print(f"Assets path: {settings.attachmentFolderPath}")

    Note:
        - Unknown fields are allowed and preserved
        - Known fields are type-checked
        - Some fields may be version-dependent
        - Changes require app restart
    """
    model_config = ConfigDict(extra='allow')


class AppearanceSettings(BaseModel):
    """Schema for appearance.json settings.
    
    This model validates Obsidian's appearance settings file.
    It allows any valid JSON fields while providing type checking
    for known fields.

    The appearance.json file manages visual settings including:
    1. Theme Settings
       - Active theme
       - Light/dark mode
       - Custom CSS
       - Snippet management

    2. Interface Customization
       - Font settings
       - Colors and contrast
       - Workspace layout
       - Custom styling

    3. Reading Experience
       - Text size and spacing
       - Line width
       - Paragraph spacing
       - List indentation

    4. Mobile Settings
       - Touch interface
       - Gesture controls
       - Mobile-specific layout

    Example:
        >>> # Create settings with defaults
        >>> settings = AppearanceSettings()
        >>> 
        >>> # Create settings with custom values
        >>> settings = AppearanceSettings(
        ...     theme="obsidian",
        ...     baseFontSize=16,
        ...     textFontFamily="Inter",
        ...     monospaceFontFamily="Fira Code",
        ...     enabledCssSnippets=["custom"]
        ... )
        >>> 
        >>> # Access settings
        >>> print(f"Theme: {settings.theme}")
        >>> print(f"Font size: {settings.baseFontSize}px")

    Note:
        - Theme changes take effect immediately
        - Font changes may require reload
        - CSS snippets must be in snippets directory
        - Mobile settings sync separately
    """
    model_config = ConfigDict(extra='allow')


class HotkeysSettings(BaseModel):
    """Schema for hotkeys.json settings.
    
    This model validates Obsidian's hotkey configuration file.
    It allows any valid JSON fields while providing type checking
    for known fields.

    The hotkeys.json file manages keyboard shortcuts for:
    1. Core Commands
       - File operations
       - Navigation
       - Search
       - View modes

    2. Editor Commands
       - Text formatting
       - List management
       - Link creation
       - Block operations

    3. Plugin Commands
       - Plugin-specific actions
       - Custom commands
       - Workspace management

    4. Custom Commands
       - User-defined actions
       - Command combinations
       - Multi-step operations

    Example:
        >>> # Create settings with defaults
        >>> settings = HotkeysSettings()
        >>> 
        >>> # Create settings with custom hotkeys
        >>> settings = HotkeysSettings(**{
        ...     "editor:toggle-bold": ["Mod+B"],
        ...     "editor:toggle-italics": ["Mod+I"],
        ...     "app:go-back": ["Mod+Alt+Left"],
        ...     "workspace:split-vertical": ["Mod+\\"]
        ... })
        >>> 
        >>> # Access hotkeys
        >>> print(f"Bold: {settings.dict()['editor:toggle-bold']}")
        >>> print(f"Back: {settings.dict()['app:go-back']}")

    Note:
        - Hotkeys must be unique
        - Platform-specific modifiers
        - Plugin hotkeys included
        - Changes take effect immediately
    """
    model_config = ConfigDict(extra='allow')


# Map of file names to their schema classes for validation
SCHEMA_MAP: Dict[str, Any] = {
    'app.json': AppSettings,
    'appearance.json': AppearanceSettings,
    'hotkeys.json': HotkeysSettings,
    'types.json': BaseModel,
    'templates.json': BaseModel,
    'core-plugins.json': BaseModel,
    'community-plugins.json': BaseModel,
    'core-plugins-migration.json': BaseModel,
}