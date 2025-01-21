# Developer Guide

This guide covers everything you need to know to develop ObsyncIt.

## Development Environment Setup

### 1. Basic Setup

```bash
# Clone repository
git clone https://github.com/yourusername/obsyncit.git
cd obsyncit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate    # Windows

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### 2. Development Tools

- **Code Quality**
  - black: Code formatting
  - isort: Import sorting
  - pylint: Static analysis
  - mypy: Type checking
  - ruff: Fast linting

- **Testing**
  - pytest: Test framework
  - pytest-cov: Coverage reporting
  - pytest-mock: Mocking support
  - pytest-asyncio: Async test support

- **Documentation**
  - sphinx: Documentation generator
  - mkdocs: Documentation site
  - pdoc: API documentation

## Code Organization

### 1. Package Structure

```
obsyncit/
├── obsyncit/           # Main package
│   ├── __init__.py
│   ├── main.py        # CLI entry point
│   ├── obsync_tui.py  # TUI interface
│   ├── sync.py       # Core sync logic
│   ├── backup.py     # Backup management
│   ├── vault.py      # Vault operations
│   ├── errors.py     # Error handling
│   ├── logger.py     # Logging setup
│   └── schemas/      # Data models
├── tests/            # Test suite
├── docs/            # Documentation
└── scripts/         # Development scripts
```

### 2. Module Responsibilities

1. **main.py**
   - CLI interface
   - Command processing
   - Argument parsing

2. **sync.py**
   - Core sync logic
   - File operations
   - Progress tracking

3. **backup.py**
   - Backup creation
   - Backup restoration
   - Rotation management

4. **vault.py**
   - Vault validation
   - Settings management
   - Directory operations

## Development Workflow

### 1. Feature Development

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement Changes**
   - Write tests first
   - Implement feature
   - Add documentation

3. **Code Quality**
   ```bash
   # Format code
   black obsyncit tests
   isort obsyncit tests

   # Run linters
   ruff check obsyncit tests
   pylint obsyncit tests
   mypy obsyncit
   ```

4. **Run Tests**
   ```bash
   # Run test suite
   pytest

   # With coverage
   pytest --cov=obsyncit
   ```

### 2. Code Review Process

1. **Pre-Review Checklist**
   - Tests pass
   - Coverage maintained
   - Documentation updated
   - Type hints complete
   - Code formatted

2. **Pull Request**
   - Clear description
   - Link related issues
   - Include test results
   - List breaking changes

3. **Review Response**
   - Address feedback
   - Update tests
   - Maintain documentation

## Testing

### 1. Test Organization

```
tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
├── conftest.py       # Test configuration
└── fixtures/         # Test data
```

### 2. Test Categories

1. **Unit Tests**
   ```python
   def test_vault_validation():
       vault = VaultManager("/path")
       assert vault.validate()
   ```

2. **Integration Tests**
   ```python
   def test_sync_operation():
       sync = SyncManager(source, target)
       result = sync.sync_settings()
       assert result.success
   ```

3. **Property Tests**
   ```python
   @given(st.text())
   def test_path_handling(path):
       vault = VaultManager(path)
       assert vault.path.is_absolute()
   ```

### 3. Testing Tools

1. **pytest Fixtures**
   ```python
   @pytest.fixture
   def sample_vault():
       return create_test_vault()
   ```

2. **Mocking**
   ```python
   @patch('obsyncit.vault.VaultManager')
   def test_sync(mock_vault):
       mock_vault.validate.return_value = True
       # Test logic here
   ```

3. **Coverage**
   ```bash
   pytest --cov=obsyncit --cov-report=html
   ```

## Documentation

### 1. Code Documentation

1. **Docstring Format**
   ```python
   def validate_vault(path: Path) -> bool:
       """Validate an Obsidian vault.
       
       Args:
           path: Path to the vault directory
           
       Returns:
           bool: True if valid, False otherwise
           
       Raises:
           VaultError: If validation fails
       """
       pass
   ```

2. **Type Hints**
   ```python
   from typing import Optional, List, Dict

   def process_vault(
       path: Path,
       options: Optional[Dict[str, str]] = None,
       depth: int = 3
   ) -> List[str]:
       pass
   ```

### 2. Project Documentation

1. **README.md**
   - Project overview
   - Quick start guide
   - Basic usage
   - Contributing guide

2. **API Documentation**
   - Class documentation
   - Method signatures
   - Usage examples
   - Type information

3. **User Guides**
   - Installation
   - Configuration
   - Advanced usage
   - Troubleshooting

## Error Handling

### 1. Exception Hierarchy

```python
class ObsyncError(Exception):
    """Base exception for all ObsyncIt errors."""
    pass

class ValidationError(ObsyncError):
    """Validation related errors."""
    pass

class SyncError(ObsyncError):
    """Synchronization related errors."""
    pass
```

### 2. Error Context

```python
try:
    vault.validate()
except ValidationError as e:
    logger.error(f"Validation failed: {e.context}")
    raise
```

### 3. Error Recovery

```python
def sync_with_retry(max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            perform_sync()
            break
        except TransientError:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * attempt)
```

## Performance Optimization

### 1. Profiling

```python
import cProfile

def profile_sync():
    profiler = cProfile.Profile()
    profiler.enable()
    perform_sync()
    profiler.disable()
    profiler.print_stats(sort='cumulative')
```

### 2. Memory Management

```python
def process_large_vault():
    with ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(process_chunk, chunk)
            for chunk in chunks
        ]
```

### 3. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_vault_info(path: str) -> Dict[str, Any]:
    return load_vault_info(path)
```

## Release Process

### 1. Version Management

```python
# Version in __init__.py
__version__ = "1.0.0"
```

### 2. Release Steps

1. **Update Version**
   ```bash
   bump2version patch  # or minor/major
   ```

2. **Update Changelog**
   ```markdown
   ## [1.0.0] - 2024-01-18
   ### Added
   - New feature X
   ### Fixed
   - Bug in Y
   ```

3. **Create Release**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

### 3. Distribution

1. **Build Package**
   ```bash
   python -m build
   ```

2. **Upload to PyPI**
   ```bash
   python -m twine upload dist/*
   ```

## Best Practices

### 1. Code Style

- Follow PEP 8
- Use type hints
- Write descriptive docstrings
- Keep functions focused

### 2. Git Practices

- Clear commit messages
- Regular small commits
- Feature branches
- Pull request workflow

### 3. Testing

- Write tests first
- Maintain coverage
- Test edge cases
- Use meaningful assertions

### 4. Documentation

- Keep docs updated
- Include examples
- Document breaking changes
- Update CHANGELOG