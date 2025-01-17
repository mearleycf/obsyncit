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
  - Vault discovery and validation

- **Flexible Usage**:
  - Command-line interface for automation
  - Interactive TUI with real-time sync status
  - Selective syncing of specific settings
  - Backup restoration capabilities
  - Multiple vault support with auto-discovery

## Installation

Currently, the package is only available for installation from source:

```bash
# Clone the repository
git clone https://github.com/yourusername/obsyncit.git
cd obsyncit

# Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate    # On Windows

# Install in development mode
pip install -e .
```

## Usage

After installation, two commands will be available:

### Command Line Interface (CLI)

```bash
# Basic sync between vaults
obsyncit /path/to/source/vault /path/to/target/vault

# Auto-discover and list available vaults
obsyncit --list-vaults

# Dry run to preview changes
obsyncit --dry-run /path/to/source/vault /path/to/target/vault

# Sync specific settings only
obsyncit --items themes plugins /path/to/source/vault /path/to/target/vault

# Restore from backup
obsyncit --restore latest /path/to/target/vault
```

### Terminal User Interface (TUI)

```bash
# Launch the interactive TUI
obsyncit-tui
```

The TUI provides an interactive interface for:
- Selecting source and target vaults
- Previewing sync operations
- Performing dry runs
- Executing syncs with visual feedback
- Managing backups

### Configuration

Create a `config.toml` in your config directory:
- Linux/macOS: `~/.config/obsyncit/config.toml`
- Windows: `%APPDATA%\obsyncit\config.toml`

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

```
obsyncit/
├── main.py           # CLI entry point
├── obsync_tui.py     # TUI interface
├── sync.py          # Core sync operations
├── backup.py        # Backup management
├── vault.py         # Vault operations
├── vault_discovery.py # Vault discovery logic
├── errors.py        # Error handling
├── logger.py        # Logging configuration
└── schemas/         # JSON schemas
    ├── appearance.json
    ├── app.json
    └── ...
```

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate    # On Windows

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=obsyncit

# Run specific test categories
pytest tests/test_sync.py    # Sync tests
pytest tests/test_backup.py  # Backup tests
pytest tests/test_cli.py     # CLI tests
```

### Code Style

The project follows strict PEP 8 guidelines and uses:
- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
