"""Vault Manager for Obsidian Settings.

This module provides comprehensive functionality for managing Obsidian vaults,
including validation, file operations, and settings management. It handles:

1. Vault Management
   - Vault structure validation
   - Settings directory management
   - File and directory operations

2. Settings Files
   - Core settings (app.json, appearance.json, etc.)
   - Plugin settings (core and community)
   - Theme configuration
   - Type definitions and templates

3. Resource Directories
   - Plugin directories and files
   - Theme directories
   - CSS snippets
   - Plugin icons and resources

Example Usage:
    >>> from obsyncit.vault import VaultManager
    >>> 
    >>> # Create manager for a vault
    >>> vault = VaultManager("/path/to/vault")
    >>> 
    >>> # Validate vault structure
    >>> if vault.validate_vault():
    ...     print("Valid Obsidian vault")
    >>> 
    >>> # Get settings files
    >>> settings = vault.get_settings_files()
    >>> print(f"Found settings: {settings}")
    >>> 
    >>> # Get directories
    >>> dirs = vault.get_settings_dirs()
    >>> print(f"Found directories: {dirs}")
    >>> 
    >>> # Get complete vault settings
    >>> if settings := vault.get_vault_settings():
    ...     if settings.has_plugins:
    ...         print("Plugins directory exists")
    ...         print(f"Located at: {settings.pluginDir}")
    ...     if settings.has_themes:
    ...         print("Themes directory exists")
    ...         print(f"Located at: {settings.themeDir}")
"""

import json
from pathlib import Path
from typing import Optional, Set, Union, List

from loguru import logger

from obsyncit.errors import (
    VaultError,
    handle_file_operation_error,
    handle_json_error
)
from obsyncit.schemas.obsidian import ObsidianSettings


