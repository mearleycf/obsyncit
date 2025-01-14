# ObsyncIt Test Suite

This directory contains the test suite for the ObsyncIt tool.

## Test Structure

### Unit Tests

- `test_json_validation.py`: Tests for JSON schema validation
  - Validates settings file formats
  - Tests error handling for invalid JSON
  - Ensures schema compliance

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

## Test Dependencies

Required packages for testing (installed with `pip install -e ".[dev]"`):
- pytest
- pytest-cov
- pytest-mock
- pytest-asyncio 