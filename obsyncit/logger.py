"""
Logging configuration module.

This module provides logging setup and configuration using Loguru. It handles
both console and file logging, with support for log rotation, retention,
compression, and custom formatting.

Typical usage example:
    >>> from obsyncit.logger import setup_logging
    >>> from obsyncit.schemas import Config
    >>> 
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
    >>> setup_logging(config)
    >>> 
    >>> # Now you can use logger throughout your code
    >>> from loguru import logger
    >>> logger.info("Logging configured and ready")
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal, Union, Any, Dict

from loguru import logger

from obsyncit.schemas import Config

# Valid log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Valid rotation units
RotationUnit = Literal["bytes", "KB", "MB", "GB", "days", "months", "years"]

# Valid retention units
RetentionUnit = Literal["days", "months", "years"]

# Valid compression formats
CompressionFormat = Literal["gz", "bz2", "zip", "xz", "lzma", "tar", "tar.gz", "tar.bz2"]


@dataclass
class LoggerConfig:
    """Configuration for a single logger handler.
    
    Attributes:
        sink: Where to send the logs (file path, sys.stderr, etc.)
        level: Minimum log level to capture
        format: Log message format string
        colorize: Whether to colorize output (console only)
        rotation: When to rotate log files (file only)
        retention: How long to keep old logs (file only)
        compression: How to compress rotated logs (file only)
        backtrace: Whether to include exception backtraces
        diagnose: Whether to include variable values in tracebacks
    """
    sink: Union[str, Path, "sys.stderr"]
    level: LogLevel = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    colorize: bool = True
    rotation: Optional[str] = None
    retention: Optional[str] = None
    compression: Optional[CompressionFormat] = None
    backtrace: bool = True
    diagnose: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary for loguru.

        Returns:
            Dictionary of loguru configuration options with None values filtered out
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
    
    Args:
        config: Handler configuration

    Returns:
        Handler ID from loguru
    """
    return logger.add(**config.to_dict())


def setup_logging(config: Config) -> None:
    """Configure Loguru logging based on configuration.
    
    This function sets up both console and file logging with the specified
    configuration. It removes any existing handlers before adding new ones.

    The console handler supports:
    - Colorized output
    - Custom formatting
    - Configurable log level
    - Exception backtraces

    The file handler supports:
    - Log file rotation (by size or time)
    - Log retention policies
    - Compression of old logs
    - Full debug logging
    
    Args:
        config: Configuration object containing logging settings

    Example:
        >>> setup_logging(Config(
        ...     logging=LoggingConfig(
        ...         log_dir=".logs",
        ...         level="INFO",
        ...         format="{time} | {level} | {message}",
        ...         rotation="1 day",
        ...         retention="1 week",
        ...         compression="zip"
        ...     )
        ... ))
    """
    log_config = config.logging
    log_dir = Path(log_config.log_dir)
    log_dir.mkdir(exist_ok=True)

    # Remove all existing handlers
    logger.remove()

    # Configure console logging
    console_config = LoggerConfig(
        sink=sys.stderr,
        level=log_config.level,
        format=log_config.format,
        colorize=True,
    )
    _add_handler(console_config)

    # Configure file logging
    file_config = LoggerConfig(
        sink=str(log_dir / "obsync_{time}.log"),
        level="DEBUG",  # Always use DEBUG for file logging
        format=log_config.format,
        colorize=False,
        rotation=log_config.rotation,
        retention=log_config.retention,
        compression=log_config.compression,
    )
    _add_handler(file_config)

    logger.info("Logging configured successfully")
    logger.debug(f"Log directory: {log_dir}")
    logger.debug(f"Console level: {log_config.level}")
    logger.debug(f"File rotation: {log_config.rotation}")
    logger.debug(f"File retention: {log_config.retention}")
    logger.debug(f"File compression: {log_config.compression}")