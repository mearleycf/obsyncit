"""Test configuration and fixtures."""
import os
import shutil
from pathlib import Path
import pytest
from loguru import logger


def force_rmtree(path: Path):
    """Force remove a directory tree, handling permission issues."""
    try:
        if not path.exists():
            return
        for child in path.glob('**/*'):
            try:
                if child.is_file():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
            except (PermissionError, OSError):
                continue
        try:
            path.rmdir()
        except (PermissionError, OSError):
            pass
    except Exception as e:
        logger.warning(f"Failed to remove {path}: {e}")


def pytest_sessionstart(session):
    """Setup test environment."""
    # Clear any leftover test directories from previous runs
    tmp_root = Path('/private/var/folders/lq/b2s6mqss6t1c2mttbrtwxvz40000gn/T/pytest-of-mikeearley')
    if tmp_root.exists():
        for item in tmp_root.iterdir():
            force_rmtree(item)


def pytest_sessionfinish(session, exitstatus):
    """Cleanup after all tests complete."""
    tmp_root = Path('/private/var/folders/lq/b2s6mqss6t1c2mttbrtwxvz40000gn/T/pytest-of-mikeearley')
    if tmp_root.exists():
        for item in tmp_root.iterdir():
            force_rmtree(item)
        try:
            tmp_root.rmdir()
        except (PermissionError, OSError):
            pass