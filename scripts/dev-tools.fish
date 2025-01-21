#!/usr/bin/env fish
# Development helper script for ObsyncIt

# Colors for output
set -l RED '\033[0;31m'
set -l GREEN '\033[0;32m'
set -l YELLOW '\033[1;33m'
set -l NC '\033[0m' # No Color

# Print help message
function show_help
    echo "Development helper script for ObsyncIt"
    echo
    echo "Usage: "(status filename)" [command]"
    echo
    echo "Commands:"
    echo "  setup      - Set up development environment"
    echo "  test       - Run test suite"
    echo "  lint       - Run linters"
    echo "  type       - Run type checker"
    echo "  format     - Format code"
    echo "  clean      - Clean build artifacts"
    echo "  docs       - Build documentation"
    echo "  all        - Run all checks"
    echo "  help       - Show this help message"
    echo
end

# Set up development environment
function setup
    echo -e "$GREEN"Setting up development environment..."$NC"
    python -m venv .venv
    source .venv/bin/activate.fish
    pip install -e ".[dev]"
    pre-commit install
    echo -e "$GREEN"Development environment ready!"$NC"
end

# Run test suite
function run_tests
    echo -e "$GREEN"Running tests..."$NC"
    pytest --cov=obsyncit
    echo -e "$GREEN"Tests complete!"$NC"
end

# Run linters
function run_lint
    echo -e "$GREEN"Running linters..."$NC"
    ruff check obsyncit tests
    pylint obsyncit tests
    echo -e "$GREEN"Linting complete!"$NC"
end

# Run type checker
function run_type_check
    echo -e "$GREEN"Running type checker..."$NC"
    mypy obsyncit
    echo -e "$GREEN"Type checking complete!"$NC"
end

# Format code
function format_code
    echo -e "$GREEN"Formatting code..."$NC"
    black obsyncit tests
    isort obsyncit tests
    echo -e "$GREEN"Formatting complete!"$NC"
end

# Clean build artifacts
function clean
    echo -e "$GREEN"Cleaning build artifacts..."$NC"
    find . -type d -name "__pycache__" -exec rm -r {} +
    find . -type d -name "*.egg-info" -exec rm -r {} +
    find . -type d -name ".eggs" -exec rm -r {} +
    find . -type d -name ".pytest_cache" -exec rm -r {} +
    find . -type d -name ".coverage" -exec rm -r {} +
    find . -type d -name "htmlcov" -exec rm -r {} +
    find . -type d -name ".tox" -exec rm -r {} +
    find . -type d -name "build" -exec rm -r {} +
    find . -type d -name "dist" -exec rm -r {} +
    echo -e "$GREEN"Cleaning complete!"$NC"
end

# Build documentation
function build_docs
    echo -e "$GREEN"Building documentation..."$NC"
    cd docs
    sphinx-build -b html source build/html
    echo -e "$GREEN"Documentation built!"$NC"
end

# Run all checks
function run_all
    format_code
    run_lint
    run_type_check
    run_tests
    build_docs
    echo -e "$GREEN"All checks complete!"$NC"
end

# Main script logic
set -l command $argv[1]
if test -z "$command"
    set command "help"
end

switch $command
    case "setup"
        setup
    case "test"
        run_tests
    case "lint"
        run_lint
    case "type"
        run_type_check
    case "format"
        format_code
    case "clean"
        clean
    case "docs"
        build_docs
    case "all"
        run_all
    case "help"
        show_help
    case "*"
        echo -e "$RED"Unknown command: $command"$NC"
        show_help
        exit 1
end 