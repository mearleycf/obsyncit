"""
Obsidian vault management module.

This module provides functionality for interacting with Obsidian vaults,
including path validation and JSON settings validation.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger
from jsonschema import validate, ValidationError

from schemas import SCHEMA_MAP


class VaultManager:
    """Handles operations specific to Obsidian vaults."""
    
    def __init__(self, vault_path: str | Path, settings_dir: str = ".obsidian"):
        """
        Initialize the vault manager.
        
        Args:
            vault_path: Path to the Obsidian vault
            settings_dir: Name of the settings directory (default: .obsidian)
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.settings_dir = settings_dir
        self.settings_path = self.vault_path / self.settings_dir
    
    def validate_vault(self) -> bool:
        """
        Validate that the path exists and is an Obsidian vault.
        
        Returns:
            bool: True if path is valid, False otherwise
        """
        try:
            if not self.vault_path.exists():
                logger.error(f"Vault does not exist: {self.vault_path}")
                return False
            
            if not self.settings_path.exists():
                logger.error(f"Vault has no {self.settings_dir} directory: {self.settings_path}")
                return False
                
            return True
        except PermissionError as e:
            logger.error(f"Permission denied accessing vault path: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error validating vault path: {str(e)}")
            return False

    def validate_json_file(self, file_path: Path) -> bool:
        """
        Validate that a file contains valid JSON and matches its schema.
        
        Args:
            file_path: Path to the JSON file to validate
            
        Returns:
            bool: True if JSON is valid and matches schema, False otherwise
        """
        try:
            if not file_path.exists():
                return True  # Skip validation for non-existent files
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Get schema for this file type
            file_name = file_path.name
            if file_name in SCHEMA_MAP:
                try:
                    validate(instance=data, schema=SCHEMA_MAP[file_name])
                except ValidationError as e:
                    logger.error(f"Schema validation failed for {file_path}:")
                    logger.error(f"  - {e.message}")
                    logger.debug(f"  - Path: {' -> '.join(str(p) for p in e.path)}")
                    logger.debug(f"  - Schema path: {' -> '.join(str(p) for p in e.schema_path)}")
                    return False
                    
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return False
        except PermissionError as e:
            logger.error(f"Permission denied reading {file_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            return False

    def get_settings_file(self, filename: str) -> Optional[Path]:
        """
        Get the path to a settings file in the vault.
        
        Args:
            filename: Name of the settings file
            
        Returns:
            Optional[Path]: Path to the settings file if it exists, None otherwise
        """
        file_path = self.settings_path / filename
        return file_path if file_path.exists() else None 