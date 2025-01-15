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

## Schema Versioning

### Version Format
- Major.Minor.Patch (e.g., 1.0.0)
- Major: Breaking changes
- Minor: New features
- Patch: Bug fixes

### Version History
```json
{
    "1.0.0": {
        "released": "2024-01-01",
        "changes": [
            "Initial schema release"
        ]
    },
    "1.1.0": {
        "released": "2024-02-01",
        "changes": [
            "Added support for plugin-specific settings",
            "Extended theme configuration options"
        ]
    }
}
```

### Migration Guidelines

1. **Forward Migration**
   ```python
   from obsyncit.schemas.migrations import migrate_forward

   # Migrate from version 1.0.0 to latest
   new_settings = migrate_forward(old_settings, "1.0.0")
   ```

2. **Backward Migration**
   ```python
   from obsyncit.schemas.migrations import migrate_backward

   # Migrate to specific version
   old_settings = migrate_backward(new_settings, "1.0.0")
   ```

## Schema Format

Each schema follows the JSON Schema specification and includes:

1. **Properties**
   ```json
   {
       "type": "object",
       "properties": {
           "theme": {
               "type": "string",
               "enum": ["light", "dark", "custom"]
           },
           "fontSize": {
               "type": "integer",
               "minimum": 8,
               "maximum": 32
           }
       },
       "required": ["theme"]
   }
   ```

2. **Validation Rules**
   ```json
   {
       "type": "object",
       "properties": {
           "plugins": {
               "type": "array",
               "items": {
                   "type": "object",
                   "properties": {
                       "id": {"type": "string"},
                       "enabled": {"type": "boolean"}
                   },
                   "required": ["id", "enabled"]
               }
           }
       }
   }
   ```

3. **Documentation**
   ```json
   {
       "title": "Appearance Settings",
       "description": "Controls the visual appearance of Obsidian",
       "examples": [
           {
               "theme": "dark",
               "fontSize": 14
           }
       ]
   }
   ```

## Validation Error Examples

### Common Errors

1. **Missing Required Field**
   ```python
   try:
       validate_settings(settings)
   except ValidationError as e:
       # Error: {'theme': ['required field']}
       print(e.schema_errors)
   ```

2. **Invalid Type**
   ```python
   # Error: fontSize must be integer
   {
       "theme": "dark",
       "fontSize": "14"  # Should be integer
   }
   ```

3. **Enum Violation**
   ```python
   # Error: theme must be one of ['light', 'dark', 'custom']
   {
       "theme": "blue"
   }
   ```

### Error Handling

```python
from obsyncit.schemas import validate_settings
from obsyncit.errors import ValidationError

def handle_validation_error(error: ValidationError):
    """Handle validation errors with user-friendly messages."""
    messages = []
    for field, errors in error.schema_errors.items():
        for err in errors:
            messages.append(f"{field}: {err}")
    return "\n".join(messages)
```

## Custom Schema Extensions

### Adding New Properties

1. **Create Extension Schema**
   ```python
   # custom_schema.py
   from obsyncit.schemas.base import BaseSchema

   class CustomSchema(BaseSchema):
       custom_field: str
       custom_setting: bool = True
   ```

2. **Register Extension**
   ```python
   from obsyncit.schemas import register_extension

   register_extension("custom", CustomSchema)
   ```

### Plugin-Specific Extensions

1. **Define Plugin Schema**
   ```python
   # plugin_schema.py
   from pydantic import BaseModel

   class PluginSettings(BaseModel):
       enabled: bool = True
       config: dict = {}
   ```

2. **Use in Validation**
   ```python
   from obsyncit.schemas import validate_plugin_settings

   validate_plugin_settings("plugin_name", settings)
   ```

## Development

When modifying schemas:

1. Follow JSON Schema best practices
   ```json
   {
       "$schema": "http://json-schema.org/draft-07/schema#",
       "type": "object",
       "additionalProperties": false
   }
   ```

2. Update corresponding tests
   ```python
   def test_schema_validation():
       assert validate_settings(valid_settings)
       with pytest.raises(ValidationError):
           validate_settings(invalid_settings)
   ```

3. Document changes
   ```python
   """
   Version: 1.1.0
   Changes:
   - Added support for custom themes
   - Extended plugin configuration options
   """
   ```

4. Validate against real settings files
   ```python
   def test_real_settings():
       for settings_file in get_test_settings():
           assert validate_settings(settings_file)
   ```
