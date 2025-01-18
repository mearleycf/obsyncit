# ObsyncIt Test Suite

This directory contains the comprehensive test suite for ObsyncIt, ensuring reliability and correctness of all operations.

## Test Categories

### Unit Tests

- `test_vault.py`: Vault Management Tests
  - Vault structure validation
  - Settings file handling
  - Path resolution
  - Plugin management

- `test_sync.py`: Sync Operation Tests
  - File synchronization
  - Directory handling
  - Progress reporting
  - Error recovery
  - Atomic operations

- `test_backup.py`: Backup System Tests
  - Backup creation
  - Restoration process
  - Rotation policies
  - Compression handling
  - Error recovery

- `test_vault_discovery.py`: Discovery Tests
  - Platform-specific paths
  - Vault detection
  - Metadata extraction
  - Cache management

### Integration Tests

- `test_cli.py`: CLI Integration
  - Command parsing
  - Error handling
  - Output formatting
  - Exit codes
  - Config loading

- `test_tui.py`: TUI Integration
  - Screen rendering
  - User input handling
  - Progress display
  - Error presentation
  - Navigation

### System Tests

- `test_e2e.py`: End-to-End Tests
  - Complete sync workflows
  - Real vault operations
  - Error scenarios
  - Recovery procedures

### Performance Tests

- `test_perf.py`: Performance Testing
  - Large vault handling
  - Memory usage
  - CPU utilization
  - IO operations

## Coverage Goals

The project maintains strict test coverage requirements:

### Core Functionality (100%)

- Sync operations
- Backup management
- Vault operations
- Schema validation

### Supporting Features (90%+)

- CLI interface
- TUI components
- Discovery system
- Logging system

### Error Handling (100%)

- Custom exceptions
- Recovery procedures
- User feedback
- System state

## Test Configuration

### pytest Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=obsyncit --cov-report=html --cov-report=term-missing
```

### Coverage Configuration

```ini
[coverage:run]
branch = True
source = obsyncit

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
```

## Test Data Management

### Fixtures

```python
@pytest.fixture
def sample_vault(tmp_path):
    """Create a sample vault with test data."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    return VaultFixture(vault)

@pytest.fixture
def mock_settings():
    """Provide mock settings data."""
    return {
        "appearance.json": {"theme": "default"},
        "app.json": {"spellcheck": True}
    }
```

### Test Utilities

```python
class VaultFixture:
    """Helper class for vault testing."""
    def __init__(self, path):
        self.path = path
        self.settings = {}
    
    def add_plugin(self, plugin_id, version="1.0.0"):
        """Add a test plugin to the vault."""
        pass

    def verify_state(self):
        """Verify vault integrity."""
        pass
```

## Running Tests

### Basic Test Run

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_sync.py

# Run specific test class
pytest tests/test_sync.py::TestSyncManager

# Run specific test
pytest tests/test_sync.py::TestSyncManager::test_sync_files
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov-report=html

# Show missing lines
pytest --cov-report=term-missing

# Generate XML report for CI
pytest --cov-report=xml
```

## Writing Tests

### Test Structure

```python
class TestSyncManager:
    """Test suite for sync operations."""
    
    def test_sync_files(self, sample_vault):
        """Test basic file synchronization."""
        manager = SyncManager()
        result = manager.sync_files(
            source=sample_vault.path,
            target=sample_vault.create_target()
        )
        assert result.success
        assert result.files_synced > 0
```

### Mocking Guidelines

```python
@pytest.fixture
def mock_fs(mocker):
    """Mock filesystem operations."""
    return mocker.patch('obsyncit.sync.os.path')

def test_with_mock(mock_fs):
    """Test using mocked filesystem."""
    mock_fs.exists.return_value = True
    # Test implementation
```

## CI Integration

### GitHub Actions

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Run tests
      run: |
        pip install -e ".[dev]"
        pytest
```

## Contributing

When adding or modifying tests:

1. **Coverage**
   - Maintain coverage goals
   - Test edge cases
   - Include error scenarios
   - Test async operations

2. **Documentation**
   - Document fixtures
   - Explain test purpose
   - Update README
   - Add examples

3. **Performance**
   - Use appropriate fixtures
   - Clean up resources
   - Mock heavy operations
   - Profile test runs
