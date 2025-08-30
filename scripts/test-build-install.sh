#!/bin/bash

# Script to locally test build and install the nb-runtype package

set -e  # Exit on any error

echo "=== Building the package ==="
python -m build

echo "=== Creating test virtual environment ==="
python -m venv test_env

echo "=== Activating test environment and installing package ==="
source test_env/bin/activate
pip install dist/*.whl

echo "=== Testing imports ==="
python -c "from nb_runtype import enable_runtype, disable_runtype, no_runtype, is_runtype_enabled, get_runtype_config, RuntypeError; print('All imports successful')"

echo "=== Deactivating environment ==="
deactivate

echo "=== Cleaning up ==="
rm -rf test_env

echo "=== Build and install test completed successfully ==="
