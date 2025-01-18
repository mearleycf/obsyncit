"""
Vault Discovery - Find Obsidian vaults in the filesystem.

This module provides functionality for discovering Obsidian vaults
in the filesystem by searching directories for .obsidian folders.

Example:
    >>> from pathlib import Path
    >>> from obsyncit.vault_discovery import VaultDiscovery
    >>> 
    >>> # Create a vault discoverer with max depth of 3
    >>> discoverer = VaultDiscovery(Path("~/Documents"), max_depth=3)
    >>> 
    >>> # Find all vaults in the directory
    >>> vaults = discoverer.find_vaults()
    >>> 
    >>> # Get information about each vault
    >>> for vault_path in vaults:
    ...     info = discoverer.get_vault_info(vault_path)
    ...     print(f"Found vault: {info['name']} with {info['plugin_count']} plugins")

Typical usage example:
    The VaultDiscovery class is typically used to locate Obsidian vaults before
    performing sync operations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from loguru import logger

from obsyncit.vault import VaultManager


@dataclass
class VaultInfo:
    """Information about an Obsidian vault.
    
    Attributes:
        name: The name of the vault (directory name)
        path: Full path to the vault directory
        settings_count: Number of JSON settings files in .obsidian directory
        plugin_count: Number of installed plugins
    """
    name: str
    path: str
    settings_count: int
    plugin_count: int


class VaultDiscovery:
    """Discovers Obsidian vaults in the filesystem.
    
    This class provides methods to recursively search directories for Obsidian
    vaults and gather information about them.

    Attributes:
        search_path: The root path to start searching from
        max_depth: Maximum directory depth to search (default: 3)
    """

    def __init__(self, search_path: Path, max_depth: int = 3) -> None:
        """Initialize the vault discovery.

        Args:
            search_path: Root path to start searching from
            max_depth: Maximum directory depth to search (default: 3)

        Raises:
            ValueError: If max_depth is less than 0
        """
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        
        self.search_path = Path(search_path).resolve()
        self.max_depth = max_depth

    def _iter_directories(self, root: Path, current_depth: int) -> Iterator[Tuple[Path, int]]:
        """Iterate through directories up to max_depth.
        
        Args:
            root: Directory to start iteration from
            current_depth: Current depth in the directory tree

        Yields:
            Tuple of (directory_path, depth)
        """
        if current_depth > self.max_depth:
            return

        try:
            for path in root.iterdir():
                if path.is_dir() and not path.name.startswith('.'):
                    yield (path, current_depth)
                    yield from self._iter_directories(path, current_depth + 1)
        except Exception:
            # Skip directories we can't access
            return

    def is_valid_vault(self, path: Path) -> bool:
        """Check if a path is a valid Obsidian vault.
        
        A valid vault must have a .obsidian directory with at least one settings file.
        
        Args:
            path: Path to check for vault validity

        Returns:
            True if the path contains a valid Obsidian vault
        """
        try:
            obsidian_dir = path / ".obsidian"
            if not obsidian_dir.exists():
                return False
            
            # Check for at least one settings file
            settings_files = list(obsidian_dir.glob("*.json"))
            return len(settings_files) > 0
        except Exception:
            return False

    def find_vaults(self) -> List[Path]:
        """Find all Obsidian vaults under the search path.
        
        This method recursively searches directories up to max_depth,
        identifying valid Obsidian vaults.

        Returns:
            List of paths to valid Obsidian vaults

        Example:
            >>> discoverer = VaultDiscovery(Path("~/Documents"))
            >>> vaults = discoverer.find_vaults()
            >>> print(f"Found {len(vaults)} vaults")
        """
        logger.info(f"Searching for vaults in: {self.search_path}")
        vaults: List[Path] = []
        
        # Search all directories
        for path, depth in self._iter_directories(self.search_path, 0):
            if self.is_valid_vault(path):
                logger.debug(f"Found vault: {path}")
                vaults.append(path)
        
        logger.info(f"Found {len(vaults)} vaults")
        return vaults

    @staticmethod
    def get_vault_info(vault_path: Path) -> VaultInfo:
        """Get information about a vault.

        Args:
            vault_path: Path to the vault

        Returns:
            VaultInfo containing metadata about the vault
        """
        try:
            vault = VaultManager(vault_path)
            settings_files = len(list(vault.settings_dir.glob("*.json")))
            plugins_dir = vault.settings_dir / "plugins"
            plugin_count = len(list(plugins_dir.glob("*"))) if plugins_dir.exists() else 0

            return VaultInfo(
                name=vault_path.name,
                path=str(vault_path),
                settings_count=settings_files,
                plugin_count=plugin_count
            )
        except Exception:
            # Return basic info if we can't access the vault
            return VaultInfo(
                name=vault_path.name,
                path=str(vault_path),
                settings_count=0,
                plugin_count=0
            )