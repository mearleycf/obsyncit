"""
Error handling module for ObsyncIt.

This module provides custom exceptions and error handling utilities
to improve error reporting and recovery strategies.

The module implements a hierarchical error system:
1. Base ObsyncError for general errors
2. Specialized errors for specific operations:
   - VaultError: Vault-related operations
   - ConfigError: Configuration issues
   - ValidationError: Schema validation
   - BackupError: Backup operations
   - SyncError: Sync operations

Each error type provides:
- Descriptive error messages
- Detailed context information
- Operation-specific attributes
- Proper error chaining

Basic Usage Examples:
    ```python
    try:
        sync_manager.sync_settings()
    except VaultError as e:
        print(f"Vault error: {e.message}")
        print(f"Vault path: {e.vault_path}")
    except ConfigError as e:
        print(f"Config error: {e.message}")
        print(f"Config file: {e.file_path}")
    except ValidationError as e:
        print(f"Validation error: {e.message}")
        print(f"Schema errors: {e.schema_errors}")
    except BackupError as e:
        print(f"Backup error: {e.message}")
        print(f"Backup path: {e.backup_path}")
    except SyncError as e:
        print(f"Sync error: {e.message}")
        print(f"Source: {e.source}")
        print(f"Target: {e.target}")
    except ObsyncError as e:
        print(f"General error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    ```

Practical Examples:

1. Raising Vault Errors:
    ```python
    def validate_vault(vault_path: Path) -> None:
        if not vault_path.exists():
            raise VaultError(
                message="Vault directory not found",
                vault_path=vault_path,
                details="Please check if the vault path exists"
            )
        if not (vault_path / ".obsidian").exists():
            raise VaultError(
                message="Invalid vault structure",
                vault_path=vault_path,
                details="Missing .obsidian directory"
            )
    ```

2. Handling Configuration Errors:
    ```python
    def load_config(config_path: Path) -> Config:
        try:
            config = Config.from_file(config_path)
            return config
        except json.JSONDecodeError as e:
            raise ConfigError(
                message="Invalid configuration format",
                file_path=config_path,
                details=f"JSON error at line {e.lineno}: {e.msg}"
            )
        except KeyError as e:
            raise ConfigError(
                message="Missing required configuration",
                file_path=config_path,
                details=f"Missing key: {e}"
            )
    ```

3. Using Error Handlers:
    ```python
    def safe_read_json(file_path: Path) -> dict:
        try:
            with open(file_path) as f:
                return json.load(f)
        except FileNotFoundError as e:
            handle_file_operation_error(e, "reading", file_path)
            raise
        except json.JSONDecodeError as e:
            handle_json_error(e, file_path)
            raise ValidationError(
                message="Invalid JSON format",
                file_path=file_path,
                schema_errors=[f"JSON error at line {e.lineno}: {e.msg}"]
            )
    ```

4. Chaining Errors:
    ```python
    def sync_vault_settings(source: Path, target: Path) -> None:
        try:
            validate_vault(source)
            validate_vault(target)
        except VaultError as e:
            raise SyncError(
                message="Sync failed due to invalid vault",
                source=source,
                target=target,
                details=str(e)
            ) from e
    ```

The examples above demonstrate:
- Proper error creation with context
- Error chaining for better debugging
- Using error handlers for common operations
- Consistent error reporting patterns
"""

import json
from pathlib import Path
from typing import Optional, List, Union

from loguru import logger


