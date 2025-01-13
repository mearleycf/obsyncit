#!/usr/bin/env python3

import os
import shutil
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime

class ObsidianSettingsSync:
    """Handles syncing of Obsidian settings between vaults."""
    
    SETTINGS_DIR = ".obsidian"
    CORE_SETTINGS_FILES = [
        "appearance.json",
        "app.json",
        "core-plugins.json",
        "community-plugins.json",
        "hotkeys.json"
    ]
    SETTINGS_DIRS = [
        "plugins",
        "themes",
        "snippets"
    ]

    def __init__(self, source_vault: str, target_vault: str, dry_run: bool = False):
        """Initialize with source and target vault paths."""
        self.source_vault = Path(source_vault).expanduser().resolve()
        self.target_vault = Path(target_vault).expanduser().resolve()
        self.dry_run = dry_run
        self.setup_logging()

    def setup_logging(self):
        """Configure logging for the sync process."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def validate_paths(self) -> bool:
        """Validate that source and target paths exist and are Obsidian vaults."""
        try:
            if not self.source_vault.exists():
                self.logger.error(f"Source vault does not exist: {self.source_vault}")
                return False
            
            if not self.target_vault.exists():
                self.logger.error(f"Target vault does not exist: {self.target_vault}")
                return False
            
            source_settings = self.source_vault / self.SETTINGS_DIR
            if not source_settings.exists():
                self.logger.error(f"Source vault has no .obsidian directory: {source_settings}")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error validating paths: {str(e)}")
            return False

    def validate_json_file(self, file_path: Path) -> bool:
        """Validate that a file contains valid JSON."""
        try:
            if not file_path.exists():
                return True  # Skip validation for non-existent files
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {str(e)}")
            return False

    def backup_target_settings(self) -> Optional[Path]:
        """Create a backup of target vault settings."""
        try:
            target_settings = self.target_vault / self.SETTINGS_DIR
            if target_settings.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = target_settings.parent / f"{self.SETTINGS_DIR}_backup_{timestamp}"
                if not self.dry_run:
                    shutil.copytree(target_settings, backup_dir, dirs_exist_ok=True)
                self.logger.info(f"Created backup of target settings at: {backup_dir}")
                return backup_dir
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
        return None

    def cleanup_old_backups(self, keep_latest: int = 5):
        """Clean up old backups, keeping only the specified number of latest backups."""
        try:
            backup_pattern = f"{self.SETTINGS_DIR}_backup_*"
            backups = sorted(self.target_vault.glob(backup_pattern))
            if len(backups) > keep_latest:
                for backup in backups[:-keep_latest]:
                    if not self.dry_run:
                        shutil.rmtree(backup)
                    self.logger.info(f"Removed old backup: {backup}")
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {str(e)}")

    def sync_settings(self, selected_items: Optional[List[str]] = None) -> bool:
        """
        Synchronize settings from source to target vault.
        
        Args:
            selected_items: Optional list of specific settings to sync (files or directories)
        """
        try:
            if not self.validate_paths():
                return False

            # Create backup
            backup_path = self.backup_target_settings()
            
            source_settings = self.source_vault / self.SETTINGS_DIR
            target_settings = self.target_vault / self.SETTINGS_DIR

            # Create target .obsidian directory if it doesn't exist
            if not self.dry_run:
                target_settings.mkdir(exist_ok=True)

            # Determine what to sync
            files_to_sync = [f for f in self.CORE_SETTINGS_FILES 
                           if not selected_items or f in selected_items]
            dirs_to_sync = [d for d in self.SETTINGS_DIRS 
                          if not selected_items or d in selected_items]

            # Sync core settings files
            for settings_file in files_to_sync:
                source_file = source_settings / settings_file
                target_file = target_settings / settings_file
                
                if source_file.exists():
                    if not self.validate_json_file(source_file):
                        continue
                        
                    if not self.dry_run:
                        shutil.copy2(source_file, target_file)
                    self.logger.info(f"Synced settings file: {settings_file}")

            # Sync settings directories
            for dir_name in dirs_to_sync:
                source_dir = source_settings / dir_name
                target_dir = target_settings / dir_name
                
                if source_dir.exists():
                    if not self.dry_run:
                        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                    self.logger.info(f"Synced directory: {dir_name}")

            # Cleanup old backups
            self.cleanup_old_backups()

            self.logger.info("Settings sync completed successfully!")
            if backup_path:
                self.logger.info(f"Backup of original settings available at: {backup_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during sync: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Sync Obsidian settings between vaults")
    parser.add_argument("source_vault", help="Path to source vault")
    parser.add_argument("target_vault", help="Path to target vault")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes")
    parser.add_argument("--items", nargs="+", help="Specific settings to sync (files or directories)")
    
    args = parser.parse_args()
    
    syncer = ObsidianSettingsSync(args.source_vault, args.target_vault, args.dry_run)
    syncer.sync_settings(args.items)

if __name__ == "__main__":
    main()
