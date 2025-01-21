# Technical Specification

## System Overview

ObsyncIt is a Python-based tool designed to synchronize settings between multiple Obsidian vaults. Its primary purpose is to maintain consistency across different Obsidian installations by synchronizing themes, plugins, snippets, and configurations. The system comprises several key components:

- **Core Synchronization Engine**: Manages the synchronization of settings files, plugins, themes, and configurations.
- **Configuration Management**: Handles loading, validating, and saving configuration files.
- **User Interface**: Provides both CLI and TUI interactions for users to manage synchronization tasks.
- **Logging and Monitoring**: Utilizes advanced logging to track operations and errors.
- **Backup System**: Automatically creates backups before performing sync operations and allows restoration.

## Core Functionality

### Synchronization of Core Settings Files

- **Files**: `appearance.json`, `app.json`
- **Functions**:
  - `sync_core_settings(source_vault: str, target_vault: str) -> None`: Synchronizes core settings files between source and target vaults.
  - `load_settings(vault_path: str, file_name: str) -> dict`: Loads settings from a specified file in the vault.
  - `save_settings(vault_path: str, file_name: str, settings: dict) -> None`: Saves settings to a specified file in the vault.

### Management of Community Plugins and Configurations

- **Functions**:
  - `sync_plugins(source_vault: str, target_vault: str) -> None`: Synchronizes community plugins and their configurations.
  - `get_plugin_configs(vault_path: str) -> dict`: Retrieves plugin configurations from the vault.
  - `apply_plugin_configs(vault_path: str, configs: dict) -> None`: Applies plugin configurations to the vault.

### Sync of Custom Themes and CSS Snippets

- **Functions**:
  - `sync_themes(source_vault: str, target_vault: str) -> None`: Synchronizes custom themes and CSS snippets.
  - `get_theme_files(vault_path: str) -> List[str]`: Retrieves theme files from the vault.
  - `copy_theme_files(source_path: str, target_path: str) -> None`: Copies theme files from source to target vault.

### Backup Functionality

- **Functions**:
  - `create_backup(vault_path: str) -> str`: Creates a backup of the vault and returns the backup path.
  - `restore_backup(backup_path: str, target_vault: str) -> None`: Restores the vault from a backup.

### JSON Schema Validation

- **Functions**:
  - `validate_settings(settings: dict, schema: dict) -> bool`: Validates settings against a JSON schema.
  - `load_schema(schema_path: str) -> dict`: Loads a JSON schema from a file.

### CLI and TUI Interactions

- **Modules**:
  - `cli`: Command-line interface for automated operations.
  - `tui`: Terminal User Interface for manual operations.
- **Functions**:
  - `cli.run_sync() -> None`: Executes synchronization from the CLI.
  - `tui.run_sync() -> None`: Executes synchronization from the TUI.

### Automatic Vault Discovery and Validation

- **Functions**:
  - `discover_vaults() -> List[str]`: Discovers all Obsidian vaults on the system.
  - `validate_vault(vault_path: str) -> bool`: Validates if a path is a valid Obsidian vault.

### Selective Syncing of Specific Settings

- **Functions**:
  - `sync_selective(source_vault: str, target_vault: str, settings: List[str]) -> None`: Synchronizes only specified settings.

### Backup Restoration Capabilities

- **Functions**:
  - `restore_from_backup(backup_path: str, target_vault: str) -> None`: Restores the target vault from a specified backup.

## Architecture

The system is structured to ensure seamless interaction between its components. Data flows as follows:

1. **Input**: User initiates a synchronization task via CLI or TUI.
2. **Processing**:
   - The system discovers and validates Obsidian vaults.
   - It creates automatic backups before any sync operation.
   - Core settings, plugins, themes, and configurations are loaded, validated, and synchronized between vaults.
3. **Output**:
   - Synchronized settings are saved to the target vault.
   - Detailed logs are generated for each operation.
   - Users receive feedback on the success or failure of the sync operation.
