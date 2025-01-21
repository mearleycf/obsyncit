# Troubleshooting Guide

This guide helps you diagnose and fix common issues with ObsyncIt.

## Common Issues

### 1. Vault Discovery Problems

#### Vault Not Found
```
Error: No valid vaults found in search path
```

**Possible Causes:**
- Incorrect search path
- Missing .obsidian directory
- Insufficient search depth

**Solutions:**
1. Check path exists:
   ```bash
   ls /your/search/path
   ```
2. Verify .obsidian directory:
   ```bash
   ls /your/vault/.obsidian
   ```
3. Increase search depth:
   ```bash
   obsyncit discover --depth 5
   ```

### 2. Sync Failures

#### Permission Errors
```
Error: Permission denied accessing [file]
```

**Solutions:**
1. Check file ownership:
   ```bash
   ls -l /path/to/file
   ```
2. Fix permissions:
   ```bash
   chmod -R u+rw /path/to/vault
   ```

#### Invalid JSON
```
Error: Invalid JSON in settings file
```

**Solutions:**
1. Validate file:
   ```bash
   obsyncit validate /path/to/file
   ```
2. Check file format:
   ```bash
   cat /path/to/file | python -m json.tool
   ```

### 3. Backup Issues

#### Backup Creation Failed
```
Error: Failed to create backup
```

**Possible Causes:**
- Insufficient disk space
- Permission issues
- Invalid backup directory

**Solutions:**
1. Check disk space:
   ```bash
   df -h
   ```
2. Verify backup directory:
   ```bash
   ls -la /path/to/backups
   ```
3. Clean old backups:
   ```bash
   obsyncit backup clean
   ```

### 4. Configuration Problems

#### Config Not Found
```
Error: No configuration file found
```

**Solutions:**
1. Create default config:
   ```bash
   obsyncit config init
   ```
2. Copy sample config:
   ```bash
   cp config.sample.toml ~/.config/obsyncit/config.toml
   ```

#### Invalid Configuration
```
Error: Invalid configuration value [value]
```

**Solutions:**
1. Validate config:
   ```bash
   obsyncit config validate
   ```
2. Reset to defaults:
   ```bash
   obsyncit config reset
   ```

## Diagnostic Tools

### 1. Debug Logging

Enable detailed logging:
```bash
obsyncit --debug --log-file debug.log
```

### 2. Validation Tools

1. **Config Validation**
   ```bash
   obsyncit config validate
   ```

2. **Vault Validation**
   ```bash
   obsyncit vault validate /path/to/vault
   ```

3. **Settings Validation**
   ```bash
   obsyncit settings validate /path/to/settings.json
   ```

### 3. System Checks

1. **Environment Check**
   ```bash
   obsyncit doctor
   ```

2. **Permission Check**
   ```bash
   obsyncit check-permissions /path/to/vault
   ```

## Recovery Procedures

### 1. Restore from Backup

1. **List Available Backups**
   ```bash
   obsyncit backup list
   ```

2. **Restore Latest**
   ```bash
   obsyncit backup restore latest
   ```

3. **Restore Specific**
   ```bash
   obsyncit backup restore backup_20240118.zip
   ```

### 2. Reset to Defaults

1. **Reset Configuration**
   ```bash
   obsyncit config reset
   ```

2. **Clean Working Directory**
   ```bash
   obsyncit clean
   ```

## Logging

### 1. Log Locations

- Linux/macOS: `~/.obsyncit/logs/`
- Windows: `%APPDATA%\obsyncit\logs\`

### 2. Log Levels

1. **ERROR**: Critical issues
2. **WARNING**: Important but non-critical
3. **INFO**: General information
4. **DEBUG**: Detailed debugging

### 3. Log Analysis

1. **View Recent Logs**
   ```bash
   obsyncit logs show
   ```

2. **Search Logs**
   ```bash
   obsyncit logs search "error"
   ```

## Getting Help

### 1. Command Help

```bash
obsyncit --help
obsyncit [command] --help
```

### 2. Documentation

1. Online documentation:
   - GitHub Wiki
   - ReadTheDocs

2. Local documentation:
   ```bash
   obsyncit docs
   ```

### 3. Support

1. **Issue Tracker**
   - GitHub Issues
   - Bug reports
   - Feature requests

2. **Community**
   - GitHub Discussions
   - Community forums

## Prevention

### 1. Best Practices

1. **Regular Backups**
   ```bash
   obsyncit backup create --schedule daily
   ```

2. **Validation Checks**
   ```bash
   obsyncit validate --all
   ```

3. **Permission Management**
   ```bash
   obsyncit check-permissions
   ```

### 2. Monitoring

1. **Health Checks**
   ```bash
   obsyncit health
   ```

2. **Space Monitoring**
   ```bash
   obsyncit space-check
   ```

## System Requirements

### 1. Software

- Python 3.8+
- Required packages
- Operating system support

### 2. Hardware

- Disk space
- Memory requirements
- CPU requirements

### 3. Permissions

- File access
- Directory creation
- Configuration management