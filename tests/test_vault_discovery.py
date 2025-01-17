"""Tests for vault discovery functionality."""

import json
from pathlib import Path
import pytest
from obsyncit.vault_discovery import VaultDiscovery


@pytest.fixture
def sample_vault(tmp_path):
    """Create a sample vault for testing."""
    vault = tmp_path / "test_vault"
    settings = vault / ".obsidian"
    settings.mkdir(parents=True)
    
    # Create sample settings files
    app_json = {"promptDelete": False}
    (settings / "app.json").write_text(json.dumps(app_json))
    
    # Create plugins directory
    plugins = settings / "plugins"
    plugins.mkdir()
    (plugins / "plugin1").mkdir()
    (plugins / "plugin2").mkdir()
    
    return vault


@pytest.fixture
def nested_vault(tmp_path):
    """Create a nested vault for testing depth search."""
    base = tmp_path / "nested"
    base.mkdir()
    vault = base / "dir1" / "dir2" / "vault"
    settings = vault / ".obsidian"
    settings.mkdir(parents=True)
    (settings / "app.json").write_text("{}")
    return vault


@pytest.fixture
def multiple_vaults(tmp_path):
    """Create multiple vaults for testing."""
    # Create root vault
    root_vault = tmp_path / "root_vault"
    (root_vault / ".obsidian").mkdir(parents=True)
    (root_vault / ".obsidian" / "app.json").write_text("{}")
    
    # Create nested vault
    nested = tmp_path / "dir" / "nested_vault"
    (nested / ".obsidian").mkdir(parents=True)
    (nested / ".obsidian" / "app.json").write_text("{}")
    
    # Create sibling vault
    sibling = tmp_path / "dir" / "sibling_vault"
    (sibling / ".obsidian").mkdir(parents=True)
    (sibling / ".obsidian" / "app.json").write_text("{}")
    
    return tmp_path


def restore_permissions(path: Path):
    """Recursively restore permissions on a path and its contents."""
    if path.is_file():
        path.chmod(0o644)
    else:
        path.chmod(0o755)
        for item in path.iterdir():
            restore_permissions(item)


@pytest.fixture
def locked_vault(tmp_path):
    """Create a vault with no permissions."""
    vault = tmp_path / "locked_vault"
    settings = vault / ".obsidian"
    settings.mkdir(parents=True)
    vault.chmod(0o000)
    return vault


def test_find_single_vault(sample_vault):
    """Test finding a single vault."""
    discovery = VaultDiscovery(sample_vault.parent)
    vaults = discovery.find_vaults()
    
    assert len(vaults) == 1
    assert vaults[0] == sample_vault


def test_find_nested_vault(nested_vault):
    """Test finding a deeply nested vault."""
    # Test with sufficient depth
    discovery = VaultDiscovery(nested_vault.parent.parent.parent, max_depth=3)
    vaults = discovery.find_vaults()
    assert len(vaults) == 1
    assert vaults[0] == nested_vault
    
    # Test with insufficient depth
    discovery = VaultDiscovery(nested_vault.parent.parent.parent, max_depth=1)
    vaults = discovery.find_vaults()
    assert len(vaults) == 0


def test_find_multiple_vaults(multiple_vaults):
    """Test finding multiple vaults."""
    discovery = VaultDiscovery(multiple_vaults)
    vaults = discovery.find_vaults()
    
    assert len(vaults) == 3
    vault_names = {v.name for v in vaults}
    assert "root_vault" in vault_names
    assert "nested_vault" in vault_names
    assert "sibling_vault" in vault_names


def test_get_vault_info(sample_vault):
    """Test getting vault information."""
    info = VaultDiscovery.get_vault_info(sample_vault)
    
    assert info.name == "test_vault"


def test_invalid_vault(tmp_path):
    """Test handling invalid vault directories."""
    # Create a directory that looks like a vault but isn't
    fake_vault = tmp_path / "fake_vault"
    fake_vault.mkdir()
    # Create .obsidian directory but no settings
    obsidian_dir = fake_vault / ".obsidian"
    obsidian_dir.mkdir()

    # Create a valid vault for comparison
    valid_vault = tmp_path / "valid_vault"
    valid_vault.mkdir()
    valid_obsidian = valid_vault / ".obsidian"
    valid_obsidian.mkdir()
    # Add some settings files to make it valid
    (valid_obsidian / "app.json").write_text("{}")
    (valid_obsidian / "appearance.json").write_text("{}")

    discovery = VaultDiscovery(tmp_path)
    vaults = discovery.find_vaults()

    # Should only find the valid vault
    assert len(vaults) == 1
    assert vaults[0] == valid_vault

    # Verify vault info
    info = discovery.get_vault_info(valid_vault)
    assert info.settings_count == 2


def test_permission_error(locked_vault):
    """Test handling permission errors."""
    discovery = VaultDiscovery(locked_vault.parent)
    vaults = discovery.find_vaults()
    assert len(vaults) == 0


def test_get_vault_info_invalid_vault(tmp_path):
    """Test getting info for invalid vault."""
    info = VaultDiscovery.get_vault_info(tmp_path)
    
    assert info.name == tmp_path.name


def test_ignore_hidden_directories(multiple_vaults):
    """Test that hidden directories are ignored."""
    # Create a hidden directory with a vault
    hidden = multiple_vaults / ".hidden" / "vault"
    (hidden / ".obsidian").mkdir(parents=True)
    (hidden / ".obsidian" / "app.json").write_text("{}")
    
    discovery = VaultDiscovery(multiple_vaults)
    vaults = discovery.find_vaults()
    
    # Hidden vault should not be found
    assert not any(v.name == "vault" for v in vaults) 