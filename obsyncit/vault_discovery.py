"""
Vault Discovery - Find Obsidian vaults in the filesystem.

This module provides functionality for discovering Obsidian vaults
in the filesystem by searching directories for .obsidian folders.
"""

from pathlib import Path
from typing import List, Optional
from loguru import logger

from obsyncit.vault import VaultManager


class VaultDiscovery:
    """Discovers Obsidian vaults in the filesystem."""

    def __init__(self, search_path: Path, max_depth: int = 3) -> None:
        """Initialize the vault discovery.

        Args:
            search_path: Root path to start searching from
            max_depth: Maximum directory depth to search
        """
        self.search_path = Path(search_path).resolve()
        self.max_depth = max_depth

    def is_valid_vault(self, path: Path) -> bool:
        """Check if a path is a valid Obsidian vault.
        
        A valid vault must have a .obsidian directory with at least one settings file.
        """
        obsidian_dir = path / ".obsidian"
        if not obsidian_dir.is_dir():
            return False
        
        # Check for at least one settings file
        settings_files = list(obsidian_dir.glob("*.json"))
        return len(settings_files) > 0

    def find_vaults(self) -> List[Path]:
        """Find all Obsidian vaults under the search path."""
        logger.info(f"Searching for vaults in: {self.search_path}")
        vaults = []
        
        try:
            # Start with the search path
            paths_to_search = [(self.search_path, 0)]
            
            while paths_to_search:
                current_path, current_depth = paths_to_search.pop(0)
                
                # Skip if we've exceeded max depth
                if current_depth > self.max_depth:
                    continue
                
                try:
                    # Check if current path is a vault
                    obsidian_dir = current_path / ".obsidian"
                    if obsidian_dir.is_dir() and self.is_valid_vault(current_path):
                        logger.debug(f"Found vault: {current_path}")
                        vaults.append(current_path)
                    
                    # Add subdirectories to search queue if within depth limit
                    if current_depth < self.max_depth:
                        for path in current_path.iterdir():
                            # Skip hidden directories and files
                            if path.name.startswith('.'):
                                continue
                            if path.is_dir():
                                paths_to_search.append((path, current_depth + 1))
                except PermissionError:
                    logger.debug(f"Permission denied: {current_path}")
                except Exception as e:
                    logger.debug(f"Error searching directory {current_path}: {str(e)}")
                    
        except Exception as e:
            logger.debug(f"Error searching directory: {str(e)}")
        
        logger.info(f"Found {len(vaults)} vaults")
        return vaults

    @staticmethod
    def get_vault_info(vault_path: Path) -> dict:
        """Get information about a vault.

        Args:
            vault_path: Path to the vault

        Returns:
            dict: Dictionary containing vault information
        """
        try:
            vault = VaultManager(vault_path)
            settings_files = len(list(vault.settings_dir.glob("*.json")))
            plugins_dir = vault.settings_dir / "plugins"
            plugin_count = len(list(plugins_dir.glob("*"))) if plugins_dir.is_dir() else 0

            return {
                "name": vault_path.name,
                "path": str(vault_path),
                "settings_count": settings_files,
                "plugin_count": plugin_count
            }
        except Exception as e:
            logger.debug(f"Error getting vault info for {vault_path}: {e}")
            return {
                "name": vault_path.name,
                "path": str(vault_path),
                "settings_count": 0,
                "plugin_count": 0
            } 