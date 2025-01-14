"""Tests for logging configuration in ObsyncIt."""

import sys
from pathlib import Path
import pytest
from loguru import logger
from obsyncit.logger import setup_logging
from obsyncit.schemas import Config, LoggingConfig


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
            compression="zip"
        )
    )


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for log files."""
    log_dir = tmp_path / ".logs"
    log_dir.mkdir()
    return log_dir


def test_setup_logging_basic(sample_config, temp_log_dir, mocker):
    """Test basic logging setup."""
    # Mock logger.add to capture parameters
    mock_add = mocker.patch('loguru.logger.add')
    
    # Update config to use temp directory
    sample_config.logging.log_dir = str(temp_log_dir)
    
    # Setup logging
    setup_logging(sample_config)
    
    # Verify logger was configured correctly
    assert mock_add.call_count == 2  # Console and file handlers
    
    # Check console handler
    console_call = mock_add.call_args_list[0]
    assert console_call[0][0] == sys.stderr
    assert console_call[1]['level'] == "DEBUG"
    assert console_call[1]['format'] == "{time} | {level} | {message}"
    assert console_call[1]['colorize'] is True
    
    # Check file handler
    file_call = mock_add.call_args_list[1]
    assert str(temp_log_dir) in str(file_call[0][0])
    assert file_call[1]['rotation'] == "1 day"
    assert file_call[1]['retention'] == "1 week"
    assert file_call[1]['compression'] == "zip"
    assert file_call[1]['level'] == "DEBUG"


def test_setup_logging_directory_creation(sample_config, tmp_path):
    """Test log directory creation."""
    log_dir = tmp_path / "nonexistent_logs"
    sample_config.logging.log_dir = str(log_dir)
    
    # Setup logging
    setup_logging(sample_config)
    
    # Verify directory was created
    assert log_dir.exists()
    assert log_dir.is_dir()


def test_setup_logging_levels(sample_config, temp_log_dir, mocker):
    """Test different logging levels."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    # Test each log level
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        sample_config.logging.level = level
        setup_logging(sample_config)
        
        # Verify console handler level
        console_call = mock_add.call_args_list[-2]
        assert console_call[1]['level'] == level


def test_setup_logging_format(sample_config, temp_log_dir, mocker):
    """Test custom log format."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    # Test custom format
    custom_format = "{time:YYYY-MM-DD HH:mm:ss} | {name}:{function}:{line} | {level} | {message}"
    sample_config.logging.format = custom_format
    setup_logging(sample_config)
    
    # Verify format was applied
    for call in mock_add.call_args_list[-2:]:  # Check both handlers
        assert call[1]['format'] == custom_format


def test_setup_logging_rotation(sample_config, temp_log_dir, mocker):
    """Test log rotation settings."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    # Test different rotation settings
    rotations = ["100 MB", "1 week", "1 month", "5 days"]
    for rotation in rotations:
        sample_config.logging.rotation = rotation
        setup_logging(sample_config)
        
        # Verify rotation setting
        file_call = mock_add.call_args_list[-1]
        assert file_call[1]['rotation'] == rotation


def test_setup_logging_retention(sample_config, temp_log_dir, mocker):
    """Test log retention settings."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    # Test different retention settings
    retentions = ["1 week", "1 month", "1 year", "5"]
    for retention in retentions:
        sample_config.logging.retention = retention
        setup_logging(sample_config)
        
        # Verify retention setting
        file_call = mock_add.call_args_list[-1]
        assert file_call[1]['retention'] == retention


def test_setup_logging_compression(sample_config, temp_log_dir, mocker):
    """Test log compression settings."""
    mock_add = mocker.patch('loguru.logger.add')
    sample_config.logging.log_dir = str(temp_log_dir)
    
    # Test different compression settings
    compressions = ["zip", "gz", "tar", "tar.gz"]
    for compression in compressions:
        sample_config.logging.compression = compression
        setup_logging(sample_config)
        
        # Verify compression setting
        file_call = mock_add.call_args_list[-1]
        assert file_call[1]['compression'] == compression


def test_setup_logging_integration(sample_config, temp_log_dir):
    """Test actual logging output."""
    sample_config.logging.log_dir = str(temp_log_dir)
    setup_logging(sample_config)
    
    # Log some messages
    test_message = "Test log message"
    logger.debug(test_message)
    logger.info(test_message)
    logger.warning(test_message)
    logger.error(test_message)
    
    # Check log file contents
    log_files = list(temp_log_dir.glob("*.log"))
    assert log_files
    
    with open(log_files[0]) as f:
        content = f.read()
        assert test_message in content
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            assert level in content 