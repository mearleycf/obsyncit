"""Test utilities and helper functions."""

import json
import pytest
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from obsyncit.vault import VaultManager
from obsyncit.schemas import Config


def clean_directory(path: Path) -> None:
    """Recursively clean a directory, handling all edge cases."""
    if not path.exists():
        return

    # First, reset permissions to ensure we can delete everything
    for item in path.rglob('*'):
        try:
            item.chmod(0o777)
        except:
            pass  # Continue even if chmod fails

    # Then remove directories one by one
    try:
        shutil.rmtree(path)
    except:
        for sub in path.glob('*'):
            if sub.is_file():
                try:
                    sub.unlink()
                except:
                    pass
            else:
                try:
                    shutil.rmtree(sub)
                except:
                    pass


@pytest.fixture
def sample_vault(clean_dir) -> Path:
    """Create a sample vault for testing.

    Args:
        clean_dir: Clean directory fixture

    Returns:
        Path to the created vault
    """
    return create_test_vault(clean_dir / "sample_vault")


def create_test_vault(
    path: Path,
    settings: Optional[Dict[str, Any]] = None,
    create_default_settings: bool = True
) -> Path:
    """Create a test vault with configurable settings.
    
    This is a helper function that creates a test vault with the proper
    structure and sample settings files.
    
    Args:
        path: Path where to create the test vault
        settings: Optional settings to write to the vault
        create_default_settings: Whether to create default settings if none provided
        
    Returns:
        Path to the created vault
    """
    # Clean up any existing files
    if path.exists():
        clean_directory(path)
        
    # Create vault directory
    path.mkdir(parents=True, exist_ok=True)
    settings_dir = path / ".obsidian"
    settings_dir.mkdir(exist_ok=True)
    
    # Add default or provided settings
    if settings is None and create_default_settings:
        settings = {
            "app.json": {"test": True},
            "appearance.json": {"theme": "default"},
            "hotkeys.json": {"test": True},
            "core-plugins.json": {"enabled": []},
            "community-plugins.json": {"enabled": []}
        }
    
    if settings:
        for name, content in settings.items():
            file_path = settings_dir / name
            file_path.write_text(json.dumps(content))
    
    return path


def create_test_config(path: Path) -> None:
    """Create a test configuration file.
    
    Args:
        path: Path to the config file to create
    """
    config = {
        "logging": {
            "level": "DEBUG",
            "rotation": "1 day",
            "retention": "1 week",
            "compression": "zip"
        },
        "backup": {
            "max_backups": 5,
            "ignore_errors": True
        },
        "sync": {
            "dry_run": False,
            "ignore_errors": True,
            "core_settings": True,
            "core_plugins": True,
            "community_plugins": True
        }
    }
    
    path.write_text(json.dumps(config))


def create_vault_fixture(tmp_path: Path) -> VaultManager:
    """Create a test vault with a vault manager.
    
    Args:
        tmp_path: Temporary directory for tests
        
    Returns:
        VaultManager instance for the test vault
    """
    vault_path = tmp_path / "test_vault"
    create_test_vault(vault_path)
    return VaultManager(vault_path)


def delete_test_vaults(tmp_path: Path, *names: str) -> None:
    """Delete test vaults cleanly.
    
    Args:
        tmp_path: Temporary directory containing test vaults
        *names: Names of vaults to delete
    """
    for name in names:
        vault_path = tmp_path / name
        clean_directory(vault_path)
