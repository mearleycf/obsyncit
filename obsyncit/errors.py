"""Error Handling for ObsyncIt.

This module provides a comprehensive error handling system with custom
exceptions and error handlers. It includes:

1. Custom Exceptions
   - Base exception class for all ObsyncIt errors
   - Specific exceptions for different error types
   - Detailed error context and messages

2. Error Handlers
   - Standardized error handling functions
   - Consistent error reporting
   - Detailed error context

3. Error Categories
   - Validation errors (invalid settings, JSON, etc.)
   - Sync errors (file operations, permissions, etc.)
   - Backup errors (creation, restoration, etc.)

Example Usage:
    >>> from obsyncit.errors import ObsyncError, ValidationError
    >>> 
    >>> try:
    ...     # Some operation that might fail
    ...     validate_settings(data)
    ... except ValidationError as e:
    ...     print(f"Validation failed: {e}")
    ...     print(f"Context: {e.context}")
    ... except ObsyncError as e:
    ...     print(f"Operation failed: {e}")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Union, NoReturn
from typing_extensions import TypeAlias

from loguru import logger

# Type aliases
ErrorContext: TypeAlias = Union[str, Path]
"""Type for error context information"""

class ObsyncError(Exception):
    """Base exception class for all ObsyncIt errors.
    
    This is the parent class for all custom exceptions in ObsyncIt.
    It provides consistent error handling and context information.
    
    Attributes:
        message: Human-readable error description
        context: Additional context about the error
        details: List of detailed error information
    
    Example:
        >>> try:
        ...     raise ObsyncError("Operation failed", "context")
        ... except ObsyncError as e:
        ...     print(f"{e.message}: {e.context}")
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        details: Optional[List[str]] = None
    ) -> None:
        """Initialize the base error.
        
        Args:
            message: Human-readable error description
            context: Additional context about the error
            details: List of detailed error information
        """
        self.message = message
        self.context = context
        self.details = details or []
        super().__init__(self.message)

    def __str__(self) -> str:
        """Get string representation of the error.
        
        Returns:
            Formatted error message with context
        """
        if self.context:
            return f"{self.message} [{self.context}]"
        return self.message


class ValidationError(ObsyncError):
    """Exception raised for validation errors.
    
    This exception is raised when validation fails for settings,
    configuration files, or other validated content.
    
    Attributes:
        file_path: Path to the file that failed validation
        errors: List of validation error messages
    
    Example:
        >>> try:
        ...     validate_config("config.json")
        ... except ValidationError as e:
        ...     print(f"Validation failed: {e.errors}")
    """
    
    def __init__(
        self,
        message: str,
        file_path: Path,
        errors: List[str]
    ) -> None:
        """Initialize validation error.
        
        Args:
            message: Human-readable error description
            file_path: Path to the file that failed validation
            errors: List of validation error messages
        """
        super().__init__(message, str(file_path), errors)
        self.file_path = file_path
        self.errors = errors


class SyncError(ObsyncError):
    """Exception raised for synchronization errors.
    
    This exception is raised when sync operations fail between
    source and target vaults.
    
    Attributes:
        source: Source vault path
        target: Target vault path
        details: List of sync error details
    
    Example:
        >>> try:
        ...     sync_vaults(source, target)
        ... except SyncError as e:
        ...     print(f"Sync failed: {e.source} -> {e.target}")
    """
    
    def __init__(
        self,
        message: str,
        source: Optional[Path] = None,
        target: Optional[Path] = None,
        details: Optional[List[str]] = None
    ) -> None:
        """Initialize sync error.
        
        Args:
            message: Human-readable error description
            source: Source vault path
            target: Target vault path
            details: List of sync error details
        """
        context = f"{source} -> {target}" if source and target else None
        super().__init__(message, context, details)
        self.source = source
        self.target = target


