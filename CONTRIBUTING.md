# Contributing to ObsyncIt

First off, thank you for considering contributing to ObsyncIt! It's people like you that make ObsyncIt such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before submitting a bug report:
- Check the [issue tracker](../../issues) to see if the problem has already been reported
- If you're unable to find an open issue addressing the problem, open a new one

When submitting a bug report, include:
- A clear and descriptive title
- Exact steps to reproduce the behavior
- What you expected would happen
- What actually happened
- Log files (usually in ~/.obsyncit/logs/ or %APPDATA%\obsyncit\logs\)
- Python version and operating system

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:
- A clear and descriptive title
- Detailed explanation of the proposed functionality
- Any possible drawbacks
- Use cases for the enhancement

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows our style guidelines
6. Submit that pull request!

## Development Process

1. Clone the repository
```bash
git clone https://github.com/yourusername/obsyncit.git
cd obsyncit
```

2. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate    # On Windows
```

3. Install development dependencies
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks
```bash
pre-commit install
```

5. Make your changes and run tests
```bash
pytest
```

## Style Guidelines

### Python Style Guide

- Follow PEP 8
- Use type hints for all function parameters and return values
- Write comprehensive docstrings for all public functions and classes
- Organize imports:
  1. Standard library
  2. Third-party packages
  3. Local modules
- Use descriptive variable names
- Keep functions focused and small

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally
- Consider starting the commit message with an applicable emoji:
    * 🎨 `:art:` when improving the format/structure of the code
    * 🐛 `:bug:` when fixing a bug
    * ✨ `:sparkles:` when adding a new feature
    * 📝 `:memo:` when writing docs
    * ⚡️ `:zap:` when improving performance
    * 🔥 `:fire:` when removing code or files
    * 💚 `:green_heart:` when fixing the CI build
    * ✅ `:white_check_mark:` when adding tests
    * 🔒 `:lock:` when dealing with security
    * ⬆️ `:arrow_up:` when upgrading dependencies
    * ⬇️ `:arrow_down:` when downgrading dependencies

## Testing

We use pytest for testing. Run the full test suite with:
```bash
pytest
```

For coverage information:
```bash
pytest --cov=obsyncit
```

## Documentation

We use Google-style docstrings for Python documentation. Example:

```python
def validate_vault(path: str) -> bool:
    """Validates if a given path contains a valid Obsidian vault.

    Args:
        path: The filesystem path to check

    Returns:
        bool: True if the path contains a valid vault, False otherwise

    Raises:
        ValueError: If the path is empty or None
    """
```

## Need Help?

Feel free to reach out by:
1. Opening an issue
2. Starting a discussion
3. Commenting on relevant issues