# ObsyncIt JSON Schemas

This directory contains JSON schemas used for validating Obsidian settings files.

## Schema Overview

The schemas define the structure and validation rules for various Obsidian settings files:

### Core Settings

- `appearance.json`: Theme and appearance settings
  - Color scheme
  - Font settings
  - Interface preferences

- `app.json`: Application settings
  - Startup behavior
  - Performance settings
  - General preferences

- `core-plugins.json`: Built-in plugin settings
  - Enabled/disabled status
  - Plugin-specific configurations

- `community-plugins.json`: Third-party plugin settings
  - Installed plugins
  - Plugin configurations
  - Version information

- `hotkeys.json`: Keyboard shortcuts
  - Command mappings
  - Custom shortcuts
  - Plugin hotkeys

## Schema Format

Each schema follows the JSON Schema specification and includes:

1. **Properties**
   - Field definitions
   - Data types
   - Required fields

2. **Validation Rules**
   - Value constraints
   - Pattern matching
   - Conditional requirements

3. **Documentation**
   - Field descriptions
   - Usage examples
   - Default values

## Usage

The schemas are used by the validation system to:

1. Validate settings files before sync
2. Ensure data integrity
3. Prevent corruption of settings
4. Provide helpful error messages

## Development

When modifying schemas:

1. Follow JSON Schema best practices
2. Update corresponding tests
3. Document changes
4. Validate against real settings files
