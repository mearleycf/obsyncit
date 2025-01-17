"""
ObsyncIt Error Classes.

This module defines exception classes used throughout the ObsyncIt package.
Each error type provides specific context and information about where and
why an error occurred.
"""

from pathlib import Path
from typing import List, Optional, Union, Callable, Any
from functools import wraps
import json
from loguru import logger


class ObsyncError(Exception):
    """Base error class for ObsyncIt."""

    def __init__(self, message: str, details: Optional[str] = None):
        """Initialize the error."""
        self.message = message
        self.details = details
        super().__init__(self.full_message)

    @property
    def full_message(self) -> str:
        """Get the complete error message with details."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message

    def __reduce__(self):
        """Support pickling of error instances."""
        return (self.__class__, (self.message, self.details))


class VaultError(ObsyncError):
    """Error related to Obsidian vault operations."""

    def __init__(self, message: str, vault_path: Union[str, Path], details: Optional[str] = None):
        """Initialize the error."""
        self.vault_path = Path(vault_path)
        self._details = details
        error_details = [f"Vault: {self.vault_path}"]
        if details:
            error_details.append(details)
        super().__init__(message, "\n".join(error_details))

    def __reduce__(self):
        """Support pickling of error instances."""
        return (self.__class__, (self.message, self.vault_path, self._details))


class ConfigError(ObsyncError):
    """Error related to configuration loading or validation."""

    def __init__(self, message: str, file_path: Optional[Union[str, Path]] = None, details: Optional[str] = None):
        """Initialize the error."""
        self.file_path = Path(file_path) if file_path else None
        self._details = details
        error_parts = []
        if self.file_path:
            error_parts.append(f"Config: {self.file_path}")
        if details:
            error_parts.append(details)
        super().__init__(message, "\n".join(error_parts) if error_parts else None)

    def __reduce__(self):
        """Support pickling of error instances."""
        return (self.__class__, (self.message, self.file_path, self._details))


class ValidationError(ObsyncError):
    """Error related to JSON schema validation."""

    def __init__(self, message: str, file_path: Union[str, Path], errors: List[str]):
        """Initialize the error."""
        self.file_path = Path(file_path)
        self.schema_errors = errors
        error_parts = [f"File: {self.file_path}"]
        error_parts.extend([f"- {error}" for error in errors])
        super().__init__(message, "\n".join(error_parts))

    def __reduce__(self):
        """Support pickling of error instances."""
        return (self.__class__, (self.message, self.file_path, self.schema_errors))


class BackupError(ObsyncError):
    """Error related to backup operations."""

    def __init__(self, message: str, backup_path: Union[str, Path], details: Optional[str] = None):
        """Initialize the error."""
        self.backup_path = Path(backup_path)
        self._details = details
        error_parts = [f"Backup: {self.backup_path}"]
        if details:
            error_parts.append(details)
        super().__init__(message, "\n".join(error_parts))

    def __reduce__(self):
        """Support pickling of error instances."""
        return (self.__class__, (self.message, self.backup_path, self._details))


class SyncError(ObsyncError):
    """Error related to sync operations."""

    def __init__(self, message: str, source: Optional[Union[str, Path]] = None, 
                 target: Optional[Union[str, Path]] = None, details: Optional[str] = None):
        """Initialize the error."""
        self.source = Path(source) if source else None
        self.target = Path(target) if target else None
        self._details = details
        error_parts = []
        if self.source:
            error_parts.append(f"Source: {self.source}")
        if self.target:
            error_parts.append(f"Target: {self.target}")
        if details:
            error_parts.append(details)
        super().__init__(message, "\n".join(error_parts) if error_parts else None)

    def __reduce__(self):
        """Support pickling of error instances."""
        return (self.__class__, (self.message, self.source, self.target, self._details))


def handle_file_operation_error(error: Exception, operation: str, path: Union[str, Path]) -> None:
    """Handle file operation errors."""
    path_str = str(path)
    if isinstance(error, PermissionError):
        logger.error(f"Permission denied {operation}")
        logger.debug(f"Path: {path_str}")
        raise ObsyncError(f"Permission denied {operation}", f"Path: {path_str}")
    elif isinstance(error, FileNotFoundError):
        logger.error("File not found")
        logger.debug(f"Path: {path_str}")
        raise ObsyncError(f"File not found", f"Path: {path_str}")
    else:
        logger.error(f"File operation failed: {operation}")
        logger.debug(f"Path: {path_str}")
        logger.debug(f"Error: {str(error)}")
        raise ObsyncError(f"File operation failed: {operation}", f"Path: {path_str}\nError: {str(error)}")


def handle_json_error(error: Union[json.JSONDecodeError, Exception], file_path: Path) -> None:
    """Handle JSON operation errors."""
    if isinstance(error, json.JSONDecodeError):
        # Get context around the error
        start = max(0, error.pos - 20)
        end = min(len(error.doc), error.pos + 20)
        context = error.doc[start:end]
        
        logger.error("Invalid JSON format")
        logger.debug(f"File: {file_path}")
        logger.debug(f"Line {error.lineno}, Column {error.colno}: {error.msg}")
        logger.debug(f"Context: {context}")
        
        error_details = f"Line {error.lineno}, Column {error.colno}: {error.msg}"
        raise ValidationError("Invalid JSON format", file_path, [error_details])
    else:
        logger.error(f"JSON operation failed")
        logger.debug(f"File: {file_path}")
        logger.debug(f"Error: {str(error)}")
        raise ValidationError("JSON operation failed", file_path, [str(error)])