class BackupError(ObsyncError):
    """Exception raised for backup operation errors.
    
    This exception is raised when backup creation or restoration
    operations fail.
    
    Attributes:
        vault_path: Path to the vault being backed up/restored
        backup_path: Path to the backup file/directory
    
    Example:
        >>> try:
        ...     create_backup(vault_path)
        ... except BackupError as e:
        ...     print(f"Backup failed: {e.vault_path}")
    """
    
    def __init__(
        self,
        message: str,
        vault_path: Optional[Path] = None,
        backup_path: Optional[Path] = None,
        details: Optional[List[str]] = None
    ) -> None:
        """Initialize backup error.
        
        Args:
            message: Human-readable error description
            vault_path: Path to the vault being backed up/restored
            backup_path: Path to the backup file/directory
            details: List of backup error details
        """
        context = str(vault_path) if vault_path else None
        super().__init__(message, context, details)
        self.vault_path = vault_path
        self.backup_path = backup_path


class VaultError(ObsyncError):
    """Exception raised for vault-related errors.
    
    This exception is raised when operations on an Obsidian vault
    fail, such as validation or settings access.
    
    Attributes:
        vault_path: Path to the problematic vault
    
    Example:
        >>> try:
        ...     validate_vault(path)
        ... except VaultError as e:
        ...     print(f"Invalid vault: {e.vault_path}")
    """
    
    def __init__(
        self,
        message: str,
        vault_path: Path,
        details: Optional[List[str]] = None
    ) -> None:
        """Initialize vault error.
        
        Args:
            message: Human-readable error description
            vault_path: Path to the problematic vault
            details: List of vault error details
        """
        super().__init__(message, str(vault_path), details)
        self.vault_path = vault_path


def handle_file_operation_error(
    error: Exception,
    operation: str,
    path: Union[str, Path]
) -> NoReturn:
    """Handle file operation errors consistently.
    
    This function provides standardized handling of file operation
    errors, including permission issues, missing files, etc. It logs
    the error with appropriate context and raises an ObsyncError.
    
    Args:
        error: The caught file operation exception
        operation: Description of the operation being performed
        path: Path to the file/directory involved
    
    Raises:
        ObsyncError: Always raised with formatted error message
    
    Example:
        >>> try:
        ...     with open("config.json", "r") as f:
        ...         data = json.load(f)
        ... except Exception as e:
        ...     handle_file_operation_error(
        ...         e,
        ...         "reading configuration",
        ...         "config.json"
        ...     )
    
    Note:
        This function never returns as it always raises an exception.
        The NoReturn type hint indicates this behavior.
    """
    logger.error(f"File operation error while {operation}: {error}")
    logger.debug("", exc_info=True)
    raise ObsyncError(
        f"Failed while {operation}",
        str(path),
        [str(error)]
    )


def handle_json_error(
    error: Union[json.JSONDecodeError, Exception],
    file_path: Path
) -> NoReturn:
    """Handle JSON parsing and validation errors consistently.
    
    This function provides standardized handling of JSON-related errors,
    including syntax errors, decoding issues, and schema validation
    failures. It logs the error with appropriate context and raises
    a ValidationError.
    
    Args:
        error: The caught JSON error (JSONDecodeError or other exception)
        file_path: Path to the JSON file being processed
    
    Raises:
        ValidationError: Always raised with formatted error message
    
    Example:
        >>> try:
        ...     with open("settings.json", "r") as f:
        ...         settings = json.load(f)
        ... except json.JSONDecodeError as e:
        ...     handle_json_error(e, Path("settings.json"))
        ... except Exception as e:
        ...     handle_json_error(e, Path("settings.json"))
    
    Note:
        This function never returns as it always raises an exception.
        The NoReturn type hint indicates this behavior.
        
        For JSONDecodeError, it includes line and column information
        in the error message to help locate syntax errors.
    """
    if isinstance(error, json.JSONDecodeError):
        logger.error(
            f"JSON decode error in {file_path}: {error}"
        )
        logger.debug(
            f"Error at line {error.lineno}, column {error.colno}",
            exc_info=True
        )
        raise ValidationError(
            "Invalid JSON format",
            file_path,
            [f"Line {error.lineno}, column {error.colno}: {error.msg}"]
        )
    else:
        logger.error(f"JSON validation error in {file_path}: {error}")
        logger.debug("", exc_info=True)
        raise ValidationError(
            "JSON validation failed",
            file_path,
            [str(error)]
        )