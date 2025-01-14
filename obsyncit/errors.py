"""
Error handling module for ObsyncIt.

This module provides custom exceptions and error handling utilities
to improve error reporting and recovery strategies.
"""

from pathlib import Path
from typing import Optional
from loguru import logger


class ObsyncError(Exception):
    """Base exception class for ObsyncIt errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        """
        Initialize the exception.
        
        Args:
            message: Main error message
            details: Optional detailed explanation or context
        """
        self.message = message
        self.details = details
        super().__init__(self.full_message)
    
    @property
    def full_message(self) -> str:
        """Get the full error message including details if available."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class VaultError(ObsyncError):
    """Raised for errors related to Obsidian vault operations."""
    
    def __init__(self, message: str, vault_path: Path, details: Optional[str] = None):
        """
        Initialize the vault error.
        
        Args:
            message: Main error message
            vault_path: Path to the vault where the error occurred
            details: Optional detailed explanation or context
        """
        self.vault_path = vault_path
        vault_context = f"Vault: {vault_path}"
        super().__init__(message, f"{vault_context}\n{details}" if details else vault_context)


class ConfigError(ObsyncError):
    """Raised for configuration-related errors."""
    pass


class ValidationError(ObsyncError):
    """Raised when validation fails for settings files."""
    
    def __init__(self, message: str, file_path: Path, schema_errors: Optional[list] = None):
        """
        Initialize the validation error.
        
        Args:
            message: Main error message
            file_path: Path to the file that failed validation
            schema_errors: Optional list of specific schema validation errors
        """
        details = [f"File: {file_path}"]
        if schema_errors:
            details.extend([f"- {err}" for err in schema_errors])
        super().__init__(message, "\n".join(details))


class BackupError(ObsyncError):
    """Raised for backup-related errors."""
    
    def __init__(self, message: str, backup_path: Optional[Path] = None, details: Optional[str] = None):
        """
        Initialize the backup error.
        
        Args:
            message: Main error message
            backup_path: Optional path to the backup involved in the error
            details: Optional detailed explanation or context
        """
        context = []
        if backup_path:
            context.append(f"Backup: {backup_path}")
        if details:
            context.append(details)
        super().__init__(message, "\n".join(context) if context else None)


class SyncError(ObsyncError):
    """Raised for synchronization-related errors."""
    
    def __init__(self, message: str, source: Optional[Path] = None, target: Optional[Path] = None, 
                 details: Optional[str] = None):
        """
        Initialize the sync error.
        
        Args:
            message: Main error message
            source: Optional source path involved in the error
            target: Optional target path involved in the error
            details: Optional detailed explanation or context
        """
        context = []
        if source:
            context.append(f"Source: {source}")
        if target:
            context.append(f"Target: {target}")
        if details:
            context.append(details)
        super().__init__(message, "\n".join(context) if context else None)


def handle_file_operation_error(e: Exception, operation: str, path: Path) -> None:
    """
    Handle file operation errors with appropriate logging and context.
    
    Args:
        e: The caught exception
        operation: Description of the operation being performed
        path: Path to the file involved
    """
    if isinstance(e, PermissionError):
        logger.error(f"Permission denied {operation}: {path}")
        logger.debug(f"File permissions: {oct(path.stat().st_mode)[-3:]}")
    elif isinstance(e, FileNotFoundError):
        logger.error(f"File not found while {operation}: {path}")
        if path.parent.exists():
            logger.debug(f"Parent directory exists: {path.parent}")
        else:
            logger.debug(f"Parent directory missing: {path.parent}")
    elif isinstance(e, IsADirectoryError):
        logger.error(f"Expected file but found directory while {operation}: {path}")
    elif isinstance(e, NotADirectoryError):
        logger.error(f"Expected directory but found file while {operation}: {path}")
    else:
        logger.error(f"Error {operation}: {path}")
        logger.error(f"Error details: {str(e)}")
        logger.debug(f"Error type: {type(e).__name__}")


def handle_json_error(e: Exception, file_path: Path) -> None:
    """
    Handle JSON-related errors with appropriate logging and context.
    
    Args:
        e: The caught exception
        file_path: Path to the JSON file
    """
    if isinstance(e, json.JSONDecodeError):
        logger.error(f"Invalid JSON in {file_path}")
        logger.error(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")
        if e.doc:
            # Show the problematic line and position
            line = e.doc.split('\n')[e.lineno - 1]
            pointer = ' ' * (e.colno - 1) + '^'
            logger.debug(f"Context:\n{line}\n{pointer}")
    else:
        logger.error(f"Error processing JSON file: {file_path}")
        logger.error(f"Error details: {str(e)}") 