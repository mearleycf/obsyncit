# Obsidian Settings Sync (ObsyncIt)

A powerful Python tool for synchronizing settings between Obsidian vaults, including themes, plugins, and snippets. Built with safety and flexibility in mind.

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

## Project Structure

- `obsyncit/`: Core package directory
  - `main.py`: CLI entry point
  - `obsync.py`: Core sync functionality
  - `obsync_tui.py`: TUI interface
  - `sync.py`: Sync operations
  - `backup.py`: Backup management
  - `vault.py`: Vault operations
  - `errors.py`: Error handling
  - `schemas/`: JSON schemas and validation
  - `logger.py`: Logging configuration

- `tests/`: Test suite
  - Unit tests
  - Integration tests
  - Test fixtures and utilities

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
