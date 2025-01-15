"""
Sync Manager - Core synchronization functionality.

This module provides the core functionality for syncing settings between Obsidian vaults.
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional, Set, Union

from loguru import logger

from obsyncit.backup import BackupManager
from obsyncit.errors import (
    BackupError,
    SyncError,
    ValidationError,
    ObsyncError,
    handle_file_operation_error
)
from obsyncit.schemas import Config
from obsyncit.vault import VaultManager


class SyncManager:
    """Manages the synchronization of settings between Obsidian vaults."""

    def __init__(
        self,
        source_vault: str | Path,
        target_vault: str | Path,
        config: Config
    ) -> None:
        """Initialize the sync manager.

        Args:
            source_vault: Path to the source vault
            target_vault: Path to the target vault
            config: Configuration object
        """
        self.source = VaultManager(source_vault)
        self.target = VaultManager(target_vault)
        self.config = config
        self.backup_mgr = BackupManager(
            self.target.vault_path,
            config.backup.backup_dir,
            config.backup.max_backups
        )

    def sync_settings(self, items: Optional[List[str]] = None) -> bool:
        """Sync settings from source to target vault.

        Args:
            items: Optional list of specific items to sync. If None, syncs all items.

        Returns:
            bool: True if sync was successful, or if ignore_errors is True and at least one item synced

        Raises:
            SyncError: If there is an error during sync
        """
        try:
            # Validate vaults
            if not self.source.validate_vault():
                raise SyncError("Invalid source vault", source=self.source.vault_path, target=self.target.vault_path)
            if not self.target.validate_vault():
                raise SyncError("Invalid target vault", source=self.source.vault_path, target=self.target.vault_path)

            # Create backup of target settings if not in dry run mode
            if not self.config.sync.dry_run:
                try:
                    self.backup_mgr.create_backup()
                except BackupError as e:
                    if not self.config.sync.ignore_errors:
                        raise
                    logger.warning(f"Backup failed but continuing: {str(e)}")

            # Get list of items to sync
            if items is None:
                items = self._get_sync_items()
            elif not items:
                logger.warning("No items specified for sync")
                return True

            # Create target settings directory if it doesn't exist
            if not self.config.sync.dry_run:
                self.target.settings_dir.mkdir(exist_ok=True)

            # Sync each item
            success = True
            any_success = False
            for item in items:
                try:
                    self._sync_item(item)
                    any_success = True
                except (SyncError, ValidationError) as e:
                    if not self.config.sync.ignore_errors:
                        raise
                    logger.warning(f"Failed to sync {item}: {str(e)}")
                    success = False

            # Return True if all items synced successfully, or if ignore_errors is True and at least one item synced
            return success if not self.config.sync.ignore_errors else any_success

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            logger.debug("", exc_info=True)
            if isinstance(e, (SyncError, ValidationError, BackupError)):
                raise
            raise SyncError(str(e), source=self.source.vault_path, target=self.target.vault_path) from e

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
            for item in ["app.json", "appearance.json", "hotkeys.json"]:
                if (self.source.settings_dir / item).exists():
                    sync_items.add(item)

        # Add core plugins if enabled
        if self.config.sync.core_plugins:
            if (self.source.settings_dir / "core-plugins.json").exists():
                sync_items.add("core-plugins.json")

        # Add community plugins if enabled
        if self.config.sync.community_plugins:
            if (self.source.settings_dir / "community-plugins.json").exists():
                sync_items.add("community-plugins.json")

        # Add snippets if enabled
        if self.config.sync.snippets:
            if (self.source.settings_dir / "snippets").exists():
                sync_items.add("snippets")

        # Add themes if enabled
        if self.config.sync.themes:
            if (self.source.settings_dir / "themes").exists():
                sync_items.add("themes")

        # Override with user-specified items if provided
        if items:
            sync_items = {item for item in items if item in sync_items}

        return sync_items

    def validate_json_file(self, file_path: Path, required_fields: Optional[List[str]] = None) -> None:
        """Validate a JSON file.

        Args:
            file_path: Path to the JSON file to validate
            required_fields: Optional list of fields that must be present in the JSON

        Raises:
            ObsyncError: If the file doesn't exist or can't be read
            ValidationError: If the JSON is invalid or missing required fields
        """
        try:
            if not file_path.exists():
                raise ObsyncError("File not found", str(file_path))

            try:
                with open(file_path) as f:
                    data = json.load(f)
            except PermissionError:
                raise ObsyncError("Permission denied", str(file_path))
            except json.JSONDecodeError as e:
                raise ValidationError("Invalid JSON", file_path, [str(e)])

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValidationError(
                        "Schema validation failed",
                        file_path,
                        [f"Missing required fields: {', '.join(missing_fields)}"]
                    )

        except (ObsyncError, ValidationError):
            raise
        except Exception as e:
            raise ObsyncError(f"Failed to validate JSON file: {str(e)}", str(file_path)) from e

    def _sync_item(self, item: str) -> None:
        """Sync a specific settings item from source to target.

        Args:
            item: Name of the item to sync

        Raises:
            SyncError: If there is an error during sync
            ValidationError: If JSON validation fails
        """
        source_path = self.source.settings_dir / item
        target_path = self.target.settings_dir / item

        if not source_path.exists():
            raise SyncError(f"Source item does not exist: {item}", source=self.source.vault_path, target=self.target.vault_path)

        try:
            # Validate JSON files
            if item.endswith('.json'):
                with open(source_path) as f:
                    try:
                        json.load(f)
                    except json.JSONDecodeError as e:
                        raise ValidationError(f"Invalid JSON in {item}", file_path=source_path) from e

            # Copy file or directory
            if not self.config.sync.dry_run:
                if source_path.is_file():
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Synced file: {item}")
                else:
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    logger.info(f"Synced directory: {item}")
            else:
                logger.info(f"Would sync: {item} (dry run)")

        except Exception as e:
            if isinstance(e, (SyncError, ValidationError)):
                raise
            raise SyncError(f"Failed to sync {item}: {str(e)}", source=self.source.vault_path, target=self.target.vault_path) from e

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
