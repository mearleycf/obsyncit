"""ObsyncIt Error Classes and Error Handling Utilities.

This module defines the exception hierarchy and error handling utilities used throughout ObsyncIt.
It provides specific error types for different operations (vault, config, sync, etc.) and
includes decorators and helper functions for consistent error handling.

Typical usage:
    try:
        result = perform_operation()
    except VaultError as e:
        logger.error(e.full_message)
        # Handle vault-specific error
    except ConfigError as e:
        logger.error(e.full_message)
        # Handle configuration error

Error Hierarchy:
    ObsyncError (base)
    ├── VaultError
    ├── ConfigError
    ├── ValidationError
    ├── BackupError
    └── SyncError
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import (
    List, Optional, Union, Callable, Any, TypeVar, ParamSpec,
    cast, overload, NoReturn, Type
)

from loguru import logger


# Type variables for generic function signatures
T = TypeVar('T')
P = ParamSpec('P')
PathLike = Union[str, Path]


class ObsyncError(Exception):
    """Base error class for all ObsyncIt exceptions.
    
    This class serves as the root of the ObsyncIt exception hierarchy and provides
    common functionality for all derived error classes.
    
    Attributes:
        message: The primary error message
        details: Additional error details or context
    """

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        """Initialize the error with a message and optional details.
        
        Args:
            message: The primary error message
            details: Additional context or details about the error
        """
        self.message = message
        self.details = details
        super().__init__(self.full_message)

    @property
    def full_message(self) -> str:
        """Get the complete error message including details.
        
        Returns:
            The formatted error message with details if available
        """
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message

    def __reduce__(self) -> tuple[Type[ObsyncError], tuple[str, Optional[str]]]:
        """Support pickling of error instances.
        
        Returns:
            A tuple containing the class and arguments needed for reconstruction
        """
        return (self.__class__, (self.message, self.details))


class VaultError(ObsyncError):
    """Error specific to Obsidian vault operations.
    
    Used when operations involving vault access, validation, or modification fail.
    
    Attributes:
        vault_path: Path to the vault where the error occurred
        message: The error message
        details: Additional error context
    """

    def __init__(self, message: str, vault_path: PathLike, details: Optional[str] = None) -> None:
        """Initialize a vault error.
        
        Args:
            message: The error message
            vault_path: Path to the relevant vault
            details: Additional error context
        """
        self.vault_path = Path(vault_path)
        self._details = details
        error_details = [f"Vault: {self.vault_path}"]
        if details:
            error_details.append(details)
        super().__init__(message, "\n".join(error_details))

    def __reduce__(self) -> tuple[Type[VaultError], tuple[str, Path, Optional[str]]]:
        """Support pickling of VaultError instances."""
        return (self.__class__, (self.message, self.vault_path, self._details))


class ConfigError(ObsyncError):
    """Error related to configuration loading or validation.
    
    Used for issues with configuration files, settings, or validation failures.
    
    Attributes:
        file_path: Optional path to the configuration file
        message: The error message
        details: Additional error context
    """

    def __init__(
        self, 
        message: str, 
        file_path: Optional[PathLike] = None, 
        details: Optional[str] = None
    ) -> None:
        """Initialize a configuration error.
        
        Args:
            message: The error message
            file_path: Optional path to the relevant configuration file
            details: Additional error context
        """
        self.file_path = Path(file_path) if file_path else None
        self._details = details
        error_parts = []
        if self.file_path:
            error_parts.append(f"Config: {self.file_path}")
        if details:
            error_parts.append(details)
        super().__init__(message, "\n".join(error_parts) if error_parts else None)

    def __reduce__(self) -> tuple[Type[ConfigError], tuple[str, Optional[Path], Optional[str]]]:
        """Support pickling of ConfigError instances."""
        return (self.__class__, (self.message, self.file_path, self._details))


class ValidationError(ObsyncError):
    """Error related to JSON schema validation.
    
    Used when validation of JSON data against a schema fails.
    
    Attributes:
        file_path: Path to the file that failed validation
        schema_errors: List of specific validation errors
        message: The error message
    """

    def __init__(self, message: str, file_path: PathLike, errors: List[str]) -> None:
        """Initialize a validation error.
        
        Args:
            message: The error message
            file_path: Path to the file that failed validation
            errors: List of specific validation errors
        """
        self.file_path = Path(file_path)
        self.schema_errors = errors
        error_parts = [f"File: {self.file_path}"]
        error_parts.extend([f"- {error}" for error in errors])
        super().__init__(message, "\n".join(error_parts))

    def __reduce__(self) -> tuple[Type[ValidationError], tuple[str, Path, List[str]]]:
        """Support pickling of ValidationError instances."""
        return (self.__class__, (self.message, self.file_path, self.schema_errors))


class BackupError(ObsyncError):
    """Error related to backup operations.
    
    Used when backup creation, restoration, or management fails.
    
    Attributes:
        backup_path: Path to the backup location
        message: The error message
        details: Additional error context
    """

    def __init__(self, message: str, backup_path: PathLike, details: Optional[str] = None) -> None:
        """Initialize a backup error.
        
        Args:
            message: The error message
            backup_path: Path to the relevant backup
            details: Additional error context
        """
        self.backup_path = Path(backup_path)
        self._details = details
        error_parts = [f"Backup: {self.backup_path}"]
        if details:
            error_parts.append(details)
        super().__init__(message, "\n".join(error_parts))

    def __reduce__(self) -> tuple[Type[BackupError], tuple[str, Path, Optional[str]]]:
        """Support pickling of BackupError instances."""
        return (self.__class__, (self.message, self.backup_path, self._details))


class SyncError(ObsyncError):
    """Error related to sync operations.
    
    Used when synchronization between vaults fails.
    
    Attributes:
        source: Optional path to the source vault
        target: Optional path to the target vault
        message: The error message
        details: Additional error context
    """

    def __init__(
        self, 
        message: str, 
        source: Optional[PathLike] = None,
        target: Optional[PathLike] = None, 
        details: Optional[str] = None
    ) -> None:
        """Initialize a sync error.
        
        Args:
            message: The error message
            source: Optional path to the source vault
            target: Optional path to the target vault
            details: Additional error context
        """
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

    def __reduce__(self) -> tuple[Type[SyncError], tuple[str, Optional[Path], Optional[Path], Optional[str]]]:
        """Support pickling of SyncError instances."""
        return (self.__class__, (self.message, self.source, self.target, self._details))


def with_error_handling(error_class: Type[ObsyncError]) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for consistent error handling across functions.
    
    Args:
        error_class: The error class to use for wrapping exceptions
        
    Returns:
        A decorator function that wraps the target function with error handling
    
    Example:
        @with_error_handling(VaultError)
        def process_vault(path: Path) -> None:
            # Function implementation
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except ObsyncError:
                raise
            except Exception as e:
                logger.error(f"Operation failed: {func.__name__}")
                logger.debug(f"Error: {str(e)}")
                raise error_class(str(e))
        return wrapper
    return decorator


def handle_file_operation_error(error: Exception, operation: str, path: PathLike) -> NoReturn:
    """Handle file operation errors consistently.
    
    Args:
        error: The caught exception
        operation: Description of the attempted operation
        path: Path to the file that caused the error
        
    Raises:
        ObsyncError: Always raised with appropriate context
    """
    path_str = str(path)
    if isinstance(error, FileNotFoundError):
        logger.error("File not found")
        logger.debug(f"Path: {path_str}")
        raise ObsyncError("File not found", f"Path: {path_str}")
    else:
        logger.error(f"File operation failed: {operation}")
        logger.debug(f"Path: {path_str}")
        raise ObsyncError(f"File operation failed: {operation}", f"Path: {path_str}")


def handle_json_error(error: Union[json.JSONDecodeError, Exception], file_path: Path) -> NoReturn:
    """Handle JSON parsing and validation errors consistently.
    
    Args:
        error: The caught JSON-related exception
        file_path: Path to the JSON file that caused the error
        
    Raises:
        ValidationError: Always raised with appropriate context
    """
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
        logger.error("JSON operation failed")
        logger.debug(f"File: {file_path}")
        logger.debug(f"Error: {str(error)}")
        raise ValidationError("JSON operation failed", file_path, [str(error)])
