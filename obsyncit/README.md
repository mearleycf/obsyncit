# ObsyncIt Core Package

This directory contains the core functionality of the ObsyncIt tool.

## Module Overview

### Core Modules

- `main.py`: Command-line interface entry point
  - Handles command-line arguments
  - Orchestrates the sync process
  - Provides error handling and logging setup

- `obsync.py`: Core synchronization functionality
  - Handles file operations and validation
  - Manages the sync workflow

- `obsync_tui.py`: Terminal User Interface
  - Provides an interactive interface using Rich
  - Handles user input and validation
  - Displays sync progress and results

### Utility Modules

- `sync.py`: Sync Operations
  - Implements the `SyncManager` class
  - Handles file and directory synchronization
  - Provides sync preview functionality

- `backup.py`: Backup Management
  - Implements the `BackupManager` class
  - Handles backup creation and restoration
  - Manages backup rotation and cleanup

- `vault.py`: Vault Operations
  - Manages Obsidian vault interactions
  - Validates vault structure
  - Handles vault-specific operations

- `errors.py`: Error Handling
  - Defines custom exception classes
  - Provides error context and details
  - Improves error reporting

- `logger.py`: Logging Configuration
  - Sets up logging using Loguru
  - Configures log formats and outputs
  - Manages log rotation and retention

### Data Validation

- `schemas/`: JSON Schema Validation
  - Contains JSON schemas for settings files
  - Implements validation logic
  - Ensures data integrity

## Development Guidelines

1. **Error Handling**
   - Use custom exceptions from `errors.py`
   - Provide meaningful error messages
   - Include context in error details

2. **Logging**
   - Use the logger from `logger.py`
   - Include appropriate log levels
   - Add context to log messages

3. **Code Style**
   - Follow PEP 8 guidelines
   - Use type hints
   - Document classes and functions

4. **Testing**
   - Write unit tests for new functionality
   - Update existing tests when modifying code
   - Ensure test coverage
