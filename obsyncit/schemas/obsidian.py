"""
JSON schemas for Obsidian settings files.
"""

from typing import Any, Dict

# Schema for appearance.json
APPEARANCE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "accentColor": {"type": "string"},
        "theme": {"type": "string"},
        "cssTheme": {"type": "string"},
        "baseFontSize": {"type": "integer"},
        "translucency": {"type": "boolean"},
        "nativeMenus": {"type": "boolean"},
        "showViewHeader": {"type": "boolean"},
        "baseFontSizeAction": {"type": "integer"}
    },
    "additionalProperties": True  # Allow unknown properties for forward compatibility
}

# Schema for app.json
APP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "attachmentFolderPath": {"type": "string"},
        "alwaysUpdateLinks": {"type": "boolean"},
        "showUnsupportedFiles": {"type": "boolean"},
        "strictLineBreaks": {"type": "boolean"},
        "showFrontmatter": {"type": "boolean"},
        "defaultViewMode": {"type": "string", "enum": ["source", "preview"]},
        "promptDelete": {"type": "boolean"},
        "readableLineLength": {"type": "boolean"},
        "useMarkdownLinks": {"type": "boolean"},
        "newLinkFormat": {"type": "string", "enum": ["shortest", "relative", "absolute"]},
        "useTab": {"type": "boolean"},
        "tabSize": {"type": "integer"}
    },
    "additionalProperties": True
}

# Schema for core-plugins.json
CORE_PLUGINS_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {"type": "string"},
    "uniqueItems": True
}

# Schema for community-plugins.json
COMMUNITY_PLUGINS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "installed": {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True
        },
        "enabled": {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True
        }
    },
    "required": ["installed", "enabled"],
    "additionalProperties": True
}

# Schema for hotkeys.json
HOTKEYS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "patternProperties": {
        "^.*$": {  # Any property name
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "modifiers": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["Mod", "Shift", "Alt", "Ctrl"]},
                        "uniqueItems": True
                    },
                    "key": {"type": "string"}
                },
                "required": ["modifiers", "key"]
            }
        }
    },
    "additionalProperties": True
}

# Map of file names to their schemas
SCHEMA_MAP: Dict[str, Dict[str, Any]] = {
    "appearance.json": APPEARANCE_SCHEMA,
    "app.json": APP_SCHEMA,
    "core-plugins.json": CORE_PLUGINS_SCHEMA,
    "community-plugins.json": COMMUNITY_PLUGINS_SCHEMA,
    "hotkeys.json": HOTKEYS_SCHEMA
}
