# ObsyncIt Architecture

This document provides a detailed overview of ObsyncIt's architecture and design decisions.

## Core Concepts

ObsyncIt is built around several key concepts:

1. **Vaults**: Obsidian vaults that contain settings and configurations
2. **Settings**: Various configuration files and directories that can be synchronized
3. **Sync Operations**: The process of copying settings between vaults
4. **Backups**: Automatic backup creation before sync operations

## Component Overview

### Core Components

1. **Vault Management** (`vault.py`)
   - Handles vault validation and file operations
   - Manages access to vault settings and directories
   - Provides consistent error handling for file operations

2. **Vault Discovery** (`vault_discovery.py`)
   - Recursively searches for Obsidian vaults
   - Validates discovered vaults
   - Gathers vault metadata

3. **Sync Operations** (`sync.py`)
   - Orchestrates synchronization between vaults
   - Handles both file and directory synchronization
   - Manages backup creation during sync
   - Provides dry-run capability

4. **Backup Management** (`backup.py`)
   - Creates and manages backups
   - Handles backup rotation
   - Provides restore functionality

### Supporting Components

1. **Schema Validation** (`schemas/`)
   - Defines data models for configuration
   - Validates JSON configuration files
   - Ensures type safety

2. **Error Handling** (`errors.py`)
   - Custom exception types
   - Standardized error handling
   - Detailed error context

3. **Logging** (`logger.py`)
   - Configurable logging levels
   - File and console output
   - Rotation and retention policies

4. **User Interfaces**
   - CLI interface (`main.py`)
   - TUI interface (`obsync_tui.py`)

## Data Flow

1. **Configuration Loading**
   ```
   config.toml -> Config Schema -> Runtime Config
   ```

2. **Vault Discovery**
   ```
   Search Path -> Directory Traversal -> Vault Validation -> Vault List
   ```

3. **Sync Operation**
   ```
   Source Vault -> Validation -> Backup -> File Copy -> Target Vault
   ```

4. **Error Handling**
   ```
   Error -> Custom Exception -> Error Handler -> Logging -> User Feedback
   ```

## Key Design Decisions

1. **Type Safety**
   - Comprehensive type hints throughout codebase
   - Runtime type checking through pydantic models
   - Mypy static type checking

2. **Error Handling**
   - Custom exception hierarchy
   - Detailed error context
   - Optional error ignoring for non-critical failures

3. **Configuration**
   - TOML-based configuration
   - Schema validation
   - Sane defaults

4. **Testing**
   - Comprehensive test suite
   - Integration tests
   - Fixture-based testing

## Directory Structure

```
obsyncit/
├── obsyncit/              # Main package
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── obsync_tui.py     # TUI interface
│   ├── sync.py          # Core sync logic
│   ├── backup.py        # Backup management
│   ├── vault.py         # Vault operations
│   ├── vault_discovery.py # Vault discovery
│   ├── errors.py        # Error handling
│   ├── logger.py        # Logging setup
│   └── schemas/         # Data models
│       ├── __init__.py
│       ├── config.py
│       └── obsidian.py
├── tests/               # Test suite
├── docs/               # Documentation
├── scripts/            # Utility scripts
└── examples/           # Example configs
```

## Error Handling Strategy

1. **Exception Hierarchy**
   ```
   ObsyncError (Base)
   ├── ValidationError
   ├── SyncError
   └── BackupError
   ```

2. **Error Recovery**
   - Automatic backup creation
   - Optional error ignoring
   - Detailed logging
   - User-friendly error messages

## Testing Strategy

1. **Unit Tests**
   - Individual component testing
   - Mocked dependencies
   - Edge case coverage

2. **Integration Tests**
   - End-to-end sync operations
   - Real file system operations
   - Configuration validation

3. **Property Tests**
   - Sync operation invariants
   - Data validation properties
   - Error handling consistency

## Future Considerations

1. **Plugin System**
   - Custom sync handlers
   - User-defined validations
   - Extension points

2. **Performance Optimization**
   - Parallel sync operations
   - Incremental sync
   - Change detection

3. **Enhanced UI**
   - GUI interface
   - Progress visualization
   - Interactive conflict resolution

4. **Remote Sync**
   - Cloud storage support
   - Remote vault discovery
   - Network resilience
   - Conflict resolution

5. **Enhanced Security**
   - Encryption at rest
   - Secure backup storage
   - Authentication for remote operations
   - Audit logging

6. **Monitoring and Analytics**
   - Sync operation metrics
   - Performance monitoring
   - Usage analytics
   - Error tracking

## Development Guidelines

### Code Style

1. **Python Standards**
   - Follow PEP 8
   - Use type hints
   - Write comprehensive docstrings
   - Maintain clear module structure

2. **Error Handling**
   - Use custom exceptions
   - Provide detailed error context
   - Log appropriately
   - Handle edge cases

3. **Testing**
   - Write tests first
   - Mock external dependencies
   - Test edge cases
   - Maintain test coverage

### Documentation

1. **Code Documentation**
   - Module docstrings
   - Function docstrings
   - Type hints
   - Inline comments for complex logic

2. **User Documentation**
   - Installation guide
   - Usage examples
   - Configuration reference
   - Troubleshooting guide

### Version Control

1. **Git Practices**
   - Semantic versioning
   - Clear commit messages
   - Feature branches
   - Pull request templates

2. **Release Process**
   - Version bumping
   - Changelog updates
   - Documentation updates
   - Release notes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Setting up development environment
- Code style requirements
- Testing procedures
- Pull request process
- Documentation requirements