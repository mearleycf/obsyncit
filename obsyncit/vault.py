"""
Vault Manager - Handles Obsidian vault operations.

This module provides functionality for managing Obsidian vaults,
including validation and file operations.
"""

import json
from pathlib import Path
from typing import Optional, Set, Union

from loguru import logger

from obsyncit.errors import (
    VaultError,
    handle_file_operation_error,
    handle_json_error
)


class VaultManager:
    """Manages operations on an Obsidian vault."""

    def __init__(self, vault_path: Union[str, Path]) -> None:
        """Initialize the vault manager.

        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path).resolve()
        self.settings_dir = self.vault_path / ".obsidian"

    def validate_vault(self) -> bool:
        """Validate that this is a valid Obsidian vault.

        Returns:
            bool: True if the vault is valid
        """
        try:
            # Check that vault directory exists
            if not self.vault_path.exists():
                raise VaultError(
                    "Vault directory does not exist",
                    f"Path: {self.vault_path}"
                )

            # Check that vault directory is readable
            if not self.vault_path.is_dir():
                raise VaultError(
                    "Vault path is not a directory",
                    f"Path: {self.vault_path}"
                )

            # Check that .obsidian directory exists
            if not self.settings_dir.exists():
                raise VaultError(
                    "No .obsidian directory found",
                    f"Path: {self.settings_dir}"
                )

            # Check that .obsidian directory is readable
            if not self.settings_dir.is_dir():
                raise VaultError(
                    ".obsidian path is not a directory",
                    f"Path: {self.settings_dir}"
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
            Set[str]: Set of settings file names
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
            Set[str]: Set of settings directory names
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
            file_name: Name of the settings file

        Returns:
            Optional[Path]: Full path to the file, or None if not found
        """
        try:
            file_path = self.settings_dir / file_name
            return file_path if file_path.exists() else None

        except Exception as e:
            handle_file_operation_error(e, "getting file path", file_name)
            return None
