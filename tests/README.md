# ObsyncIt Test Suite

This directory contains the test suite for the ObsyncIt tool.

## Test Categories

### Unit Tests
- `test_json_validation.py`: Tests for JSON schema validation
  - Validates settings file formats
  - Tests error handling for invalid JSON
  - Ensures schema compliance

### Integration Tests
- `test_sync.py`: End-to-end sync tests
  - Tests complete sync workflows
  - Validates file operations
  - Tests backup integration

### System Tests
- `test_cli.py`: Command-line interface tests
  - Tests argument parsing
  - Tests command execution
  - Tests exit codes

### UI Tests
- `test_tui.py`: Terminal UI tests
  - Tests user interactions
  - Tests display formatting
  - Tests progress indicators

## Coverage Goals

The project maintains strict test coverage requirements:
- Overall coverage: 90%+ (current: 90%)
- Critical paths: 100%
  - Sync operations
  - Backup operations
  - Schema validation
- UI components: 85%+
- Error handlers: 100%

Run coverage reports:
```bash
pytest --cov=obsyncit --cov-report=html
```

## Test Data Management

### Fixtures
- Use `conftest.py` for shared fixtures
- Keep test data in `tests/data/`
- Use temporary directories for file operations
- Clean up test artifacts

Example:
```python
@pytest.fixture
def sample_vault(tmp_path):
    """Create a sample vault with test data."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    return vault_path
```

### Mocking Guidelines

1. **External Dependencies**
   ```python
   @pytest.fixture
   def mock_file_system(mocker):
       return mocker.patch('obsyncit.sync.os.path')
   ```

2. **Time-Dependent Tests**
   ```python
   @pytest.fixture
   def mock_time(mocker):
       return mocker.patch('obsyncit.backup.time.time')
   ```

3. **Network Operations**
   ```python
   @pytest.fixture
   def mock_network(mocker):
       return mocker.patch('obsyncit.sync.requests.get')
   ```

### Test Organization
- Group related tests in classes
- Use descriptive test names
- Follow arrange-act-assert pattern

### Test Configuration

The test suite uses pytest and is configured in `pytest.ini` with the following features:
- Verbose output
- Code coverage reporting
- HTML coverage reports
- Logging configuration

## Running Tests

### Basic Test Run
```bash
pytest
```

### With Coverage
```bash
pytest --cov=obsyncit --cov-report=html
```

### Specific Test Files
```bash
pytest tests/test_json_validation.py
```

## Writing Tests

1. **Naming Conventions**
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test functions: `test_*`

2. **Test Organization**
   - Group related tests in classes
   - Use descriptive test names
   - Follow arrange-act-assert pattern

3. **Fixtures**
   - Use pytest fixtures for setup/teardown
   - Share common test data
   - Mock external dependencies

4. **Coverage**
   - Aim for high test coverage
   - Test edge cases
   - Include error scenarios

## Integration Test Setup

1. **Environment Setup**
   ```bash
   # Create test environment
   python -m venv test_env
   source test_env/bin/activate
   pip install -e ".[dev]"
   ```

2. **Test Data**
   ```bash
   # Generate test vaults
   python tests/utils/generate_test_data.py
   ```

3. **Run Integration Tests**
   ```bash
   pytest tests/integration/
   ```

## Test Dependencies

Required packages for testing (installed with `pip install -e ".[dev]"`):
- pytest
- pytest-cov
- pytest-mock
- pytest-asyncio
