"""
Configuration schema for ObsyncIt.

This module defines the configuration schema for the ObsyncIt tool,
validating user-provided configuration files.
"""

from enum import Enum
from pathlib import Path
from typing import Union, Optional, List
from pydantic import BaseModel, Field, validator, root_validator


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


class CoreSettingsConfig(BaseModel):
    """
    Configuration for core Obsidian settings synchronization.
    
    Controls which core settings files are synchronized:
    - app.json: General application settings
    - appearance.json: Theme and visual preferences
    - hotkeys.json: Keyboard shortcuts
    - graph.json: Graph view settings
    - workspace.json: Workspace layout (disabled by default)
    """

    app: bool = Field(
        default=True,
        description="Sync app.json (recommended for consistent behavior)"
    )
    appearance: bool = Field(
        default=True,
        description="Sync appearance.json (recommended for consistent look)"
    )
    hotkeys: bool = Field(
        default=True,
        description="Sync hotkeys.json (recommended for consistent shortcuts)"
    )
    graph: bool = Field(
        default=True,
        description="Sync graph.json (graph view settings)"
    )
    workspace: bool = Field(
        default=False,
        description="Sync workspace.json (caution: may conflict with local layouts)"
    )


class PluginConfig(BaseModel):
    """
    Configuration for plugin synchronization.
    
    Controls synchronization of:
    - Core plugin settings and states
    - Community plugin settings
    - Plugin installation states
    """

    core_enabled: bool = Field(
        default=True,
        description="Sync core plugin enabled/disabled states"
    )
    core_settings: bool = Field(
        default=True,
        description="Sync core plugin settings"
    )
    community_enabled: bool = Field(
        default=True,
        description="Sync community plugin enabled/disabled states"
    )
    community_settings: bool = Field(
        default=True,
        description="Sync community plugin settings"
    )
    sync_plugin_list: bool = Field(
        default=False,
        description="Install/remove plugins to match source (use with caution)"
    )


class CustomizationConfig(BaseModel):
    """
    Configuration for visual customization synchronization.
    
    Controls synchronization of:
    - Themes (CSS files in themes directory)
    - Snippets (CSS snippets for custom styling)
    - Custom fonts
    """

    themes: bool = Field(
        default=True,
        description="Sync theme files"
    )
    snippets: bool = Field(
        default=True,
        description="Sync CSS snippets"
    )
    fonts: bool = Field(
        default=False,
        description="Sync custom fonts (may increase sync size significantly)"
    )


class SyncConfig(BaseModel):
    """
    Sync configuration settings.
    
    This class defines which Obsidian settings and customizations
    are synchronized between vaults. It provides fine-grained control
    over different aspects of synchronization.
    
    Example Configuration:
        ```toml
        [sync]
        # Core Settings
        [sync.core_settings]
        app = true
        appearance = true
        hotkeys = true
        graph = true
        workspace = false  # Workspace layout often better kept separate
        
        # Plugin Settings
        [sync.plugins]
        core_enabled = true
        core_settings = true
        community_enabled = true
        community_settings = true
        sync_plugin_list = false  # Be cautious with automatic plugin installation
        
        # Visual Customization
        [sync.customization]
        themes = true
        snippets = true
        fonts = false  # Fonts can be large, sync manually if needed
        ```
    
    Common Use Cases:
    1. Full Sync (except workspace):
       - Enable all settings except workspace.json
       - Good for personal vaults where you want identical setup
    
    2. Visual-Only Sync:
       - Enable only appearance, themes, and snippets
       - Good for maintaining consistent look while keeping separate functionality
    
    3. Functional Sync:
       - Enable app settings, hotkeys, and plugins
       - Good for maintaining consistent behavior while allowing visual customization
    
    4. Minimal Sync:
       - Enable only core settings
       - Good for basic consistency while allowing local customization
    """

    core_settings: CoreSettingsConfig = Field(
        default_factory=CoreSettingsConfig,
        description="Core settings synchronization options"
    )
    
    plugins: PluginConfig = Field(
        default_factory=PluginConfig,
        description="Plugin synchronization options"
    )
    
    customization: CustomizationConfig = Field(
        default_factory=CustomizationConfig,
        description="Visual customization synchronization options"
    )
    
    dry_run: bool = Field(
        default=False,
        description="Simulate sync without making changes"
    )
    
    ignore_errors: bool = Field(
        default=False,
        description="Continue sync even if non-critical errors occur"
    )

    @root_validator
    def validate_plugin_dependencies(cls, values: dict) -> dict:
        """
        Validate plugin configuration dependencies.
        
        Ensures that:
        1. If sync_plugin_list is True, community_enabled must be True
        2. If community_settings is True, community_enabled should be True
        
        Args:
            values: Dictionary of configuration values

        Returns:
            dict: Validated configuration values

        Raises:
            ValueError: If configuration combinations are invalid
        """
        plugins = values.get("plugins", {})
        if not isinstance(plugins, dict):
            return values
            
        if plugins.get("sync_plugin_list") and not plugins.get("community_enabled"):
            raise ValueError(
                "sync_plugin_list requires community_enabled to be True"
            )
            
        if plugins.get("community_settings") and not plugins.get("community_enabled"):
            raise ValueError(
                "community_settings requires community_enabled to be True"
            )
            
        return values


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
