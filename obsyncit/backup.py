"""
Backup management functionality for Obsidian settings.

This module provides backup creation, verification, and cleanup functionality
for Obsidian vault settings. It supports different backup strategies and
rotation policies to ensure safe settings synchronization.
"""

import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from loguru import logger
import uuid


class BackupManager:
    """Manages backups of Obsidian settings."""

    def __init__(self, vault_path: Path, settings_dir: str, backup_count: int, dry_run: bool = False):
        """
        Initialize the backup manager.
        
        Args:
            vault_path: Path to the Obsidian vault
            settings_dir: Name of the settings directory (e.g., '.obsidian')
            backup_count: Number of backups to retain
            dry_run: If True, only simulate operations
        """
        self.vault_path = Path(vault_path).resolve()
        self.settings_dir = settings_dir
        self.backup_count = backup_count
        self.dry_run = dry_run
        self.settings_path = self.vault_path / self.settings_dir

    def _generate_backup_name(self, timestamp: Optional[datetime] = None) -> str:
        """
        Generate a backup directory name with timestamp and UUID for uniqueness.
        
        Args:
            timestamp: Optional timestamp to use, defaults to current time
            
        Returns:
            str: Name of the backup directory
        """
        if timestamp is None:
            timestamp = datetime.now()
        unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity
        return f"{self.settings_dir}_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}_{unique_id}"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Hexadecimal hash of the file
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_directory_snapshot(self, dir_path: Path, max_depth: int = 5) -> Dict[str, str]:
        """
        Create a snapshot of directory contents with file hashes.
        
        Args:
            dir_path: Path to the directory
            max_depth: Maximum directory depth to traverse
            
        Returns:
            Dict[str, str]: Mapping of relative paths to file hashes
        """
        snapshot = {}
        try:
            for item in dir_path.rglob("*"):
                # Skip if we've exceeded max depth
                relative_depth = len(item.relative_to(dir_path).parts)
                if relative_depth > max_depth:
                    continue
                
                if item.is_file():
                    relative_path = str(item.relative_to(dir_path))
                    snapshot[relative_path] = self._calculate_file_hash(item)
        except Exception as e:
            logger.error(f"Error creating directory snapshot: {str(e)}")
        return snapshot

    def _verify_backup(self, backup_path: Path, max_depth: int = 5) -> bool:
        """
        Verify that a backup was created successfully using file hashing.

        Args:
            backup_path: Path to the backup directory
            max_depth: Maximum directory depth to traverse

        Returns:
            bool: True if backup is valid, False otherwise
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup directory does not exist: {backup_path}")
                return False

            # Create snapshots of original and backup
            original_snapshot = self._get_directory_snapshot(self.settings_path, max_depth)
            backup_snapshot = self._get_directory_snapshot(backup_path, max_depth)

            # Compare snapshots
            if original_snapshot != backup_snapshot:
                # Log specific differences for debugging
                missing_files = set(original_snapshot.keys()) - set(backup_snapshot.keys())
                modified_files = {k for k in original_snapshot.keys() & backup_snapshot.keys()
                                if original_snapshot[k] != backup_snapshot[k]}
                
                if missing_files:
                    logger.error(f"Missing files in backup: {missing_files}")
                if modified_files:
                    logger.error(f"Modified files in backup: {modified_files}")
                return False

            return True
        except OSError as e:
            logger.error(f"File system error while verifying backup: {str(e)}")
            return False
        except ValueError as e:
            logger.error(f"Path resolution error while verifying backup: {str(e)}")
            return False

    def list_backups(self) -> List[Path]:
        """
        List all existing backups, sorted by creation time.
        
        Returns:
            List[Path]: List of backup directory paths
        """
        backup_pattern = f"{self.settings_dir}_backup_*"
        backups = list(self.vault_path.glob(backup_pattern))
        return sorted(backups, key=lambda p: p.stat().st_ctime)

    def create_backup(self) -> Optional[Path]:
        """
        Create a new backup of the settings directory.

        Returns:
            Optional[Path]: Path to the created backup directory if successful, None otherwise
        """
        try:
            if not self.settings_path.exists():
                logger.error(f"Settings directory does not exist: {self.settings_path}")
                return None

            backup_dir = self.vault_path / self._generate_backup_name()

            if not self.dry_run:
                shutil.copytree(self.settings_path, backup_dir, dirs_exist_ok=True)
                if not self._verify_backup(backup_dir, max_depth=5):
                    logger.error("Backup verification failed")
                    try:
                        shutil.rmtree(backup_dir)
                    except Exception as e:
                        logger.error(f"Error cleaning up failed backup: {str(e)}")
                    return None

            logger.info(f"Created backup of settings at: {backup_dir}")
            return backup_dir

        except PermissionError as e:
            logger.error(f"Permission denied creating backup: {str(e)}")
            return None
        except OSError as e:
            logger.error(f"File system error creating backup: {str(e)}")
            return None
        except shutil.Error as e:
            logger.error(f"Copy error creating backup: {str(e)}")
            return None
        return None

    def cleanup_old_backups(self) -> None:
        """Clean up old backups, keeping only the specified number of most recent backups."""
        try:
            backups = self.list_backups()
            if len(backups) > self.backup_count:
                for backup in backups[:-self.backup_count]:
                    if not self.dry_run:
                        shutil.rmtree(backup)
                    logger.info(f"Removed old backup: {backup}")
        except PermissionError as e:
            logger.error(f"Permission denied cleaning up backups: {str(e)}")
        except OSError as e:
            logger.error(f"File system error cleaning up backups: {str(e)}")
        except shutil.Error as e:
            logger.error(f"Error removing backup directories: {str(e)}")

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """
        Restore settings from a backup.

        Args:
            backup_path: Optional specific backup to restore. If None, uses most recent.

        Returns:
            bool: True if restore was successful, False otherwise
        """
        try:
            if backup_path is None:
                backups = self.list_backups()
                if not backups:
                    logger.error("No backups found to restore")
                    return False
                backup_path = backups[-1]

            if not backup_path.exists():
                logger.error(f"Backup does not exist: {backup_path}")
                return False

            if not self._verify_backup(backup_path, max_depth=5):
                logger.error("Backup verification failed")
                return False

            if not self.dry_run:
                if self.settings_path.exists():
                    shutil.rmtree(self.settings_path)
                shutil.copytree(backup_path, self.settings_path, dirs_exist_ok=True)

            logger.success(f"Successfully restored settings from backup: {backup_path}")
            return True

        except PermissionError as e:
            logger.error(f"Permission denied restoring backup: {str(e)}")
            return False
        except OSError as e:
            logger.error(f"File system error restoring backup: {str(e)}")
            return False
        except shutil.Error as e:
            logger.error(f"Copy error restoring backup: {str(e)}")
            return False
        return False