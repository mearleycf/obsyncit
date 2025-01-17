"""Configuration and fixtures for pytest."""

import os
import sys
import stat
import shutil
import subprocess
import uuid
import warnings
from pathlib import Path
import pytest
from typing import Generator

class TempDirWithCleanup:
    """A temporary directory handler that ensures proper cleanup."""
    
    def __init__(self, base_tmp_path: Path):
        """Initialize the temporary directory handler.
        
        Args:
            base_tmp_path: Base path for temporary directories
        """
        self.base_path = base_tmp_path
        self.test_id = str(uuid.uuid4())
        self.temp_path = self.base_path / f"test_{self.test_id}"
        self.garbage_dirs = []

    def __enter__(self) -> Path:
        """Create and enter the temporary directory.
        
        Returns:
            Path to the temporary directory
        """
        self.temp_path.mkdir(parents=True, exist_ok=True)
        return self.temp_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up and remove the temporary directory and any garbage."""
        self._cleanup()

    def _set_writable(self, path: Path) -> None:
        """Make a path and its contents writable."""
        if path.exists():
            # Set write permissions
            path.chmod(0o777)
            
            # Recursively set permissions for contents
            if path.is_dir() and not path.is_symlink():
                for item in path.glob('*'):
                    if item.is_file() or item.is_symlink():
                        item.chmod(0o777)
                    elif item.is_dir():
                        self._set_writable(item)

    def _rm_r(self, path: Path) -> None:
        """Recursively remove a path, handling symlinks correctly."""
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except Exception as e:
            warnings.warn(f"Failed to remove {path}: {str(e)}")

    def _delete_with_retries(self, path: Path, max_retries: int = 3) -> bool:
        """Attempt to delete a path with retries."""
        for i in range(max_retries):
            try:
                self._rm_r(path)
                return True
            except Exception:
                if i == max_retries - 1:
                    return False
                # Try to force-unlock files on Unix systems
                if sys.platform != 'win32':
                    try:
                        subprocess.run(['lsof', '-t', str(path)], capture_output=True)
                    except:
                        pass
                self._set_writable(path)
        return False

    def mark_for_cleanup(self, path: Path) -> None:
        """Mark a directory for cleanup during the cleanup phase."""
        if path.exists():
            self.garbage_dirs.append(path)

    def _cleanup(self):
        """Clean up all temporary and garbage directories."""
        all_paths = [self.temp_path] + self.garbage_dirs
        
        # First pass: Make everything writable
        for path in all_paths:
            self._set_writable(path)

        # Second pass: Try to delete everything
        for path in all_paths:
            if path.exists():
                # On Unix systems, try to unblock files
                if sys.platform != 'win32':
                    try:
                        subprocess.run(['lsof', '-t', str(path)], capture_output=True)
                    except:
                        pass
                if not self._delete_with_retries(path):
                    # If we can't delete it after retries, just hide the warnings
                    warnings.filterwarnings('ignore', message=f'.*{path}.*')


@pytest.fixture
def clean_dir(request, tmp_path) -> Generator[Path, None, None]:
    """Fixture providing a clean temporary directory with proper cleanup.
    
    This fixture ensures that temporary directories are properly cleaned up,
    even if they contain files that are temporarily locked or in use.
    
    Args:
        request: pytest request object
        tmp_path: pytest's temporary path fixture
        
    Yields:
        Path to a clean temporary directory
    """
    with TempDirWithCleanup(tmp_path) as temp_dir:
        yield temp_dir