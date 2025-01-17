# ObsyncIt Core Package

This directory contains the core functionality of the ObsyncIt tool.

## Module Overview

### Core Modules

- `main.py`: Command-line interface entry point
  - Implements CLI using Click
  - Handles command routing and validation
  - Provides rich error messages and help text
  - Manages configuration loading

- `obsync_tui.py`: Terminal User Interface
  - Built with Textual framework
  - Real-time sync status updates
  - Interactive vault selection
  - Progress visualization
  - Backup management interface

- `sync.py`: Core Sync Operations
  - Implements atomic sync operations
  - Handles file and directory synchronization
  - Provides progress callbacks
  - Implements dry-run simulation

### Utility Modules

- `vault_discovery.py`: Vault Discovery
  - Automatic vault detection
  - Platform-specific search paths
  - Vault validation and metadata
  - Cache management

- `backup.py`: Backup Management
  - Atomic backup operations
  - Compression and decompression
  - Rotation policies
  - Restoration workflows

- `vault.py`: Vault Operations
  - Vault structure validation
  - Settings management
  - Plugin compatibility checks
  - Path resolution

- `errors.py`: Error Handling
  - Custom exception hierarchy
  - Rich error context
  - User-friendly messages
  - Error recovery suggestions

- `logger.py`: Logging System
  - Structured logging with Loguru
  - Rotation and retention policies
  - Log compression
  - Debug information collection

### Data Validation

- `schemas/`: JSON Schema Validation
  - Strict schema definitions
  - Version compatibility checks
  - Custom validators
  - Error reporting

## Development Guidelines

1. **Code Style**
   - Use Black for formatting
   - Sort imports with isort
   - Follow PEP 8 guidelines
   - Maintain type hints

2. **Error Handling**
   - Use custom exceptions from `errors.py`
   - Include context in error messages
   - Implement recovery suggestions
   - Log appropriate details

3. **Logging**
   - Use structured logging
   - Include correlation IDs
   - Log at appropriate levels
   - Add relevant context

4. **Testing**
   - Maintain high coverage
   - Test edge cases
   - Mock external dependencies
   - Use pytest fixtures

5. **Documentation**
   - Keep docstrings up to date
   - Follow Google style
   - Include examples
   - Document exceptions

6. **Type Safety**
   - Use type hints consistently
   - Run mypy checks
   - Document type variables
   - Handle optional types properly

## Example Usage

```python
from obsyncit.sync import SyncManager
from obsyncit.vault import VaultManager
from obsyncit.backup import BackupManager

# Initialize managers
vault_mgr = VaultManager()
backup_mgr = BackupManager()
sync_mgr = SyncManager(vault_mgr, backup_mgr)

# Perform sync with progress
async def sync_vaults():
    source = "/path/to/source"
    target = "/path/to/target"
    
    async for progress in sync_mgr.sync(source, target):
        print(f"Progress: {progress.percentage}%")
```

## Contributing

When contributing to core modules:

1. **Documentation**
   - Update module docstrings
   - Add function/method documentation
   - Include usage examples
   - Document changes in CHANGELOG

2. **Testing**
   - Add tests for new features
   - Update existing tests
   - Maintain coverage
   - Test edge cases

3. **Code Quality**
   - Run pre-commit hooks
   - Address linter warnings
   - Maintain type safety
   - Follow project style
