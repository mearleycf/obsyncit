# Installation Guide

This guide covers the installation process for ObsyncIt.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- git (for cloning the repository)

## Installation Methods

### 1. From Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/obsyncit.git
cd obsyncit

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate    # On Windows

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### 2. Using pip (Coming Soon)

```bash
pip install obsyncit
```

## Verifying Installation

After installation, verify that ObsyncIt is working correctly:

```bash
# Check CLI version
obsyncit --version

# List available commands
obsyncit --help
```

## Configuration

1. Create configuration directory:
   ```bash
   # Linux/macOS
   mkdir -p ~/.config/obsyncit

   # Windows
   mkdir %APPDATA%\obsyncit
   ```

2. Create configuration file:
   ```bash
   # Linux/macOS
   cp config.sample.toml ~/.config/obsyncit/config.toml

   # Windows
   copy config.sample.toml %APPDATA%\obsyncit\config.toml
   ```

3. Edit the configuration file to match your needs.

## Development Setup

For development, install additional tools:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest
```

## Troubleshooting

### Common Issues

1. **Python Version Error**
   ```
   Solution: Ensure you're using Python 3.8 or higher
   ```

2. **Missing Dependencies**
   ```
   Solution: Run pip install -e ".[dev]" again
   ```

3. **Permission Issues**
   ```
   Solution: Use sudo/admin rights or --user flag
   ```

### Getting Help

If you encounter issues:

1. Check the [Issues](../../issues) section
2. Review error logs in:
   - Linux/macOS: `~/.obsyncit/logs/`
   - Windows: `%APPDATA%\obsyncit\logs\`
3. Run with debug logging:
   ```bash
   obsyncit --debug ...
   ```