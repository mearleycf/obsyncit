"""
Vault management functionality.

This module handles operations related to Obsidian vaults, including
validation and file operations.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from obsyncit.schemas import SCHEMA_MAP
from obsyncit.errors import VaultError, ValidationError


class VaultManager:
    """Handles operations specific to Obsidian vaults."""
    
    def __init__(self, vault_path: str | Path, settings_dir: str = ".obsidian"):
        """
        Initialize the vault manager.
        
        Args:
            vault_path: Path to the Obsidian vault
            settings_dir: Name of the settings directory (default: .obsidian)
            
        Raises:
            VaultError: If the vault path is invalid or inaccessible
        """
        try:
            self.vault_path = Path(vault_path).expanduser().resolve()
            self.settings_dir = settings_dir
            self.settings_path = self.vault_path / self.settings_dir
        except Exception as e:
            raise VaultError("Failed to initialize vault manager", vault_path, str(e))
    
    def validate_vault(self) -> bool:
        """
        Validate that the path exists and is an Obsidian vault.
        
        Returns:
            bool: True if path is valid, False otherwise
            
        Raises:
            VaultError: If validation fails due to permissions or other errors
        """
        try:
            if not self.vault_path.exists():
                raise VaultError(
                    "Vault does not exist",
                    self.vault_path
                )
            
            if not self.settings_path.exists():
                raise VaultError(
                    f"Vault has no {self.settings_dir} directory",
                    self.vault_path,
                    f"Expected settings at: {self.settings_path}"
                )
                
            return True
        except VaultError:
            raise
        except PermissionError as e:
            raise VaultError(
                "Permission denied accessing vault",
                self.vault_path,
                str(e)
            )
        except Exception as e:
            raise VaultError(
                "Error validating vault",
                self.vault_path,
                str(e)
            )

    def validate_json_file(self, file_path: Path) -> bool:
        """
        Validate that a file contains valid JSON and matches its schema.
        
        Args:
            file_path: Path to the JSON file to validate
            
        Returns:
            bool: True if JSON is valid and matches schema, False otherwise
            
        Raises:
            ValidationError: If the file fails JSON or schema validation
        """
        try:
            if not file_path.exists():
                return True  # Skip validation for non-existent files
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                handle_json_error(e, file_path)
                raise ValidationError(
                    "Invalid JSON format",
                    file_path,
                    [f"Error at line {e.lineno}, column {e.colno}: {e.msg}"]
                )
                
            # Get schema for this file type
            file_name = file_path.name
            if file_name in SCHEMA_MAP:
                try:
                    validate(instance=data, schema=SCHEMA_MAP[file_name])
                except JsonSchemaValidationError as e:
                    schema_errors = [
                        f"Path: {' -> '.join(str(p) for p in e.path)}",
                        f"Error: {e.message}",
                        f"Schema path: {' -> '.join(str(p) for p in e.schema_path)}"
                    ]
                    raise ValidationError(
                        "Schema validation failed",
                        file_path,
                        schema_errors
                    )
                    
            return True
        except (ValidationError, VaultError):
            raise
        except PermissionError as e:
            handle_file_operation_error(e, "reading", file_path)
            raise ValidationError(
                "Permission denied reading file",
                file_path,
                [str(e)]
            )
        except Exception as e:
            handle_file_operation_error(e, "validating", file_path)
            raise ValidationError(
                "Error validating file",
                file_path,
                [str(e)]
            )

    def get_settings_file(self, filename: str) -> Optional[Path]:
        """
        Get the path to a settings file in the vault.
        
        Args:
            filename: Name of the settings file
            
        Returns:
            Optional[Path]: Path to the settings file if it exists, None otherwise
            
        Raises:
            VaultError: If there are issues accessing the settings directory
        """
        try:
            file_path = self.settings_path / filename
            return file_path if file_path.exists() else None
        except Exception as e:
            raise VaultError(
                f"Error accessing settings file: {filename}",
                self.vault_path,
                str(e)
            ) 