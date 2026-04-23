#!/bin/bash
# Full test script for the configuration management module

set -e  # Stop on error

echo "=========================================="
echo "Configuration Management Module - Full Test"
echo "=========================================="
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated"
else
    echo "Warning: .venv not found, using system Python"
fi

echo ""
echo "1. Running unit tests..."
echo "------------------------------------------"
python -m pytest tests/test_config_management.py -v --tb=short || {
    echo "FAILED: unit tests"
    exit 1
}
echo "PASSED: unit tests"

echo ""
echo "2. Running scenario tests: permission checks..."
echo "------------------------------------------"
python tests/test_scenario_blacklist_permission.py || {
    echo "FAILED: permission scenario tests"
    exit 1
}
echo "PASSED: permission scenario tests"

echo ""
echo "3. Running scenario tests: hot-reload..."
echo "------------------------------------------"
python tests/test_scenario_hot_reload.py || {
    echo "FAILED: hot-reload scenario tests"
    exit 1
}
echo "PASSED: hot-reload scenario tests"

echo ""
echo "=========================================="
echo "All tests passed!"
echo "=========================================="
echo ""
echo "Module features fully implemented:"
echo "  - UartConfig dataclass"
echo "  - ConfigManager class"
echo "  - BlacklistManager updates"
echo "  - SerialManager integration"
echo ""
echo "Specification requirements fully satisfied:"
echo "  - Config file paths"
echo "  - Permission checks (600)"
echo "  - Error code handling (1005, 1008)"
echo "  - Hot-reload functionality"
echo "  - Blacklist management"
echo ""
