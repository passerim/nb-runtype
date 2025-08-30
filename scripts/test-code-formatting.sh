#!/bin/bash

# Script to apply black and isort formatting to code and notebooks

set -e  # Exit on any error

echo "=== Checking imports sorting with isort ==="
isort --check-only nb_runtype

echo "=== Checking Python code formatting with black ==="
black --check nb_runtype

echo "=== Checking imports sorting in notebooks with isort ==="
nbqa isort --check-only tests

echo "=== Checking notebooks formatting with black ==="
nbqa black --check tests

echo "=== Formatting check completed ==="
