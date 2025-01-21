# Obsidian Settings Sync (ObsyncIt)

A powerful Python tool for synchronizing settings between Obsidian vaults, including themes, plugins, and snippets. Built with safety and flexibility in mind.

## Features

- **Comprehensive Sync**: Synchronize all essential Obsidian settings:
  - Core settings files (appearance.json, app.json, etc.)
  - Plugin configuration (core plugins and community plugins)
  - Plugin data and settings
  - Plugin icons and resources
  - Custom themes
  - CSS snippets
  - Hotkey configurations
  - Template settings
  - Type definitions
  - Migration settings

- **Safety First**:
  - Automatic backup creation before any sync
  - JSON schema validation to prevent corruption
  - Dry-run mode to preview changes
  - Keeps last 5 backups by default
  - Detailed logging of all operations
  - Vault discovery and validation
  - Non-breaking sync (missing files don't stop the sync)

- **Flexible Usage**:
  - Command-line interface for automation
  - Interactive TUI with real-time sync status
  - Selective syncing of specific settings
  - Backup restoration capabilities
  - Multiple vault support with auto-discovery
  - Smart plugin synchronization

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

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

## Usage

After installation, two commands will be available:

### Command Line Interface (CLI)

```bash
# Basic sync between vaults
obsyncit /path/to/source/vault /path/to/target/vault

# Auto-discover and list available vaults
obsyncit --list-vaults

# Custom search path for vaults
obsyncit --list-vaults --search-path ~/Documents

# Dry run to preview changes
obsyncit --dry-run /path/to/source/vault /path/to/target/vault

# Sync specific settings only
obsyncit --items themes plugins community-plugins.json /path/to/source/vault /path/to/target/vault

# Restore from backup
obsyncit --restore latest /path/to/target/vault
```

### Terminal User Interface (TUI)

```bash
# Launch the interactive TUI
obsyncit-tui

# Launch with custom search path
obsyncit-tui --search-path ~/Documents
```

The TUI provides an interactive interface for:

- Discovering and selecting source and target vaults
- Previewing sync operations with detailed status
- Performing dry runs to validate changes
- Executing syncs with visual feedback
- Managing backups and restores

### Synced Items

ObsyncIt syncs the following items by default:

1. Core Settings:
   - app.json
   - appearance.json
   - hotkeys.json
   - types.json
   - templates.json

2. Plugin Settings:
   - core-plugins.json
   - community-plugins.json
   - core-plugins-migration.json
   - plugins directory (with all plugin data)
   - icons directory (plugin resources)

3. Additional Content:
   - themes directory
   - snippets directory

### Configuration

Create a `config.toml` in your config directory:

- Linux/macOS: `~/.config/obsyncit/config.toml`
- Windows: `%APPDATA%\obsyncit\config.toml`

```toml
[sync]
# Enable/disable component syncing
core_settings = true
core_plugins = true
community_plugins = true
themes = true
snippets = true

# Operation settings
dry_run = false
ignore_errors = false

[backup]
# Backup settings
max_backups = 5
backup_dir = ".backups"
dry_run = false
ignore_errors = false

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
└── schemas/         # Configuration schemas
    ├── config.py     # Configuration models
    └── __init__.py   # Schema exports
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
pytest tests/test_vault.py   # Vault tests
pytest tests/test_tui.py     # TUI tests
```

### Type Checking

The project uses mypy for type checking:

```bash
# Run type checker
mypy obsyncit
```

### Code Style

The project follows strict PEP 8 guidelines and uses:

- Black for code formatting
- isort for import sorting
- ruff for fast linting
- mypy for type checking
- pylint for additional static analysis

Run all checks with:

```bash
# Format code
black obsyncit tests
isort obsyncit tests

# Run linters
ruff check obsyncit tests
pylint obsyncit tests
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

If you encounter any issues or need assistance:

1. Check the [Issues](../../issues) section for known problems
2. Check the logs (usually in ~/.obsyncit/logs/ or %APPDATA%\obsyncit\logs\)
3. Run with --debug flag for more detailed logging
4. Open a new issue with logs and steps to reproduce