class VaultManager:
    """Manages operations on an Obsidian vault.
    
    This class provides comprehensive methods for validating and managing
    Obsidian vaults, including vault structure verification, settings file
    management, and resource directory handling.
    
    The manager handles:
    - Vault structure validation
    - Settings file operations
    - JSON validation
    - Directory management
    - Resource handling (plugins, themes, etc.)
    
    Attributes:
        vault_path: Absolute path to the Obsidian vault
        settings_dir: Path to the .obsidian configuration directory
    
    Important Files:
        - app.json: Core application settings
        - appearance.json: UI and theme settings
        - hotkeys.json: Keyboard shortcuts
        - types.json: Type definitions
        - templates.json: Template settings
        - community-plugins.json: Plugin list and settings
        - core-plugins.json: Built-in plugin settings
        - core-plugins-migration.json: Plugin migration data
    
    Important Directories:
        - plugins/: Plugin data and configuration
        - themes/: Custom themes
        - snippets/: CSS snippets
        - icons/: Plugin icons and resources
    
    Example:
        >>> # Initialize and validate a vault
        >>> vault = VaultManager("/path/to/vault")
        >>> if vault.validate_vault():
        ...     print(f"Valid vault at {vault.vault_path}")
        ...     print(f"Settings dir: {vault.settings_dir}")
        >>> 
        >>> # Check for specific settings files
        >>> if (vault.settings_dir / "app.json").exists():
        ...     print("Found app.json")
        >>> 
        >>> # List all JSON settings
        >>> settings = vault.get_settings_files()
        >>> print("Settings files:", settings)
        >>> 
        >>> # Check plugin directory
        >>> plugin_dir = vault.settings_dir / "plugins"
        >>> if plugin_dir.exists():
        ...     plugins = list(plugin_dir.glob("*"))
        ...     print(f"Found {len(plugins)} plugins")
    """

    def __init__(self, vault_path: Union[str, Path]) -> None:
        """Initialize the vault manager.

        This method sets up the vault manager by resolving the vault path
        and setting up the settings directory path. The vault path is resolved
        to its absolute path to ensure consistent operations.

        Args:
            vault_path: Path to the Obsidian vault (string or Path)
        
        Example:
            >>> # Initialize with string path
            >>> vault = VaultManager("/path/to/vault")
            >>> 
            >>> # Initialize with Path object
            >>> from pathlib import Path
            >>> vault = VaultManager(Path.home() / "Documents" / "MyVault")
            >>> 
            >>> # Access resolved paths
            >>> print(f"Vault path: {vault.vault_path}")
            >>> print(f"Settings: {vault.settings_dir}")
        """
        self.vault_path = Path(vault_path).resolve()
        self.settings_dir = self.vault_path / ".obsidian"

    def __repr__(self) -> str:
        """Return string representation of the VaultManager.
        
        Returns:
            String representation showing the vault path
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> str(vault)
            "VaultManager(vault_path='/path/to/vault')"
            >>> repr(vault)
            "VaultManager(vault_path='/path/to/vault')"
        """
        return f"VaultManager(vault_path='{self.vault_path}')"

    def validate_vault(self) -> bool:
        """Validate that this is a valid Obsidian vault.

        This method performs comprehensive validation of the vault structure:
        1. Checks vault directory exists
        2. Verifies .obsidian directory exists
        3. Confirms presence of essential settings files
        4. Validates directory permissions
        5. Checks for basic vault structure

        Returns:
            True if the vault is valid and accessible
            
        Raises:
            VaultError: If any validation checks fail with details
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> try:
            ...     if vault.validate_vault():
            ...         print("Valid Obsidian vault")
            ...         print("Settings dir:", vault.settings_dir)
            ... except VaultError as e:
            ...     print(f"Invalid vault: {e}")
            ...     print(f"Path: {e.vault_path}")
        """
        try:
            if not self.vault_path.exists():
                raise VaultError(
                    "Vault directory does not exist",
                    self.vault_path
                )

            if not self.settings_dir.exists():
                raise VaultError(
                    "No .obsidian directory found",
                    self.settings_dir
                )

            # Check if there are any settings files
            if not any(self.settings_dir.glob("*.json")):
                raise VaultError(
                    "No settings files found",
                    self.settings_dir
                )

            return True

        except VaultError:
            raise
        except Exception as e:
            handle_file_operation_error(e, "validating vault", self.vault_path)
            return False

    def validate_json_file(self, file_path: Path) -> bool:
        """Validate that a file contains valid JSON.

        This method checks both the existence and syntax of a JSON file.
        It does not validate against any specific schema, only that the
        file contains valid JSON data.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if the file exists and contains valid JSON
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> app_json = vault.settings_dir / "app.json"
            >>> 
            >>> # Basic validation
            >>> if vault.validate_json_file(app_json):
            ...     print("Valid JSON file")
            >>> 
            >>> # Error handling
            >>> try:
            ...     vault.validate_json_file(app_json)
            ... except json.JSONDecodeError as e:
            ...     print(f"Invalid JSON: {e}")
            ... except FileNotFoundError:
            ...     print("File not found")
        """
        try:
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False

            with open(file_path, encoding='utf-8') as f:
                json.load(f)
            return True

        except json.JSONDecodeError as e:
            handle_json_error(e, file_path)
            return False
        except Exception as e:
            handle_file_operation_error(e, "validating JSON file", file_path)
            return False

    def get_settings_files(self) -> Set[str]:
        """Get all settings files in the vault.

        This method returns the names of all JSON configuration files
        in the vault's .obsidian directory. This includes:
        - Core settings files (app.json, appearance.json)
        - Plugin configuration files
        - Theme settings
        - Type definitions
        - Template configurations

        Returns:
            Set of settings file names
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> 
            >>> # Get all settings files
            >>> files = vault.get_settings_files()
            >>> print("Found files:", files)
            >>> 
            >>> # Check for specific files
            >>> if "app.json" in files:
            ...     print("Found app.json")
            >>> if "appearance.json" in files:
            ...     print("Found appearance.json")
            >>> 
            >>> # Count settings files
            >>> print(f"Total settings: {len(files)}")
        """
        try:
            if not self.settings_dir.exists():
                return set()

            return {
                f.name for f in self.settings_dir.glob("*.json")
                if f.is_file()
            }

        except Exception as e:
            handle_file_operation_error(e, "listing settings files", self.settings_dir)
            return set()

    def get_settings_dirs(self) -> Set[str]:
        """Get all settings directories in the vault.

        Returns the names of all configuration directories in the
        vault's .obsidian directory. This includes:
        - plugins/: Plugin installation directory
        - themes/: Custom theme directory
        - snippets/: CSS snippets directory
        - icons/: Plugin icon resources

        Returns:
            Set of directory names
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> 
            >>> # Get all directories
            >>> dirs = vault.get_settings_dirs()
            >>> print("Found directories:", dirs)
            >>> 
            >>> # Check for specific directories
            >>> if "plugins" in dirs:
            ...     plugins_dir = vault.settings_dir / "plugins"
            ...     plugin_count = len(list(plugins_dir.glob("*")))
            ...     print(f"Found {plugin_count} plugins")
            >>> 
            >>> # Check for themes
            >>> if "themes" in dirs:
            ...     themes_dir = vault.settings_dir / "themes"
            ...     theme_count = len(list(themes_dir.glob("*.css")))
            ...     print(f"Found {theme_count} themes")
        """
        try:
            if not self.settings_dir.exists():
                return set()

            return {
                d.name for d in self.settings_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            }

        except Exception as e:
            handle_file_operation_error(e, "listing settings directories", self.settings_dir)
            return set()

    def get_file_path(self, file_name: str) -> Optional[Path]:
        """Get the full path to a settings file.

        Resolves the full path to a settings file in the vault's
        .obsidian directory. This is useful for accessing specific
        configuration files when you know their names.

        Args:
            file_name: Name of the settings file (e.g., "app.json")

        Returns:
            Full path to the file if it exists, None otherwise
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> 
            >>> # Get path to app.json
            >>> if path := vault.get_file_path("app.json"):
            ...     print(f"Found at: {path}")
            ...     with open(path) as f:
            ...         settings = json.load(f)
            ...     print("Settings:", settings)
            >>> 
            >>> # Check multiple files
            >>> for file in ["appearance.json", "hotkeys.json"]:
            ...     if path := vault.get_file_path(file):
            ...         print(f"Found {file}")
            ...     else:
            ...         print(f"Missing {file}")
        """
        try:
            file_path = self.settings_dir / file_name
            return file_path if file_path.exists() else None

        except Exception as e:
            handle_file_operation_error(e, "getting file path", file_name)
            return None

    def get_vault_settings(self) -> Optional[ObsidianSettings]:
        """Get the complete vault settings configuration.

        Creates an ObsidianSettings object containing paths to all
        configuration components, including:
        - Base vault path
        - Settings directory
        - Plugin directory
        - Theme directory
        - Snippets directory
        - Icons directory

        Returns:
            ObsidianSettings object if vault is valid, None otherwise
            
        Example:
            >>> vault = VaultManager("/path/to/vault")
            >>> 
            >>> # Get complete settings
            >>> if settings := vault.get_vault_settings():
            ...     # Check plugin configuration
            ...     if settings.has_plugins:
            ...         print(f"Plugins at: {settings.pluginDir}")
            ...         print(f"Icons at: {settings.iconDir}")
            ...     
            ...     # Check theme configuration
            ...     if settings.has_themes:
            ...         print(f"Themes at: {settings.themeDir}")
            ...         print(f"Snippets at: {settings.snippetDir}")
            ...     
            ...     # Access base paths
            ...     print(f"Vault: {settings.basePath}")
            ...     print(f"Config: {settings.configDir}")
        """
        try:
            if not self.validate_vault():
                return None

            settings = ObsidianSettings(
                basePath=self.vault_path,
                configDir=self.settings_dir,
                pluginDir=self.settings_dir / "plugins" if (self.settings_dir / "plugins").exists() else None,
                themeDir=self.settings_dir / "themes" if (self.settings_dir / "themes").exists() else None,
                snippetDir=self.settings_dir / "snippets" if (self.settings_dir / "snippets").exists() else None,
                iconDir=self.settings_dir / "icons" if (self.settings_dir / "icons").exists() else None,
            )
            
            return settings if settings.validate() else None

        except Exception as e:
            handle_file_operation_error(e, "getting vault settings", self.vault_path)
            return None