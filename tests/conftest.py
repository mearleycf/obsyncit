"""Configuration and fixtures for pytest."""

import shutil
import os
import stat
from pathlib import Path
import pytest
from typing import Generator


def handle_remove_readonly(func, path, exc):
    """Handle permission errors during directory removal."""
    if func in (os.rmdir, os.remove, os.unlink) and exc[1].errno == 13:  # errno.EACCES = 13
        try:
            # Change file/directory permissions
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            func(path)  # Try again
        except:
            # If still can't delete, make directory writable
            os.chmod(path, stat.S_IWRITE)
            func(path)
    else:
        raise


def pytest_configure(config):
    """Configure pytest."""
    # Set markers
    config.addinivalue_line('markers', 'slow: marks test as slow running')
    config.addinivalue_line('markers', 'vault: tests involving vault operations')


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up temporary files and directories after each test."""
    yield
    # Clean up temp directories
    temp_base = Path('/private/var/folders/lq/b2s6mqss6t1c2mttbrtwxvz40000gn/T/pytest-of-mikeearley')
    if temp_base.exists():
        for temp_dir in temp_base.glob('garbage-*'):
            try:
                if temp_dir.is_dir():
                    # Remove read-only files and directories
                    shutil.rmtree(temp_dir, ignore_errors=True, onerror=handle_remove_readonly)
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
    
    # Enhanced cleanup with error handling
    if test_dir.exists():
        try:
            # Ensure write permissions and remove directory
            shutil.rmtree(test_dir, ignore_errors=True, onerror=handle_remove_readonly)
        except Exception:
            # If cleanup fails, don't fail the test
            pass