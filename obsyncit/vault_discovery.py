"""
Vault Discovery - Find Obsidian vaults in the filesystem.

This module provides functionality for discovering Obsidian vaults
in the filesystem by searching directories for .obsidian folders.
It handles various edge cases like inaccessible directories, invalid
vault structures, and permission issues gracefully.

Features:
    - Recursive vault discovery with configurable depth
    - Validation of vault structure and settings
    - Collection of vault metadata (settings, plugins)
    - Error handling for filesystem access issues
    - Performance optimization by skipping hidden directories

Basic Example:
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
    ...     print(f"Found vault: {info.name}")
    ...     print(f"  Settings: {info.settings_count}")
    ...     print(f"  Plugins: {info.plugin_count}")

Advanced Example:
    >>> # Custom search with error handling
    >>> discoverer = VaultDiscovery(max_depth=5)
    >>> try:
    ...     vaults = discoverer.find_vaults()
    ...     for vault in vaults:
    ...         if discoverer.is_valid_vault(vault):
    ...             info = discoverer.get_vault_info(vault)
    ...             if info.plugin_count > 0:
    ...                 print(f"Found vault with plugins: {info.name}")
    ... except PermissionError:
    ...     print("Some directories were not accessible")
    ... except Exception as e:
    ...     print(f"Error during vault discovery: {e}")

Error Handling:
    The module handles various error conditions:
    - PermissionError: When directories can't be accessed
    - FileNotFoundError: When paths don't exist
    - OSError: For other filesystem-related errors
    - ValueError: For invalid parameters (e.g., negative max_depth)

Performance Notes:
    - Hidden directories (starting with '.') are skipped
    - Directory traversal stops at max_depth
    - Basic validation is performed before detailed info gathering
    - File operations use Path objects for efficiency
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from loguru import logger

from obsyncit.vault import VaultManager


@dataclass
class VaultInfo:
    """Information about an Obsidian vault.
    
    This class holds metadata about a discovered vault, including its
    name, path, and counts of settings files and plugins. It provides
    a structured way to access vault information without needing to
    repeatedly scan the filesystem.
    
    Attributes:
        name: The name of the vault (directory name)
        path: Full path to the vault directory
        settings_count: Number of JSON settings files in .obsidian directory
        plugin_count: Number of installed plugins

    Example:
        >>> info = VaultInfo(
        ...     name="My Vault",
        ...     path="/path/to/vault",
        ...     settings_count=5,
        ...     plugin_count=10
        ... )
        >>> print(f"{info.name} has {info.plugin_count} plugins")
        My Vault has 10 plugins
    """
    name: str
    path: str
    settings_count: int
    plugin_count: int


class VaultDiscovery:
    """Discovers Obsidian vaults in the filesystem.
    
    This class provides methods to recursively search directories for Obsidian
    vaults and gather information about them. It handles various edge cases
    and errors gracefully, making it suitable for use in both automated
    scripts and interactive applications.

    The discovery process follows these steps:
    1. Start at the search path (defaults to user's home)
    2. Recursively traverse directories up to max_depth
    3. Skip hidden directories for better performance
    4. Validate potential vaults by checking .obsidian structure
    5. Gather metadata about valid vaults

    Attributes:
        search_path: The root path to start searching from (defaults to user's home directory)
        max_depth: Maximum directory depth to search (default: 3)

    Example:
        >>> # Basic usage
        >>> discoverer = VaultDiscovery()
        >>> vaults = discoverer.find_vaults()
        >>> 
        >>> # Custom search path and depth
        >>> discoverer = VaultDiscovery(
        ...     search_path=Path("~/Documents"),
        ...     max_depth=5
        ... )
        >>> vaults = discoverer.find_vaults()
        >>> 
        >>> # Error handling
        >>> try:
        ...     info = discoverer.get_vault_info(vaults[0])
        ... except Exception as e:
        ...     print(f"Could not access vault: {e}")
    """

    def __init__(self, search_path: Optional[Path] = None, max_depth: int = 3) -> None:
        """Initialize the vault discovery.

        This method sets up the vault discovery with a search path and maximum
        search depth. If no search path is provided, it defaults to the user's
        home directory. The search path is resolved to its absolute path to
        ensure consistent behavior.

        Args:
            search_path: Root path to start searching from (defaults to user's home directory)
            max_depth: Maximum directory depth to search (default: 3)

        Raises:
            ValueError: If max_depth is less than 0
            OSError: If the search path cannot be resolved

        Example:
            >>> # Default initialization
            >>> discoverer = VaultDiscovery()
            >>> 
            >>> # Custom path and depth
            >>> discoverer = VaultDiscovery(
            ...     search_path=Path("~/Documents"),
            ...     max_depth=5
            ... )
        """
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        
        # Use home directory as default if no search path provided
        self.search_path = Path(search_path or Path.home()).resolve()
        self.max_depth = max_depth

    def _iter_directories(self, root: Path, current_depth: int) -> Iterator[Tuple[Path, int]]:
        """Iterate through directories up to max_depth.
        
        This is an internal method that performs the recursive directory
        traversal. It yields each directory along with its depth in the
        tree, skipping hidden directories for better performance.

        The method handles various filesystem errors gracefully:
        - PermissionError: Skips directories we can't access
        - FileNotFoundError: Handles race conditions where dirs are deleted
        - OSError: Handles other filesystem-related errors
        
        Args:
            root: Directory to start iteration from
            current_depth: Current depth in the directory tree

        Yields:
            Tuple of (directory_path, depth)
            
        Note:
            - Skips hidden directories (starting with .) for better performance
            - Silently skips directories that can't be accessed
            - Stops traversal at max_depth
            - Uses Path.iterdir() for efficient directory listing

        Example:
            >>> discoverer = VaultDiscovery(max_depth=2)
            >>> root = Path("~/Documents")
            >>> for path, depth in discoverer._iter_directories(root, 0):
            ...     print(f"Found directory at depth {depth}: {path.name}")
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
        
        This method verifies that a given path contains a valid Obsidian
        vault structure. A valid vault must have a .obsidian directory
        containing at least one JSON settings file.

        The method performs these checks:
        1. Path exists and is a directory
        2. Contains a .obsidian subdirectory
        3. .obsidian contains at least one .json file
        
        Args:
            path: Path to check for vault validity

        Returns:
            True if the path contains a valid Obsidian vault
            
        Note:
            - Handles filesystem errors gracefully
            - Only checks structure, not content validity
            - Returns False for any error condition
            - Uses Path.glob() for efficient file matching

        Example:
            >>> discoverer = VaultDiscovery()
            >>> path = Path("~/Documents/MyVault")
            >>> if discoverer.is_valid_vault(path):
            ...     print(f"Found valid vault at: {path}")
            ... else:
            ...     print(f"Not a valid vault: {path}")
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
        
        This method performs a recursive search starting from the configured
        search path, identifying all valid Obsidian vaults up to the maximum
        depth. It handles various error conditions gracefully and provides
        detailed logging of the discovery process.

        The search process:
        1. Check if the search path itself is a vault
        2. Recursively traverse directories up to max_depth
        3. Skip hidden directories for better performance
        4. Validate each potential vault
        5. Log discovery progress and results

        Returns:
            List of paths to valid Obsidian vaults

        Note:
            - Handles filesystem errors gracefully
            - Logs progress and results
            - Skips inaccessible directories
            - Returns empty list if no vaults found

        Example:
            >>> # Basic vault discovery
            >>> discoverer = VaultDiscovery(Path("~/Documents"))
            >>> vaults = discoverer.find_vaults()
            >>> print(f"Found {len(vaults)} vaults")
            >>> 
            >>> # With error handling
            >>> try:
            ...     vaults = discoverer.find_vaults()
            ...     for vault in vaults:
            ...         print(f"Found vault: {vault.name}")
            ... except Exception as e:
            ...     print(f"Error during discovery: {e}")
        """
        logger.info(f"Searching for vaults in: {self.search_path}")
        vaults: List[Path] = []
        
        # Check if the search path itself is a vault
        if self.is_valid_vault(self.search_path):
            logger.debug(f"Found vault at search path: {self.search_path}")
            vaults.append(self.search_path)
        
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

        This method gathers metadata about a vault, including its name,
        settings files, and installed plugins. It uses VaultManager to
        access the vault structure and handles various error conditions
        gracefully.

        The method collects:
        1. Vault name (directory name)
        2. Full path to the vault
        3. Count of JSON settings files
        4. Count of installed plugins

        Args:
            vault_path: Path to the vault

        Returns:
            VaultInfo containing metadata about the vault
            
        Note:
            - Returns basic info even if vault can't be fully accessed
            - Uses VaultManager for consistent vault handling
            - Handles filesystem errors gracefully
            - Efficient file counting using Path.glob()

        Example:
            >>> discoverer = VaultDiscovery()
            >>> path = Path("~/Documents/MyVault")
            >>> try:
            ...     info = discoverer.get_vault_info(path)
            ...     print(f"Vault: {info.name}")
            ...     print(f"Settings: {info.settings_count}")
            ...     print(f"Plugins: {info.plugin_count}")
            ... except Exception as e:
            ...     print(f"Error accessing vault: {e}")
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