class ObsyncError(Exception):
    """
    Base exception class for ObsyncIt errors.

    This class serves as the foundation for all custom exceptions in the
    application. It provides:
    - A primary error message
    - Optional detailed information
    - A formatted full message combining both

    The class is designed to be subclassed for specific error types,
    while maintaining a consistent interface for error handling.

    Attributes:
        message (str): Primary error message
        details (Optional[str]): Additional error details or context
        full_message (str): Formatted combination of message and details

    Example:
        ```python
        try:
            raise ObsyncError("Operation failed", "Network timeout")
        except ObsyncError as e:
            print(e.message)  # "Operation failed"
            print(e.details)  # "Network timeout"
            print(e.full_message)  # "Operation failed\nDetails: Network timeout"
        ```
    """

    def __init__(self, message: str, details: Optional[str] = None):
        """
        Initialize the exception.
        
        Args:
            message: Main error message describing what went wrong
            details: Optional detailed explanation or context about the error

        Example:
            ```python
            # Basic error
            raise ObsyncError("File not found")

            # Error with details
            raise ObsyncError(
                "Permission denied",
                "User lacks write permission for target directory"
            )
            ```
        """
        self.message = message
        self.details = details
        super().__init__(self.full_message)

    @property
    def full_message(self) -> str:
        """
        Get the full error message including details if available.

        Returns:
            str: Formatted error message with details if present

        Example:
            ```python
            error = ObsyncError("Failed", "No space left")
            print(error.full_message)  # "Failed\nDetails: No space left"
            ```
        """
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class VaultError(ObsyncError):
    """
    Raised for errors related to Obsidian vault operations.

    This exception is used when operations on an Obsidian vault fail,
    such as:
    - Invalid vault structure
    - Missing required directories
    - Permission issues
    - File system errors

    Attributes:
        message (str): Primary error message
        vault_path (Path): Path to the vault where the error occurred
        details (Optional[str]): Additional error context

    Example:
        ```python
        try:
            if not vault_path.exists():
                raise VaultError(
                    "Vault not found",
                    vault_path=vault_path,
                    details="Directory does not exist"
                )
        except VaultError as e:
            print(f"Error with vault at {e.vault_path}: {e.message}")
        ```
    """

    def __init__(self, message: str, vault_path: Path, details: Optional[str] = None):
        """
        Initialize the vault error.
        
        Args:
            message: Main error message describing what went wrong
            vault_path: Path to the vault where the error occurred
            details: Optional detailed explanation or context

        Example:
            ```python
            raise VaultError(
                "Invalid vault structure",
                vault_path=Path("/path/to/vault"),
                details="Missing .obsidian directory"
            )
            ```
        """
        self.vault_path = vault_path
        vault_context = f"Vault: {vault_path}"
        super().__init__(message, f"{vault_context}\n{details}" if details else vault_context)


class ConfigError(ObsyncError):
    """
    Raised for configuration-related errors.

    This exception handles errors related to configuration:
    - Missing configuration files
    - Invalid configuration format
    - Schema validation failures
    - Invalid settings values

    Attributes:
        message (str): Primary error message
        file_path (Optional[Path]): Path to the configuration file
        details (Optional[str]): Additional error context

    Example:
        ```python
        try:
            if not config_file.exists():
                raise ConfigError(
                    "Config file not found",
                    file_path=config_file
                )
        except ConfigError as e:
            print(f"Configuration error: {e.message}")
            if e.file_path:
                print(f"Config file: {e.file_path}")
        ```
    """

    def __init__(self, message: str, file_path: Optional[Path] = None, details: Optional[str] = None):
        """
        Initialize the configuration error.

        Args:
            message: Main error message
            file_path: Optional path to the configuration file
            details: Optional detailed explanation

        Example:
            ```python
            raise ConfigError(
                "Invalid configuration",
                file_path=Path("config.toml"),
                details="Missing required 'sync' section"
            )
            ```
        """
        self.file_path = file_path
        if file_path:
            config_context = f"Config file: {file_path}"
            super().__init__(message, f"{config_context}\n{details}" if details else config_context)
        else:
            super().__init__(message, details)


class ValidationError(ObsyncError):
    """
    Raised when validation fails for settings files.

    This exception handles JSON schema validation errors:
    - Invalid JSON syntax
    - Missing required fields
    - Invalid field types
    - Schema constraint violations

    Attributes:
        message (str): Primary error message
        file_path (Path): Path to the file that failed validation
        schema_errors (List[str]): List of specific validation errors

    Example:
        ```python
        try:
            errors = validate_schema(data)
            if errors:
                raise ValidationError(
                    "Schema validation failed",
                    file_path=Path("settings.json"),
                    schema_errors=errors
                )
        except ValidationError as e:
            print(f"Validation failed: {e.message}")
            for error in e.schema_errors:
                print(f"- {error}")
        ```
    """

    def __init__(self, message: str, file_path: Path, schema_errors: List[str]):
        """
        Initialize the validation error.

        Args:
            message: Main error message
            file_path: Path to the file that failed validation
            schema_errors: List of specific validation errors

        Example:
            ```python
            raise ValidationError(
                "Invalid settings format",
                file_path=Path("app.json"),
                schema_errors=[
                    "Missing required field: theme",
                    "Invalid type for field: fontSize"
                ]
            )
            ```
        """
        self.file_path = file_path
        self.schema_errors = schema_errors
        validation_context = f"File: {file_path}\nErrors:\n" + "\n".join(f"- {e}" for e in schema_errors)
        super().__init__(message, validation_context)


