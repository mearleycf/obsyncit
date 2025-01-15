# Obsidian Settings Sync (ObsyncIt)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/yourusername/obsyncit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A powerful Python tool for synchronizing settings between Obsidian vaults, including themes, plugins, and snippets. Built with safety and flexibility in mind.

## Quick Start

```bash
# Install from PyPI
pip install obsyncit

# Basic sync between vaults
obsyncit /path/to/source/vault /path/to/target/vault

# Or use the interactive TUI
obsyncit-tui
```

## Features

- **Comprehensive Sync**: Synchronize all essential Obsidian settings:
  - Core settings files (appearance.json, app.json, etc.)
  - Community plugins and configurations
  - Custom themes
  - CSS snippets
  - Hotkey configurations

- **Safety First**:
  - Automatic backup creation before any sync
  - JSON schema validation to prevent corruption
  - Dry-run mode to preview changes
  - Keeps last 5 backups by default
  - Detailed logging of all operations

- **Flexible Usage**:
  - Command-line interface for automation
  - Interactive TUI for user-friendly operation
  - Selective syncing of specific settings
  - Backup restoration capabilities

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/obsyncit.git
   cd obsyncit
   ```

2. Create a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. For development:

   ```bash
   pip install -e ".[dev]"
   ```

## Usage

### Command Line Interface

```bash
# Basic sync between vaults
python -m obsyncit.main /path/to/source/vault /path/to/target/vault

# Dry run to preview changes
python -m obsyncit.main /path/to/source/vault /path/to/target/vault --dry-run

# Sync specific settings only
python -m obsyncit.main /path/to/source/vault /path/to/target/vault --items themes plugins

# Restore from backup
python -m obsyncit.main /path/to/target/vault --restore latest
```

### TUI Interface

```bash
python -m obsyncit.obsync_tui
```

The TUI provides an interactive interface for:

- Selecting source and target vaults
- Previewing sync operations
- Performing dry runs
- Executing syncs with visual feedback
- Managing backups

## Configuration

Create a `config.toml` file to customize the sync behavior:

```toml
[sync]
# Settings files to sync
settings_files = [
    "appearance.json",
    "app.json",
    "core-plugins.json",
    "community-plugins.json",
    "hotkeys.json"
]

# Directories to sync
settings_dirs = [
    "plugins",
    "themes",
    "snippets"
]

[backup]
# Backup settings
max_backups = 5
backup_dir = ".backups"

[logging]
# Logging configuration
level = "INFO"
log_dir = "logs"
rotation = "1 week"
retention = "1 month"
compression = "zip"
```

## API Documentation

### Core Classes

- `ObsidianSettingsSync`: Main sync manager class
  ```python
  from obsyncit import ObsidianSettingsSync
  
  sync = ObsidianSettingsSync(source_vault, target_vault, config)
  sync.sync_settings(items=['themes', 'plugins'])
  ```

- `Config`: Configuration management
  ```python
  from obsyncit.schemas import Config
  
  config = Config(
      sync={'dry_run': True},
      backup={'max_backups': 5}
  )
  ```

### Error Handling

All operations raise appropriate exceptions from `obsyncit.errors`:
- `VaultError`: Invalid vault operations
- `ConfigError`: Configuration issues
- `ValidationError`: Schema validation failures
- `BackupError`: Backup operations failures
- `SyncError`: Sync operation failures

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Fix permissions on vault directory
   chmod -R u+rw /path/to/vault/.obsidian
   ```

2. **Invalid JSON Settings**
   ```bash
   # Validate settings files
   obsyncit --validate /path/to/vault
   ```

3. **Sync Conflicts**
   ```bash
   # Use dry run to preview changes
   obsyncit --dry-run /source /target
   ```

### Debug Mode

Enable debug logging for detailed information:
```bash
obsyncit --log-level DEBUG /source /target
```

## Development Environment

1. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Configure development tools:
   ```bash
   # Install linting tools
   pip install black ruff pylint

   # Set up test environment
   pip install pytest pytest-cov
   ```

## Project Structure

```
obsyncit/
├── obsyncit/           # Core package
│   ├── __init__.py    # Package initialization
│   ├── main.py        # CLI entry point
│   ├── obsync_tui.py  # TUI interface
│   ├── sync.py        # Sync operations
│   ├── backup.py      # Backup management
│   ├── vault.py       # Vault operations
│   ├── errors.py      # Error definitions
│   ├── logger.py      # Logging setup
│   └── schemas/       # JSON schemas
├── tests/             # Test suite
│   ├── __init__.py
│   ├── test_sync.py
│   ├── test_backup.py
│   └── ...
├── docs/              # Documentation
├── .github/           # GitHub workflows
├── .pre-commit-config.yaml
├── pyproject.toml     # Project configuration
├── setup.py          # Package setup
└── README.md         # This file
```

## Development

### Running Tests

```bash
pytest
```

This will run the test suite with coverage reporting.

### Code Style

The project follows PEP 8 guidelines. Use the provided pre-commit hooks to maintain code quality:

```bash
pre-commit install
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
