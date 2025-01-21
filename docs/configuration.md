# Configuration Guide

This guide explains all configuration options available in ObsyncIt.

## Configuration File Location

The configuration file (config.toml) should be placed in:

- Linux/macOS: `~/.config/obsyncit/config.toml`
- Windows: `%APPDATA%\obsyncit\config.toml`

## Configuration Sections

### 1. Sync Settings

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
max_depth = 3
default_vault = ""
```

### 2. Backup Settings

```toml
[backup]
# Backup settings
enabled = true
max_backups = 5
backup_dir = ".backups"
compression = true
dry_run = false
ignore_errors = false
backup_on_sync = true
```

### 3. Logging Settings

```toml
[logging]
# Logging configuration
level = "INFO"
format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
log_dir = "logs"
rotation = "1 week"
retention = "1 month"
compression = "zip"
```

### 4. Path Settings

```toml
[paths]
# Default search paths for vault discovery
search_paths = [
    "~/Documents",
    "~/Dropbox",
    "~/iCloudDrive"
]
```

## Configuration Options Explained

### Sync Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| core_settings | bool | true | Sync core Obsidian settings |
| core_plugins | bool | true | Sync built-in plugin settings |
| community_plugins | bool | true | Sync community plugin settings |
| themes | bool | true | Sync custom themes |
| snippets | bool | true | Sync CSS snippets |
| dry_run | bool | false | Preview changes without applying |
| ignore_errors | bool | false | Continue on non-critical errors |
| max_depth | int | 3 | Maximum directory depth for vault discovery |
| default_vault | string | "" | Default source vault path |

### Backup Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| enabled | bool | true | Enable automatic backups |
| max_backups | int | 5 | Number of backups to keep |
| backup_dir | string | ".backups" | Backup directory name |
| compression | bool | true | Compress backups |
| dry_run | bool | false | Preview backup operations |
| ignore_errors | bool | false | Continue on backup errors |
| backup_on_sync | bool | true | Create backup before sync |

### Logging Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| level | string | "INFO" | Log level |
| format | string | "{time} \| {level} \| {message}" | Log format |
| log_dir | string | "logs" | Log directory |
| rotation | string | "1 week" | Log rotation interval |
| retention | string | "1 month" | Log retention period |
| compression | string | "zip" | Log compression format |

### Path Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| search_paths | list | ["~/Documents"] | Paths to search for vaults |

## Example Configurations

### Minimal Configuration

```toml
[sync]
core_settings = true
community_plugins = true

[backup]
enabled = true
max_backups = 3

[logging]
level = "INFO"
```

### Full Configuration

```toml
[sync]
core_settings = true
core_plugins = true
community_plugins = true
themes = true
snippets = true
dry_run = false
ignore_errors = false
max_depth = 3
default_vault = "~/Documents/MainVault"

[backup]
enabled = true
max_backups = 5
backup_dir = ".backups"
compression = true
dry_run = false
ignore_errors = false
backup_on_sync = true

[logging]
level = "INFO"
format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
log_dir = "logs"
rotation = "1 week"
retention = "1 month"
compression = "zip"

[paths]
search_paths = [
    "~/Documents",
    "~/Dropbox/Obsidian",
    "~/iCloudDrive/Obsidian"
]
```

## Environment Variables

ObsyncIt also supports configuration through environment variables:

- `OBSYNCIT_CONFIG`: Path to config file
- `OBSYNCIT_LOG_LEVEL`: Override log level
- `OBSYNCIT_DEFAULT_VAULT`: Default vault path

## Validation

The configuration is validated against a schema to ensure:

1. Required fields are present
2. Values are of correct type
3. Paths are valid
4. Settings are consistent

## Reloading Configuration

Configuration changes are detected and reloaded:

- When starting a new sync operation
- When explicitly requested via CLI/TUI
- When configuration file changes (if watching enabled)