class BackupError(ObsyncError):
    """
    Raised for errors during backup operations.

    This exception handles backup-related errors:
    - Backup creation failures
    - Restore operation failures
    - Backup management issues
    - Storage space problems

    Attributes:
        message (str): Primary error message
        backup_path (Path): Path to the backup location
        details (Optional[str]): Additional error context

    Example:
        ```python
        try:
            if not backup_path.exists():
                raise BackupError(
                    "Backup not found",
                    backup_path=backup_path,
                    details="Cannot restore from non-existent backup"
                )
        except BackupError as e:
            print(f"Backup error: {e.message}")
            print(f"Backup path: {e.backup_path}")
        ```
    """

    def __init__(self, message: str, backup_path: Path, details: Optional[str] = None):
        """
        Initialize the backup error.

        Args:
            message: Main error message
            backup_path: Path to the backup location
            details: Optional detailed explanation

        Example:
            ```python
            raise BackupError(
                "Backup creation failed",
                backup_path=Path(".backups/latest"),
                details="Insufficient disk space"
            )
            ```
        """
        self.backup_path = backup_path
        backup_context = f"Backup path: {backup_path}"
        super().__init__(message, f"{backup_context}\n{details}" if details else backup_context)


class SyncError(ObsyncError):
    """
    Raised for errors during sync operations.

    This exception handles synchronization failures:
    - File copy errors
    - Permission issues
    - Network problems
    - Validation failures during sync

    Attributes:
        message (str): Primary error message
        source (Path): Source vault path
        target (Path): Target vault path
        details (Optional[str]): Additional error context

    Example:
        ```python
        try:
            if not source_file.exists():
                raise SyncError(
                    "Source file missing",
                    source=source_vault,
                    target=target_vault,
                    details=f"File: {source_file}"
                )
        except SyncError as e:
            print(f"Sync failed: {e.message}")
            print(f"Source: {e.source}")
            print(f"Target: {e.target}")
        ```
    """

    def __init__(self, message: str, source: Path, target: Path, details: Optional[str] = None):
        """
        Initialize the sync error.

        Args:
            message: Main error message
            source: Source vault path
            target: Target vault path
            details: Optional detailed explanation

        Example:
            ```python
            raise SyncError(
                "Failed to copy settings",
                source=Path("/source/vault"),
                target=Path("/target/vault"),
                details="Permission denied"
            )
            ```
        """
        self.source = source
        self.target = target
        sync_context = f"Source: {source}\nTarget: {target}"
        super().__init__(message, f"{sync_context}\n{details}" if details else sync_context)


def handle_file_operation_error(error: Exception, operation: str, path: Union[str, Path]) -> None:
    """
    Handle file system operation errors with appropriate logging.

    This utility function provides consistent error handling for file
    operations, with appropriate logging and context information.

    Args:
        error: The exception that occurred
        operation: Description of the operation being performed
        path: Path to the file or directory involved

    Example:
        ```python
        try:
            shutil.copy2(source, target)
        except Exception as e:
            handle_file_operation_error(e, "copying settings", target)
            raise SyncError("Failed to copy settings")
        ```
    """
    logger.error(f"Error {operation}: {path}")
    logger.debug("", exc_info=True)


def handle_json_error(error: json.JSONDecodeError, file_path: Path) -> None:
    """
    Handle JSON parsing errors with detailed error reporting.

    This utility function provides detailed error reporting for JSON
    parsing failures, including line and column information.

    Args:
        error: The JSON decode error
        file_path: Path to the JSON file

    Example:
        ```python
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            handle_json_error(e, file_path)
            raise ValidationError("Invalid JSON format")
        ```
    """
    logger.error(f"Invalid JSON in {file_path}")
    logger.error(f"Error at line {error.lineno}, column {error.colno}: {error.msg}")
    logger.debug("", exc_info=True)
