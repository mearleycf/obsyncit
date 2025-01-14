"""
Sync Manager - Core synchronization functionality.

This module provides the core functionality for syncing settings between Obsidian vaults.
"""

import shutil
from pathlib import Path
from typing import List, Optional, Set

from loguru import logger

from obsyncit.backup import BackupManager
from obsyncit.errors import (
    BackupError,
    SyncError,
    ValidationError,
    handle_file_operation_error
)
from obsyncit.schemas import Config
from obsyncit.vault import VaultManager


class SyncManager:
    """Manages the synchronization of settings between Obsidian vaults."""

    def __init__(
        self,
        source_vault: str,
        target_vault: str,
        config: Config,
        dry_run: bool = False
    ) -> None:
        """Initialize the sync manager.

        Args:
            source_vault: Path to the source vault
            target_vault: Path to the target vault
            config: Configuration object
            dry_run: Whether to simulate operations without making changes
        """
        self.source = VaultManager(source_vault)
        self.target = VaultManager(target_vault)
        self.config = config
        self.dry_run = dry_run
        self.backup_mgr = BackupManager(
            self.target.vault_path,
            config.backup.backup_dir,
            config.backup.max_backups
        )

    def sync_settings(self, items: Optional[List[str]] = None) -> bool:
        """Sync settings from source to target vault.

        Args:
            items: Optional list of specific settings to sync

        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            # Validate source vault
            if not self.source.validate_vault():
                raise SyncError(
                    "Invalid source vault",
                    f"Path: {self.source.vault_path}"
                )

            # Validate target vault
            if not self.target.validate_vault():
                raise SyncError(
                    "Invalid target vault",
                    f"Path: {self.target.vault_path}"
                )

            # Create backup before syncing
            if not self.dry_run and not self.backup_mgr.create_backup():
                raise BackupError(
                    "Failed to create backup",
                    f"Target vault: {self.target.vault_path}"
                )

            # Determine what to sync
            sync_items = self._get_sync_items(items)
            if not sync_items:
                logger.warning("No items to sync")
                return True

            # Sync each item
            success = True
            for item in sync_items:
                try:
                    self._sync_item(item)
                except Exception as e:
                    logger.error(f"Failed to sync {item}: {str(e)}")
                    success = False

            return success

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            logger.debug("", exc_info=True)
            return False

    def _get_sync_items(self, items: Optional[List[str]] = None) -> Set[str]:
        """Get the list of items to sync based on config and user input.

        Args:
            items: Optional list of specific items to sync

        Returns:
            Set[str]: Set of items to sync
        """
        # Start with configured items
        sync_items = set()

        # Add core settings if enabled
        if self.config.sync.core_settings:
            sync_items.add("app.json")
            sync_items.add("appearance.json")
            sync_items.add("hotkeys.json")

        # Add core plugins if enabled
        if self.config.sync.core_plugins:
            sync_items.add("core-plugins.json")

        # Add community plugins if enabled
        if self.config.sync.community_plugins:
            sync_items.add("community-plugins.json")

        # Add snippets if enabled
        if self.config.sync.snippets:
            sync_items.add("snippets")

        # Add themes if enabled
        if self.config.sync.themes:
            sync_items.add("themes")

        # Override with user-specified items if provided
        if items:
            sync_items = {item for item in items if item in sync_items}

        return sync_items

    def _sync_item(self, item: str) -> None:
        """Sync a specific settings item from source to target.

        Args:
            item: Name of the item to sync
        """
        source_path = self.source.vault_path / ".obsidian" / item
        target_path = self.target.vault_path / ".obsidian" / item

        if not source_path.exists():
            logger.warning(f"Source item does not exist: {item}")
            return

        # Handle directories (themes, snippets)
        if source_path.is_dir():
            self._sync_directory(source_path, target_path, item)
        else:
            self._sync_file(source_path, target_path, item)

    def _sync_directory(
        self,
        source_path: Path,
        target_path: Path,
        item: str
    ) -> None:
        """Sync a directory of settings (themes, snippets).

        Args:
            source_path: Path to source directory
            target_path: Path to target directory
            item: Name of the directory being synced
        """
        try:
            if self.dry_run:
                logger.info(f"Would sync directory: {item}")
                return

            # Remove existing directory if it exists
            if target_path.exists():
                shutil.rmtree(target_path)

            # Copy directory
            shutil.copytree(source_path, target_path)
            logger.info(f"Synced directory: {item}")

        except Exception as e:
            handle_file_operation_error(e, "syncing directory", target_path)
            raise SyncError(
                f"Failed to sync directory: {item}",
                str(e)
            ) from e

    def _sync_file(self, source_path: Path, target_path: Path, item: str) -> None:
        """Sync a settings file.

        Args:
            source_path: Path to source file
            target_path: Path to target file
            item: Name of the file being synced
        """
        try:
            if self.dry_run:
                logger.info(f"Would sync file: {item}")
                return

            # Validate source file
            if not self.source.validate_json_file(source_path):
                raise ValidationError(
                    f"Invalid source settings file: {item}",
                    f"Path: {source_path}"
                )

            # Copy file
            shutil.copy2(source_path, target_path)

            # Validate target file
            if not self.target.validate_json_file(target_path):
                # Restore from backup if validation fails
                if not self.backup_mgr.restore_backup(item):
                    raise BackupError(
                        "Failed to restore file from backup",
                        f"File: {item}"
                    )
                raise ValidationError(
                    f"Invalid target settings file after sync: {item}",
                    f"Path: {target_path}"
                )

            logger.info(f"Synced file: {item}")

        except Exception as e:
            handle_file_operation_error(e, "syncing file", target_path)
            raise SyncError(
                f"Failed to sync file: {item}",
                str(e)
            ) from e

    def list_backups(self) -> List[str]:
        """List available backups for the target vault.

        Returns:
            List[str]: List of backup paths
        """
        return self.backup_mgr.list_backups()

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """Restore settings from a backup.

        Args:
            backup_path: Optional specific backup to restore from

        Returns:
            bool: True if restore was successful
        """
        try:
            if self.dry_run:
                logger.info("Would restore from backup")
                return True

            return self.backup_mgr.restore_backup(backup_path)

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            logger.debug("", exc_info=True)
            return False
