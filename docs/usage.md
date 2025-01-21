# Usage Guide

This guide covers the basic and advanced usage of ObsyncIt.

## Basic Usage

### Command Line Interface (CLI)

1. **Basic Sync**
   ```bash
   obsyncit /path/to/source/vault /path/to/target/vault
   ```

2. **List Available Vaults**
   ```bash
   obsyncit --list-vaults
   ```

3. **Dry Run**
   ```bash
   obsyncit --dry-run /path/to/source/vault /path/to/target/vault
   ```

4. **Selective Sync**
   ```bash
   obsyncit --items themes,plugins /path/to/source/vault /path/to/target/vault
   ```

### Terminal User Interface (TUI)

1. **Launch TUI**
   ```bash
   obsyncit-tui
   ```

2. **Custom Search Path**
   ```bash
   obsyncit-tui --search-path ~/Documents
   ```

## Advanced Usage

### Sync Operations

1. **Sync Specific Items**
   ```bash
   # Sync only themes
   obsyncit --items themes /source/vault /target/vault

   # Sync plugins and snippets
   obsyncit --items plugins,snippets /source/vault /target/vault

   # Sync core settings only
   obsyncit --items core-settings /source/vault /target/vault
   ```

2. **Advanced Sync Options**
   ```bash
   # Ignore errors during sync
   obsyncit --ignore-errors /source/vault /target/vault

   # Custom backup directory
   obsyncit --backup-dir /path/to/backups /source/vault /target/vault

   # Skip backup creation
   obsyncit --no-backup /source/vault /target/vault
   ```

### Backup Management

1. **Create Backup**
   ```bash
   # Manual backup
   obsyncit backup create /path/to/vault

   # Compressed backup
   obsyncit backup create --compress /path/to/vault
   ```

2. **Restore from Backup**
   ```bash
   # Restore latest backup
   obsyncit backup restore /path/to/vault

   # Restore specific backup
   obsyncit backup restore --backup-file backup_20240118.zip /path/to/vault
   ```

3. **List Backups**
   ```bash
   # List all backups
   obsyncit backup list /path/to/vault

   # Show backup details
   obsyncit backup list --details /path/to/vault
   ```

### Vault Discovery

1. **Custom Search**
   ```bash
   # Search specific directory
   obsyncit discover --path ~/Documents

   # Set search depth
   obsyncit discover --path ~/Documents --depth 5
   ```

2. **Filter Vaults**
   ```bash
   # Show only vaults with plugins
   obsyncit discover --has-plugins

   # Show vaults modified recently
   obsyncit discover --modified-since "1 week ago"
   ```

### Logging and Debugging

1. **Debug Mode**
   ```bash
   # Enable debug logging
   obsyncit --debug /source/vault /target/vault

   # Save debug log to file
   obsyncit --debug --log-file debug.log /source/vault /target/vault
   ```

2. **Custom Log Level**
   ```bash
   # Set specific log level
   obsyncit --log-level INFO /source/vault /target/vault

   # Quiet mode
   obsyncit --quiet /source/vault /target/vault
   ```

## TUI Features

### Navigation

- **Arrow keys**: Navigate menus and lists
- **Enter**: Select/Confirm
- **Esc**: Back/Cancel
- **Tab**: Switch focus
- **q**: Quit application

### Vault Selection

1. **Source Vault**
   - Browse local vaults
   - Filter by name
   - Show vault details

2. **Target Vault**
   - Same navigation as source
   - Quick recent vault selection

### Sync Operations

1. **Item Selection**
   - Toggle individual items
   - Select/Deselect all
   - Filter items

2. **Operation Options**
   - Toggle dry run
   - Set backup options
   - Configure error handling

### Real-time Feedback

- Progress indicators
- Status messages
- Error notifications
- Operation summary

## Examples

### Common Workflows

1. **Initial Vault Setup**
   ```bash
   # List available vaults
   obsyncit --list-vaults

   # Dry run to check changes
   obsyncit --dry-run /source/vault /target/vault

   # Perform sync with backup
   obsyncit /source/vault /target/vault
   ```

2. **Regular Sync**
   ```bash
   # Quick sync with default options
   obsyncit /source/vault /target/vault

   # Sync specific items
   obsyncit --items plugins,themes /source/vault /target/vault
   ```

3. **Backup Management**
   ```bash
   # Create backup
   obsyncit backup create /path/to/vault

   # List backups
   obsyncit backup list /path/to/vault

   # Restore if needed
   obsyncit backup restore /path/to/vault
   ```

## Tips and Best Practices

1. **Before Syncing**
   - Run with --dry-run first
   - Check vault compatibility
   - Ensure sufficient space
   - Review selected items

2. **During Sync**
   - Monitor log output
   - Check error messages
   - Watch progress indicators
   - Don't modify vaults

3. **After Sync**
   - Verify sync completion
   - Check log files
   - Test vault functionality
   - Keep backups