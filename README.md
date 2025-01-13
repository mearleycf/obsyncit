# Obsidian Settings Sync

A Python tool to synchronize settings between Obsidian vaults, including themes, plugins, and snippets.

## Features

- Sync Obsidian settings between vaults
- Backup existing settings before sync
- Validate JSON configuration files
- Dry-run mode to preview changes
- Selective syncing of specific settings
- Beautiful TUI interface
- Detailed logging
- Automatic cleanup of old backups

## Installation

1. Clone this repository
2. Create a virtual environment (optional but recommended):

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

## Usage

### Command Line Interface

```bash
# Sync all settings
python obsync.py /path/to/source/vault /path/to/target/vault

# Dry run to preview changes
python obsync.py /path/to/source/vault /path/to/target/vault --dry-run

# Sync specific settings only
python obsync.py /path/to/source/vault /path/to/target/vault --items themes plugins
```

### TUI Interface

```bash
python obsync_tui.py
```

The TUI interface provides an interactive way to:
- Select source and target vaults
- Preview the sync operation
- Perform dry runs
- Execute the sync with visual feedback

## Settings That Can Be Synced

- Core Settings Files:
  - appearance.json
  - app.json
  - core-plugins.json
  - community-plugins.json
  - hotkeys.json
- Directories:
  - plugins/
  - themes/
  - snippets/

## Safety Features

- Automatic backup creation before sync
- JSON validation to prevent corruption
- Dry-run mode for safety
- Keeps last 5 backups by default
- Detailed logging of all operations

## License

MIT License 
