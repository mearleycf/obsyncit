"""Configuration and fixtures for pytest."""

import shutil
import os
import stat
from pathlib import Path
import pytest
from typing import Generator
import time


def force_remove_dir(path: Path) -> None:
    """Force remove a directory and its contents."""
    if not path.exists():
        return

    # First pass: make everything writable
    for root, dirs, files in os.walk(str(path)):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                dir_path.chmod(stat.S_IRWXU)
            except:
                pass
        for file_name in files:
            file_path = Path(root) / file_name
            try:
                file_path.chmod(stat.S_IRWXU)
            except:
                pass

    # Second pass: actually remove everything
    for _ in range(3):  # Try up to 3 times
        try:
            shutil.rmtree(path)
            break
        except:
            time.sleep(0.1)  # Wait a bit before retrying


def pytest_configure(config):
    """Configure pytest."""
    # Set markers
    config.addinivalue_line('markers', 'slow: marks test as slow running')
    config.addinivalue_line('markers', 'vault: tests involving vault operations')


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up temporary files and directories after each test."""
    # Let the test run
    yield

    # Clean up temp directories
    temp_base = Path('/private/var/folders/lq/b2s6mqss6t1c2mttbrtwxvz40000gn/T/pytest-of-mikeearley')
    if temp_base.exists():
        for temp_dir in temp_base.glob('garbage-*'):
            if temp_dir.is_dir():
                force_remove_dir(temp_dir)
            elif temp_dir.is_file():
                try:
                    temp_dir.unlink()
                except:
                    pass


@pytest.fixture
def clean_dir(tmp_path) -> Generator[Path, None, None]:
    """Fixture providing a clean temporary directory.
    
    Args:
        tmp_path: pytest's temporary path fixture
        
    Yields:
        Path to a clean temporary directory
    """
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    
    if test_dir.exists():
        force_remove_dir(test_dir)


@pytest.fixture
def clean_test_dir(clean_dir: Path) -> Generator[Path, None, None]:
    """Fixture ensuring test directory is properly cleaned up.
    
    This is a more robust version of clean_dir that handles permission issues.
    
    Args:
        clean_dir: Base clean directory fixture
        
    Yields:
        Path to a clean test directory
    """
    yield clean_dir
    if clean_dir.exists():
        force_remove_dir(clean_dir)
