"""Logging Configuration for ObsyncIt.

This module provides a comprehensive logging setup using Loguru. It handles:

1. Console Logging
   - Colorized output
   - Custom formatting
   - Configurable log levels
   - Exception tracebacks with variable inspection

2. File Logging
   - Automatic log file rotation (by size or time)
   - Configurable retention policies
   - Log file compression
   - Complete debug logging for troubleshooting

3. Configuration
   - TOML-based configuration
   - Multiple handler support
   - Custom format strings
   - Flexible sink types

Format Placeholders:
    {time}: Timestamp (customizable format)
    {level}: Log level (DEBUG, INFO, etc.)
    {message}: Log message
    {name}: Logger name
    {function}: Function name
    {line}: Line number
    {file}: File name
    {module}: Module name
    {thread}: Thread ID
    {process}: Process ID

Example Usage:
    >>> from obsyncit.logger import setup_logging
    >>> from obsyncit.schemas import Config, LoggingConfig
    >>> 
    >>> # Create configuration
    >>> config = Config(
    ...     logging=LoggingConfig(
    ...         log_dir=".logs",
    ...         level="INFO",
    ...         format="{time} | {level} | {message}",
    ...         rotation="1 day",
    ...         retention="1 week",
    ...         compression="zip"
    ...     )
    ... )
    >>> 
    >>> # Set up logging
    >>> setup_logging(config)
    >>> 
    >>> # Use logger
    >>> from loguru import logger
    >>> logger.info("Application started")
    >>> 
    >>> try:
    ...     raise ValueError("Example error")
    ... except Exception as e:
    ...     logger.exception("Caught an error")
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal, Union, Any, Dict, TypeAlias

from loguru import logger

from obsyncit.schemas import Config

# Type definitions for log configuration
LogLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
"""Valid log levels for handlers"""

RotationUnit: TypeAlias = Literal["bytes", "KB", "MB", "GB", "days", "months", "years"]
"""Valid units for log file rotation"""

RetentionUnit: TypeAlias = Literal["days", "months", "years"]
"""Valid units for log file retention"""

CompressionFormat: TypeAlias = Literal[
    "gz", "bz2", "zip", "xz", "lzma", "tar", "tar.gz", "tar.bz2"
]
"""Valid compression formats for rotated logs"""


@dataclass
class LoggerConfig:
    """Configuration for a single logger handler.
    
    This class defines the configuration for a single logging handler,
    supporting both console and file logging with extensive customization
    options.
    
    Attributes:
        sink: Output destination (file path, sys.stderr, etc.)
        level: Minimum log level ("DEBUG", "INFO", etc.)
        format: Message format with placeholders
        colorize: Enable ANSI colors (console only)
        rotation: Log rotation trigger ("100 MB", "1 day", etc.)
        retention: Log retention period ("1 week", "1 month", etc.)
        compression: Compression format for old logs
        backtrace: Include exception backtraces
        diagnose: Include variable values in tracebacks
    
    Example:
        >>> config = LoggerConfig(
        ...     sink="app.log",
        ...     level="DEBUG",
        ...     rotation="1 day",
        ...     compression="zip"
        ... )
        >>> config_dict = config.to_dict()
    """
    sink: Union[str, Path, "sys.stderr"]
    """Where to send the logs (file path, sys.stderr, etc.)"""
    
    level: LogLevel = "INFO"
    """Minimum log level to capture"""
    
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    """Log message format string with placeholders"""
    
    colorize: bool = True
    """Whether to use ANSI colors (console only)"""
    
    rotation: Optional[str] = None
    """When to rotate log files (time or size based)"""
    
    retention: Optional[str] = None
    """How long to keep old logs"""
    
    compression: Optional[CompressionFormat] = None
    """How to compress rotated logs"""
    
    backtrace: bool = True
    """Whether to include exception backtraces"""
    
    diagnose: bool = True
    """Whether to include variable values in tracebacks"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary for Loguru.
        
        This method creates a dictionary of configuration options suitable
        for passing to loguru.logger.add(). It filters out None values
        to ensure only valid options are passed.

        Returns:
            Dict of configuration options for Loguru
            
        Example:
            >>> config = LoggerConfig(sink="app.log", level="DEBUG")
            >>> loguru.logger.add(**config.to_dict())
        """
        config_dict = {
            "sink": self.sink,
            "level": self.level,
            "format": self.format,
            "colorize": self.colorize,
            "backtrace": self.backtrace,
            "diagnose": self.diagnose,
        }

        # Add optional parameters only if they're set
        if self.rotation:
            config_dict["rotation"] = self.rotation
        if self.retention:
            config_dict["retention"] = self.retention
        if self.compression:
            config_dict["compression"] = self.compression

        return config_dict


def _add_handler(config: LoggerConfig) -> int:
    """Add a new logger handler with the specified configuration.
    
    This internal function adds a new handler to the Loguru logger
    using the provided configuration.
    
    Args:
        config: Handler configuration object

    Returns:
        Handler ID from Loguru for future reference
        
    Example:
        >>> handler_id = _add_handler(LoggerConfig(
        ...     sink="app.log",
        ...     level="DEBUG"
        ... ))
    """
    return logger.add(**config.to_dict())


def setup_logging(config: Config) -> None:
    """Configure Loguru logging based on the provided configuration.
    
    This function sets up a complete logging configuration with both
    console and file handlers. It first removes any existing handlers
    to ensure a clean configuration.

    Console Handler Features:
        - Colorized output for better readability
        - Configurable format string
        - User-specified log level
        - Exception tracebacks with variable inspection

    File Handler Features:
        - Automatic log file creation and rotation
        - Size or time-based rotation
        - Configurable retention period
        - Log file compression
        - Always logs at DEBUG level for troubleshooting

    Log Format Options:
        - {time}: Timestamp (e.g., "2024-01-18 12:34:56")
        - {level}: Log level (e.g., "INFO", "ERROR")
        - {message}: The actual log message
        - {name}: Logger name (e.g., "obsyncit.sync")
        - {function}: Function name (e.g., "sync_settings")
        - {line}: Line number in source file
        - {file}: Source file name
        - {module}: Module name
        - {thread}: Thread ID for debugging
        - {process}: Process ID for debugging
    
    Args:
        config: Configuration object containing logging settings
        
    Example:
        >>> # Basic setup with defaults
        >>> config = Config(
        ...     logging=LoggingConfig(
        ...         log_dir=".logs",
        ...         level="INFO"
        ...     )
        ... )
        >>> setup_logging(config)
        >>> 
        >>> # Advanced setup with rotation
        >>> config = Config(
        ...     logging=LoggingConfig(
        ...         log_dir=".logs",
        ...         level="DEBUG",
        ...         format="{time} | {level: <8} | {name}:{function}:{line} | {message}",
        ...         rotation="1 day",
        ...         retention="1 week",
        ...         compression="zip"
        ...     )
        ... )
        >>> setup_logging(config)
        >>> 
        >>> # Use the configured logger
        >>> from loguru import logger
        >>> logger.info("Application started")
        >>> try:
        ...     raise ValueError("Example error")
        ... except Exception:
        ...     logger.exception("Caught an error")
    
    Notes:
        - The log directory will be created if it doesn't exist
        - File logs are always at DEBUG level regardless of console level
        - Both handlers include exception tracebacks with variables
        - Log files are named with timestamps for easy identification
        - Compression is applied to rotated log files only
        - The console handler respects the configured log level
        - Exception logging includes variable values by default
        - Color output is enabled for console but not file logs
        - All existing handlers are removed before configuration
    """
    log_config = config.logging
    log_dir = Path(log_config.log_dir)
    log_dir.mkdir(exist_ok=True)

    # Remove all existing handlers
    logger.remove()

    # Configure console logging
    logger.add(
        sink=sys.stderr,
        level=log_config.level,
        format=log_config.format,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Configure file logging (always DEBUG level)
    logger.add(
        sink=str(log_dir / "obsyncit_{time}.log"),
        level="DEBUG",
        format=log_config.format,
        rotation=log_config.rotation,
        retention=log_config.retention,
        compression=log_config.compression,
        backtrace=True,
        diagnose=True,
    )

    # Log configuration details at appropriate levels
    logger.info("Logging configured successfully")
    logger.debug(f"Log directory: {log_dir}")
    logger.debug(f"Console level: {log_config.level}")
    logger.debug(f"File rotation: {log_config.rotation}")
    logger.debug(f"File retention: {log_config.retention}")
    logger.debug(f"File compression: {log_config.compression}")