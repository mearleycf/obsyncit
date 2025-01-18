#!/opt/homebrew/bin/fish

# Run all test commands sequentially
echo "Running all tests..."

# Main test suite
set timestamp (date +%Y-%m-%d_%H-%M)
pytest -v 2>&1 | tee logs/test_logs_$timestamp.log.txt

# Individual test files
set test_files backup cli errors json_validation logger sync tui vault_discovery

for test_type in $test_files
    echo "Running $test_type tests..."
    set timestamp (date +%Y-%m-%d_%H-%M)
    pytest -v tests/test_$test_type.py 2>&1 | tee logs/test_logs_$timestamp"_"$test_type.log.txt
end

# Archive all logs at the end
python logs/archive_logs.py

echo "All tests completed!" 