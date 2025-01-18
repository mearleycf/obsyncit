"""Test utilities and helper functions."""

import json
import shutil
from pathlib import Path
import pytest
from typing import Optional, Dict, Any

from obsyncit.vault import VaultManager
from obsyncit.schemas import Config


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
    """Create a test vault with optional settings.

    Args:
        path: Path where the vault should be created
        settings: Optional dictionary of settings files and their content
        create_default_settings: Whether to create default settings files

    Returns:
        Path to the created vault
    """
    # Create vault directory and settings dir
    settings_dir = path / ".obsidian"
    settings_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default settings
    default_settings = {
        "app.json": {"test": True},
        "appearance.json": {"theme": "default", "cssTheme": ""},
        "core-plugins.json": ["file-explorer", "global-search", "switcher", "graph"],
        "workspace.json": {"main": {"mode": "source", "source": False}},
        "hotkeys.json": {},
        "core-plugin-settings.json": {}
    }
    
    if create_default_settings:
        for name, content in default_settings.items():
            file_path = settings_dir / name
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2)
    
    # Add custom settings
    if settings:
        for name, content in settings.items():
            file_path = settings_dir / name
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2)
    
    # Create standard Obsidian subdirectories if using default settings
    if create_default_settings:
        # Create plugins directory
        plugins_dir = settings_dir / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        
        # Create themes directory
        themes_dir = settings_dir / "themes"
        themes_dir.mkdir(exist_ok=True)
        
        # Create snippets directory
        snippets_dir = settings_dir / "snippets"
        snippets_dir.mkdir(exist_ok=True)
    
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
            "community_plugins": True,
            "themes": True,
            "snippets": True
        }
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


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