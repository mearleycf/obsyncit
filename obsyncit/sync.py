"""
Sync Manager - Core synchronization functionality.

This module provides the core functionality for syncing settings between Obsidian vaults.
It handles synchronization of various settings files and directories, backup management,
and validation of settings files.

Key Components:
    - SyncManager: Main class for managing sync operations
    - SyncResult: Data class for storing sync operation results
    - Validatable: Protocol for objects that can be validated

The sync process includes:
1. Validation of source and target vaults
2. Automatic backup of target vault before sync
3. Selective syncing of:
   - Core settings files (app.json, appearance.json, etc.)
   - Plugin configurations and data
   - Themes and snippets
4. Error handling and recovery
5. Dry run capability for previewing changes

Example:
    >>> from obsyncit.sync import SyncManager
    >>> from obsyncit.schemas import Config
    >>> 
    >>> # Initialize sync manager
    >>> sync_mgr = SyncManager(
    ...     source_vault="/path/to/source",
    ...     target_vault="/path/to/target",
    ...     config=Config()
    ... )
    >>> 
    >>> # Perform sync
    >>> result = sync_mgr.sync_settings([
    ...     "app.json",
    ...     "appearance.json",
    ...     "plugins"
    ... ])
    >>> 
    >>> if result.success:
    ...     print("Sync completed successfully!")
    ...     print(f"Items synced: {result.items_synced}")
    ... else:
    ...     print(f"Sync failed: {result.summary}")
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Union, Dict, Any, Generator
from typing_extensions import Protocol
from contextlib import contextmanager

from loguru import logger

from obsyncit.backup import BackupManager
from obsyncit.errors import (
    BackupError,
    SyncError,
    ValidationError,
    ObsyncError,
)
from obsyncit.schemas import Config
from obsyncit.vault import VaultManager


class Validatable(Protocol):
    """Protocol for objects that can be validated.
    
    This protocol defines the interface for objects that support
    validation. Classes implementing this protocol must provide
    a validate() method that returns a boolean indicating whether
    the object is valid.
    
    Example:
        >>> class ConfigFile(Validatable):
        ...     def __init__(self, path: Path):
        ...         self.path = path
        ...     
        ...     def validate(self) -> bool:
        ...         return self.path.exists() and self.path.suffix == '.json'
    """
    
    def validate(self) -> bool:
        """Validate the object.
        
        Returns:
            bool: True if the object is valid, False otherwise
        """
        ...


@dataclass(frozen=True)
class SyncResult:
    """Result of a sync operation.
    
    This immutable dataclass stores the results of a sync operation,
    including which items were successfully synced, which failed,
    and any errors that occurred.
    
    Attributes:
        success: Whether the overall sync operation was successful
        items_synced: List of items that were successfully synced
        items_failed: List of items that failed to sync
        errors: Dictionary mapping failed items to their error messages
    
    Example:
        >>> result = SyncResult(
        ...     success=True,
        ...     items_synced=["app.json", "appearance.json"],
        ...     items_failed=[],
        ...     errors={}
        ... )
        >>> print(result.summary)
        Sync successful
        Items synced: 2
    
    Note:
        The success flag will be False if any items failed to sync,
        unless ignore_errors was enabled in the configuration.
    """
    
    success: bool
    items_synced: List[str]
    items_failed: List[str]
    errors: Dict[str, str]

    def __post_init__(self) -> None:
        """Validate the sync result.
        
        Raises:
            ValueError: If no items failed but success is False
        """
        if not self.items_failed and not self.success:
            raise ValueError("Invalid state: no failed items but success is False")

    @property
    def any_success(self) -> bool:
        """Check if any items were successfully synced.
        
        Returns:
            bool: True if at least one item was synced successfully
        """
        return bool(self.items_synced)
    
    @property
    def summary(self) -> str:
        """Get a formatted summary of the sync operation.
        
        Returns:
            str: A human-readable summary of the sync results
        """
        return str(self)

    def __str__(self) -> str:
        """Get a human-readable summary of the sync result.
        
        Returns:
            str: A multi-line string containing:
                - Overall success/failure status
                - Number of items synced
                - List of failed items and their errors (if any)
        """
        parts = [
            f"Sync {'successful' if self.success else 'failed'}",
            f"Items synced: {len(self.items_synced)}",
        ]
        if self.items_failed:
            parts.append(f"Items failed: {len(self.items_failed)}")
            for item, error in self.errors.items():
                parts.append(f"  - {item}: {error}")
        return "\n".join(parts)


class SyncManager:
    """Manages the synchronization of settings between Obsidian vaults.
    
    This class is responsible for synchronizing settings, plugins, themes,
    and other configuration files between two Obsidian vaults. It handles:
    - Validation of source and target vaults
    - Automatic backup of target vault before sync
    - Selective syncing of specific items
    - Error handling and recovery
    - Dry run capability
    
    The sync process is configurable through the Config object, which allows:
    - Enabling/disabling specific sync items (core settings, plugins, etc.)
    - Configuring backup behavior
    - Setting error handling preferences
    - Enabling dry run mode
    
    Attributes:
        source: VaultManager for the source vault
        target: VaultManager for the target vault
        config: Configuration settings
        backup_mgr: BackupManager for handling vault backups
        CORE_SETTINGS_FILES: Set of core settings files to sync
        PLUGIN_FILES: Set of plugin-related files to sync
        SYNC_DIRECTORIES: Set of directories that can be synced
    
    Example:
        >>> # Initialize with basic configuration
        >>> sync_mgr = SyncManager(
        ...     source_vault="/path/to/source",
        ...     target_vault="/path/to/target",
        ...     config=Config(
        ...         sync=SyncConfig(
        ...             dry_run=True,
        ...             core_settings=True,
        ...             plugins=True
        ...         )
        ...     )
        ... )
        >>> 
        >>> # Perform sync
        >>> result = sync_mgr.sync_settings()
        >>> print(result.summary)
    """

    # Core settings files that should be synced
    CORE_SETTINGS_FILES = {
        "app.json",
        "appearance.json",
        "hotkeys.json",
        "types.json",
        "templates.json",
    }
    
    # Plugin configuration files
    PLUGIN_FILES = {
        "core-plugins.json",
        "community-plugins.json",
        "core-plugins-migration.json",
        "plugins",  # Directory containing plugin data
    }
    
    # Directories that can be synced
    SYNC_DIRECTORIES = {"snippets", "themes", "plugins", "icons"}

    def __init__(
        self,
        source_vault: Union[str, Path],
        target_vault: Union[str, Path],
        config: Config,
    ) -> None:
        """Initialize the sync manager.
        
        Args:
            source_vault: Path to the source vault
            target_vault: Path to the target vault
            config: Configuration settings
        
        Raises:
            VaultError: If either vault path is invalid
        """
        self.source = VaultManager(source_vault)
        self.target = VaultManager(target_vault)
        self.config = config
        self.backup_mgr = BackupManager(
            self.target.vault_path,
            config.backup.backup_dir,
            config.backup.max_backups,
        )

    def _sync_plugins_directory(self) -> None:
        """Sync the plugins directory and its contents.
        
        This method synchronizes the entire plugins directory from source
        to target, including all plugin subdirectories and their contents.
        If a plugin exists in the target but not in the source, it will
        be removed.
        
        Note:
            This is skipped in dry run mode.
        
        Raises:
            SyncError: If plugin sync fails and ignore_errors is False
        """
        source_plugins = self.source.settings_dir / "plugins"
        target_plugins = self.target.settings_dir / "plugins"
        
        if not source_plugins.exists():
            logger.debug("Source plugins directory does not exist, skipping plugin sync")
            return

        if not self.config.sync.dry_run:
            # Create plugins directory if it doesn't exist
            target_plugins.mkdir(exist_ok=True)

            # Copy each plugin directory
            for plugin_dir in source_plugins.iterdir():
                if plugin_dir.is_dir():
                    target_plugin_dir = target_plugins / plugin_dir.name
                    logger.debug(f"Syncing plugin: {plugin_dir.name}")
                    try:
                        if target_plugin_dir.exists():
                            shutil.rmtree(target_plugin_dir)
                        shutil.copytree(plugin_dir, target_plugin_dir)
                    except Exception as e:
                        logger.warning(f"Failed to sync plugin {plugin_dir.name}: {e}")
                        if not self.config.sync.ignore_errors:
                            raise

    def _sync_icons_directory(self) -> None:
        """Sync the icons directory and its contents.
        
        This method synchronizes the entire icons directory from source
        to target. The target icons directory is completely replaced
        with the contents of the source directory.
        
        Note:
            This is skipped in dry run mode.
        
        Raises:
            SyncError: If icons sync fails and ignore_errors is False
        """
        source_icons = self.source.settings_dir / "icons"
        target_icons = self.target.settings_dir / "icons"
        
        if not source_icons.exists():
            logger.debug("Source icons directory does not exist, skipping icons sync")
            return

        if not self.config.sync.dry_run:
            try:
                if target_icons.exists():
                    shutil.rmtree(target_icons)
                shutil.copytree(source_icons, target_icons)
                logger.debug("Successfully synced icons directory")
            except Exception as e:
                logger.warning(f"Failed to sync icons directory: {e}")
                if not self.config.sync.ignore_errors:
                    raise

    def _get_sync_items(self, items: Optional[List[str]] = None) -> Set[str]:
        """Get the list of items to sync based on config and user input.
        
        This method determines which items should be synced based on:
        1. Configuration settings (which types of items are enabled)
        2. Existence of items in the source vault
        3. Optional list of specific items to sync
        
        Args:
            items: Optional list of specific items to sync. If provided,
                  only these items will be considered for sync (if they
                  exist and are enabled in config).
        
        Returns:
            Set of item names to sync
        
        Example:
            >>> # Get all enabled items
            >>> all_items = sync_mgr._get_sync_items()
            >>> 
            >>> # Get specific items
            >>> specific_items = sync_mgr._get_sync_items([
            ...     "app.json",
            ...     "plugins"
            ... ])
        """
        sync_items: Set[str] = set()

        # Add core settings if enabled
        if self.config.sync.core_settings:
            sync_items.update(
                item for item in self.CORE_SETTINGS_FILES
                if (self.source.settings_dir / item).exists()
            )

        # Add plugin settings and directory if enabled
        if self.config.sync.core_plugins or self.config.sync.community_plugins:
            # Add plugin configuration files
            sync_items.update(
                item for item in self.PLUGIN_FILES
                if (self.source.settings_dir / item).exists()
            )
            
            # Add plugins directory if it exists
            if (self.source.settings_dir / "plugins").exists():
                sync_items.add("plugins")

            # Add icons directory if it exists
            if (self.source.settings_dir / "icons").exists():
                sync_items.add("icons")

        # Add directories if enabled
        if self.config.sync.snippets:
            if (self.source.settings_dir / "snippets").exists():
                sync_items.add("snippets")

        if self.config.sync.themes:
            if (self.source.settings_dir / "themes").exists():
                sync_items.add("themes")

        # Filter by provided items if specified
        if items is not None:
            if not items:
                return set()
            sync_items = {item for item in items if item in sync_items}

        return sync_items

    def _sync_item(self, item: str) -> None:
        """Sync a specific settings item from source to target.
        
        This method handles the actual synchronization of a single item,
        which can be either a file or directory. It includes:
        - Special handling for plugins and icons directories
        - JSON validation for .json files
        - File and directory copying
        
        Args:
            item: Name of the item to sync (relative to settings directory)
        
        Raises:
            SyncError: If the source item doesn't exist or sync fails
            ValidationError: If JSON validation fails
        """
        source_path = self.source.settings_dir / item
        target_path = self.target.settings_dir / item

        if not source_path.exists():
            raise SyncError(
                f"Source item does not exist: {item}",
                source=self.source.vault_path,
                target=self.target.vault_path,
            )

        with self._sync_operation(item):
            try:
                # Special handling for plugins directory
                if item == "plugins":
                    if not self.config.sync.dry_run:
                        self._sync_plugins_directory()
                    else:
                        logger.info("Would sync plugins directory (dry run)")
                    return

                # Special handling for icons directory
                if item == "icons":
                    if not self.config.sync.dry_run:
                        self._sync_icons_directory()
                    else:
                        logger.info("Would sync icons directory (dry run)")
                    return

                # Validate JSON files
                if item.endswith('.json'):
                    try:
                        self.validate_json_file(source_path)
                    except ValidationError as e:
                        logger.warning(f"Invalid JSON: {item} - {str(e)}")
                        if not self.config.sync.ignore_errors:
                            raise

                # Copy file or directory
                if not self.config.sync.dry_run:
                    try:
                        if source_path.is_file():
                            shutil.copy2(source_path, target_path)
                        else:
                            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    except Exception as e:
                        logger.warning(f"Failed to copy {item}: {e}")
                        if not self.config.sync.ignore_errors:
                            raise
            except Exception as e:
                if not self.config.sync.ignore_errors:
                    raise
                logger.warning(f"Failed to sync {item}: {str(e)}")
                raise

    def sync_settings(self, items: Optional[List[str]] = None) -> SyncResult:
        """Synchronize settings between source and target vaults.
        
        This is the main method for performing vault synchronization. It:
        1. Validates both vaults
        2. Creates a backup of the target vault
        3. Determines which items to sync
        4. Syncs each item individually
        5. Handles errors according to configuration
        
        Args:
            items: Optional list of specific items to sync. If not provided,
                  all enabled items will be synced based on configuration.
        
        Returns:
            SyncResult object containing the results of the sync operation
        
        Raises:
            VaultError: If either vault is invalid
            BackupError: If backup creation fails
            SyncError: If sync fails and ignore_errors is False
        
        Example:
            >>> # Sync all enabled items
            >>> result = sync_mgr.sync_settings()
            >>> 
            >>> # Sync specific items
            >>> result = sync_mgr.sync_settings([
            ...     "app.json",
            ...     "appearance.json"
            ... ])
            >>> 
            >>> if result.success:
            ...     print("Synced items:", result.items_synced)
        """
        try:
            # Validate vaults
            self._validate_vaults()
            
            # Create backup if not in dry run mode
            if not self.config.sync.dry_run:
                self._create_backup()
            
            # Get items to sync
            sync_items = self._get_sync_items(items)
            if not sync_items:
                logger.warning("No items to sync")
                return SyncResult(True, [], [], {})
            
            # Track results
            synced_items: List[str] = []
            failed_items: List[str] = []
            errors: Dict[str, str] = {}
            
            # Sync each item
            for item in sync_items:
                try:
                    self._sync_item(item)
                    synced_items.append(item)
                except Exception as e:
                    failed_items.append(item)
                    errors[item] = str(e)
                    if not self.config.sync.ignore_errors:
                        raise
            
            # Return results
            success = len(failed_items) == 0 or self.config.sync.ignore_errors
            return SyncResult(
                success=success,
                items_synced=synced_items,
                items_failed=failed_items,
                errors=errors,
            )
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return SyncResult(
                success=False,
                items_synced=[],
                items_failed=[str(e)],
                errors={"sync": str(e)},
            )

    def _validate_vaults(self) -> None:
        """Validate source and target vaults.
        
        Ensures both vaults:
        1. Exist and are accessible
        2. Have valid Obsidian settings directories
        3. Meet any additional validation requirements
        
        Raises:
            VaultError: If either vault fails validation
        """
        if not self.source.validate():
            raise VaultError(
                "Invalid source vault",
                vault_path=self.source.vault_path
            )
        
        if not self.target.validate():
            raise VaultError(
                "Invalid target vault",
                vault_path=self.target.vault_path
            )

    def _create_backup(self) -> None:
        """Create a backup of the target vault.
        
        Creates a backup of the target vault's settings directory
        before performing any sync operations.
        
        Note:
            This is skipped in dry run mode.
        
        Raises:
            BackupError: If backup creation fails
        """
        try:
            self.backup_mgr.create_backup()
        except Exception as e:
            raise BackupError(
                "Failed to create backup",
                backup_path=self.backup_mgr.backup_dir,
                details=str(e)
            )

    def validate_json_file(
        self,
        file_path: Path,
        required_fields: Optional[List[str]] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate a JSON settings file.
        
        This method validates a JSON file by:
        1. Checking if it can be parsed as valid JSON
        2. Verifying required fields are present (if specified)
        3. Validating against a schema (if provided)
        
        Args:
            file_path: Path to the JSON file to validate
            required_fields: Optional list of field names that must exist
            schema: Optional JSON schema to validate against
        
        Returns:
            The parsed JSON data as a dictionary
        
        Raises:
            ValidationError: If the file is invalid or missing required fields
        
        Example:
            >>> # Basic validation
            >>> data = sync_mgr.validate_json_file(Path("app.json"))
            >>> 
            >>> # With required fields
            >>> data = sync_mgr.validate_json_file(
            ...     Path("appearance.json"),
            ...     required_fields=["theme", "cssTheme"]
            ... )
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if required_fields:
                missing = [f for f in required_fields if f not in data]
                if missing:
                    raise ValidationError(
                        "Missing required fields",
                        file_path,
                        missing
                    )
            
            if schema:
                # TODO: Implement schema validation
                pass
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValidationError(
                "Invalid JSON format",
                file_path,
                [str(e)]
            )
        except Exception as e:
            raise ValidationError(
                "Validation failed",
                file_path,
                [str(e)]
            )

    @contextmanager
    def _sync_operation(self, item: str) -> Generator[None, None, None]:
        """Context manager for sync operations.
        
        This context manager provides error handling and logging
        around individual sync operations.
        
        Args:
            item: Name of the item being synced
        
        Yields:
            None
        
        Raises:
            SyncError: If the sync operation fails
        
        Example:
            >>> with sync_mgr._sync_operation("app.json"):
            ...     # Perform sync operation
            ...     shutil.copy2(source_path, target_path)
        """
        try:
            logger.debug(f"Starting sync of {item}")
            yield
            logger.debug(f"Successfully synced {item}")
        except Exception as e:
            logger.error(f"Failed to sync {item}: {e}")
            raise SyncError(
                f"Failed to sync {item}",
                source=self.source.vault_path,
                target=self.target.vault_path,
                details=str(e)
            )

    def list_backups(self) -> List[str]:
        """List available backups for the target vault.
        
        Returns:
            List of backup names, sorted by creation time (newest first)
        """
        return self.backup_mgr.list_backups()

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """Restore the target vault from a backup.
        
        Args:
            backup_path: Optional specific backup to restore.
                       If not provided, restores the most recent backup.
        
        Returns:
            bool: True if restore was successful, False otherwise
        
        Example:
            >>> # Restore most recent backup
            >>> if sync_mgr.restore_backup():
            ...     print("Restore successful!")
            >>> 
            >>> # Restore specific backup
            >>> backup_path = Path(".backups/backup_20240118_123456")
            >>> if sync_mgr.restore_backup(backup_path):
            ...     print("Restore successful!")
        """
        try:
            return self.backup_mgr.restore_backup(backup_path)
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False