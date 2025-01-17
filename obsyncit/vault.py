"""Vault Manager - Handles Obsidian vault operations.

This module provides functionality for managing Obsidian vaults,
including validation and file operations.
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
    
    This class provides methods for validating and managing Obsidian vaults,
    including checking vault structure, managing settings files, and handling
    JSON validation.
    
    Attributes:
        vault_path (Path): Path to the Obsidian vault
        settings_dir (Path): Path to the .obsidian configuration directory
    """

    def __init__(self, vault_path: Union[str, Path]) -> None:
        """Initialize the vault manager.

        Args:
            vault_path: Path to the Obsidian vault
        
        Note:
            The vault path will be resolved to its absolute path during initialization.
        """
        self.vault_path = Path(vault_path).resolve()
        self.settings_dir = self.vault_path / ".obsidian"

    def __repr__(self) -> str:
        """Return string representation of the VaultManager.
        
        Returns:
            str: String representation showing the vault path
        """
        return f"VaultManager(vault_path='{self.vault_path}')"

    def validate_vault(self) -> bool:
        """Validate that this is a valid Obsidian vault.

        This method checks:
        - Vault directory exists and is readable
        - .obsidian directory exists and is readable
        - At least one settings file exists

        Returns:
            bool: True if the vault is valid
            
        Raises:
            VaultError: If any validation checks fail
        """
        try:
            if not self.vault_path.exists():
                raise VaultError(
                    "Vault directory does not exist",
                    self.vault_path
                )

            if not self.vault_path.is_dir():
                raise VaultError(
                    "Vault path is not a directory",
                    self.vault_path
                )

            if not self.settings_dir.exists():
                raise VaultError(
                    "No .obsidian directory found",
                    self.settings_dir
                )

            if not self.settings_dir.is_dir():
                raise VaultError(
                    ".obsidian path is not a directory",
                    self.settings_dir
                )

            # Check if can access settings directory
            try:
                list(self.settings_dir.iterdir())
            except (PermissionError, OSError) as e:
                raise VaultError(
                    f"Cannot access settings directory: {e}",
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

        Args:
            file_path: Path to the file to validate

        Returns:
            bool: True if the file contains valid JSON
            
        Note:
            This method only validates JSON syntax, not schema compliance.
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
        """Get a list of settings files in the vault.

        Returns:
            Set[str]: Set of settings file names (e.g., ["app.json", "appearance.json"])
            
        Note:
            Only returns .json files in the root of the .obsidian directory.
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
        """Get a list of settings directories in the vault.

        Returns:
            Set[str]: Set of settings directory names (e.g., ["plugins", "themes"])
            
        Note:
            Only returns non-hidden directories in the .obsidian directory.
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

        Args:
            file_name: Name of the settings file (e.g., "app.json")

        Returns:
            Optional[Path]: Full path to the file, or None if not found
            
        Note:
            The file must exist in the .obsidian directory to be returned.
        """
        try:
            file_path = self.settings_dir / file_name
            return file_path if file_path.exists() else None

        except Exception as e:
            handle_file_operation_error(e, "getting file path", file_name)
            return None

    def get_vault_settings(self) -> Optional[ObsidianSettings]:
        """Get the vault settings configuration.

        Returns:
            Optional[ObsidianSettings]: The vault settings if available, None otherwise
            
        Note:
            This creates an ObsidianSettings instance with paths to various
            configuration directories if they exist.
        """
        try:
            if not self.validate_vault():
                return None

            settings = ObsidianSettings(
                basePath=self.vault_path,
                configDir=self.settings_dir,
                pluginDir=self.settings_dir / "plugins" if (self.settings_dir / "plugins").exists() else None,
                themeDir=self.settings_dir / "themes" if (self.settings_dir / "themes").exists() else None,
                snippetDir=self.settings_dir / "snippets" if (self.settings_dir / "snippets").exists() else None
            )
            
            return settings if settings.validate() else None

        except Exception as e:
            handle_file_operation_error(e, "getting vault settings", self.vault_path)
            return None
