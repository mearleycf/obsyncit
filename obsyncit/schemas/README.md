# ObsyncIt JSON Schemas

This directory contains JSON schemas used for validating Obsidian settings files and ensuring data integrity during sync operations.

## Schema Overview

### Core Settings Schemas

- `appearance.json`: Theme and UI Settings
  ```json
  {
    "theme": "string",
    "cssTheme": "string",
    "baseFontSize": "number",
    "translucency": "boolean",
    "accentColor": "string"
  }
  ```

- `app.json`: Application Configuration
  ```json
  {
    "alwaysUpdateLinks": "boolean",
    "attachmentFolderPath": "string",
    "showLineNumber": "boolean",
    "spellcheck": "boolean",
    "vimMode": "boolean"
  }
  ```

- `community-plugins.json`: Plugin Management
  ```json
  {
    "installed": {
      "type": "array",
      "items": {
        "id": "string",
        "version": "string",
        "enabled": "boolean"
      }
    }
  }
  ```

- `hotkeys.json`: Keyboard Shortcuts
  ```json
  {
    "editor:toggle-bold": "string[]",
    "editor:toggle-italics": "string[]",
    "app:go-back": "string[]"
  }
  ```

### Validation Rules

1. **Type Validation**
   - Strict type checking
   - No implicit type conversion
   - Required field validation
   - Enum value validation

2. **Version Compatibility**
   - Schema version matching
   - Forward compatibility checks
   - Backward compatibility handling
   - Migration path validation

3. **Data Integrity**
   - Required field presence
   - Value range validation
   - Pattern matching
   - Cross-field dependencies

4. **Plugin Safety**
   - Plugin ID validation
   - Version format checking
   - Dependency validation
   - Configuration structure

## Schema Usage

### Validation Process

```python
from obsyncit.schemas import validate_settings

# Validate a settings file
result = validate_settings(
    file_path="appearance.json",
    schema_type="appearance"
)

if result.is_valid:
    print("Settings are valid")
else:
    print(f"Validation errors: {result.errors}")
```

### Custom Validators

```python
from obsyncit.schemas import register_validator

@register_validator("appearance")
def validate_theme(value: str) -> bool:
    """Validate theme name and format."""
    return bool(re.match(r'^[a-zA-Z0-9-]+$', value))
```

## Development Guidelines

1. **Schema Updates**
   - Maintain backward compatibility
   - Document changes
   - Update version numbers
   - Add migration paths

2. **Testing**
   - Test with real settings
   - Include edge cases
   - Validate error messages
   - Check performance

3. **Documentation**
   - Keep examples current
   - Document constraints
   - Explain validations
   - Note changes

## Error Messages

Schemas provide detailed error messages:

```python
{
    "path": ["appearance", "theme"],
    "message": "Invalid theme name format",
    "constraint": "pattern",
    "value": "invalid@theme"
}
```

## Contributing

When updating schemas:

1. **Version Control**
   - Update schema version
   - Document changes
   - Test migrations
   - Update docs

2. **Compatibility**
   - Check existing vaults
   - Test migrations
   - Validate formats
   - Update tests

3. **Performance**
   - Optimize patterns
   - Reduce complexity
   - Test large files
   - Profile validation
