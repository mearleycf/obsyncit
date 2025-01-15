"""Tests for logging configuration in ObsyncIt."""

import sys
from pathlib import Path
import pytest
from loguru import logger
from obsyncit.logger import setup_logging
from obsyncit.schemas import Config, LoggingConfig


# Helper Functions
def assert_logger_config(mock_add, expected_config, handler_index=-1):
    """
    Verify logger configuration parameters.
    
    Args:
        mock_add: The mocked logger.add function
        expected_config: Dict of expected configuration values
        handler_index: Index of the handler to check (-1 for file handler, -2 for console handler)
    """
    call = mock_add.call_args_list[handler_index]
    for key, value in expected_config.items():
        assert call[1][key] == value


def assert_handler_setup(mock_add, handler_type="both"):
    """
    Verify basic handler setup.
    
    Args:
        mock_add: The mocked logger.add function
        handler_type: "console", "file", or "both"
    """
    if handler_type in ["console", "both"]:
        console_call = mock_add.call_args_list[0]
        assert console_call[0][0] == sys.stderr
        assert console_call[1]['colorize'] is True
    
    if handler_type in ["file", "both"]:
        file_call = mock_add.call_args_list[1]
        assert isinstance(str(file_call[0][0]), str)
        assert ".log" in str(file_call[0][0])


def verify_log_content(log_dir: Path, expected_messages: list, expected_levels: list = None):
    """
    Verify log file contents.
    
    Args:
        log_dir: Directory containing log files
        expected_messages: List of messages that should be in the log
        expected_levels: Optional list of log levels that should be present
    """
    log_files = list(log_dir.glob("*.log"))
    assert log_files, "No log files found"
    
    with open(log_files[0]) as f:
        content = f.read()
        for message in expected_messages:
            assert message in content
        if expected_levels:
            for level in expected_levels:
                assert level in content


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset logger before each test."""
    logger.remove()  # Remove all handlers
    yield
    logger.remove()  # Cleanup after test


@pytest.fixture
def mock_logger_add(mocker):
    """Mock logger.add for testing."""
    return mocker.patch('loguru.logger.add')


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config(
        logging=LoggingConfig(
            log_dir=".logs",
            level="DEBUG",
            format="{time} | {level} | {message}",
            rotation="1 day",
            retention="1 week",
            compression="zip",
        )
    )


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for log files."""
    log_dir = tmp_path / ".logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


def test_setup_logging_basic(sample_config, temp_log_dir, mocker):
    """Test basic logging setup."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    setup_logging(sample_config)
    
    # Verify basic handler setup
    assert mock_add.call_count == 2  # Console and file handlers
    assert_handler_setup(mock_add)
    
    # Verify console handler config
    assert_logger_config(mock_add, {
        'level': "DEBUG",
        'format': "{time} | {level} | {message}",
        'colorize': True
    }, -2)
    
    # Verify file handler config
    assert_logger_config(mock_add, {
        'rotation': "1 day",
        'retention': "1 week",
        'compression': "zip",
        'level': "DEBUG"
    }, -1)


def test_setup_logging_directory_creation(sample_config, tmp_path):
    """Test log directory creation."""
    log_dir = tmp_path / "nonexistent_logs"
    sample_config.logging.log_dir = str(log_dir)
    
    setup_logging(sample_config)
    
    assert log_dir.exists()
    assert log_dir.is_dir()


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_setup_logging_levels(sample_config, temp_log_dir, mocker, level):
    """Test different logging levels."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    sample_config.logging.level = level
    
    setup_logging(sample_config)
    
    assert_logger_config(mock_add, {'level': level}, -2)  # Console handler
    assert_logger_config(mock_add, {'level': level}, -1)  # File handler


def test_setup_logging_format(sample_config, temp_log_dir, mocker):
    """Test custom log format."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    custom_format = "{time:YYYY-MM-DD HH:mm:ss} | {name}:{function}:{line} | {level} | {message}"
    sample_config.logging.format = custom_format
    setup_logging(sample_config)
    
    assert_logger_config(mock_add, {'format': custom_format}, -2)  # Console handler
    assert_logger_config(mock_add, {'format': custom_format}, -1)  # File handler


@pytest.mark.parametrize("rotation", ["100 MB", "1 week", "1 month", "5 days"])
def test_setup_logging_rotation(sample_config, temp_log_dir, mocker, rotation):
    """Test log rotation settings."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    sample_config.logging.rotation = rotation
    
    setup_logging(sample_config)
    
    assert_logger_config(mock_add, {'rotation': rotation}, -1)


@pytest.mark.parametrize("retention", ["1 week", "1 month", "1 year", "5"])
def test_setup_logging_retention(sample_config, temp_log_dir, mocker, retention):
    """Test log retention settings."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    sample_config.logging.retention = retention
    
    setup_logging(sample_config)
    
    assert_logger_config(mock_add, {'retention': retention}, -1)


@pytest.mark.parametrize("compression", ["zip", "gz", "tar", "tar.gz"])
def test_setup_logging_compression(sample_config, temp_log_dir, mocker, compression):
    """Test log compression settings."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    sample_config.logging.compression = compression
    
    setup_logging(sample_config)
    
    assert_logger_config(mock_add, {'compression': compression}, -1)


def test_setup_logging_integration(sample_config, temp_log_dir):
    """Test actual logging output."""
    sample_config.logging.log_dir = str(temp_log_dir)
    setup_logging(sample_config)
    
    test_message = "Test log message"
    logger.debug(test_message)
    logger.info(test_message)
    logger.warning(test_message)
    logger.error(test_message)
    
    verify_log_content(
        temp_log_dir,
        expected_messages=[test_message],
        expected_levels=["DEBUG", "INFO", "WARNING", "ERROR"]
    ) 