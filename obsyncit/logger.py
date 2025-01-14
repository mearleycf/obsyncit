"""
Logging configuration module.

This module provides logging setup and configuration using Loguru.
"""

import sys
from pathlib import Path

from loguru import logger

from obsyncit.schemas import Config


def setup_logging(config: Config) -> None:
    """
    Configure Loguru logging based on configuration.
    
    Args:
        config: Validated configuration object
    """
    log_config = config.logging
    log_dir = Path(log_config.log_dir)
    log_dir.mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        format=log_config.format,
        level=log_config.level,
        colorize=True
    )

    # Add file handler
    logger.add(
        log_dir / "obsync_{time}.log",
        rotation=log_config.rotation,
        retention=log_config.retention,
        compression=log_config.compression,
        level="DEBUG",
        format=log_config.format
    )
