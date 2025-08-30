#!/bin/bash

# Script to check black and isort formatting to code and notebooks

set -e  # Exit on any error

echo "=== Sorting imports with isort ==="
isort nb_runtype

echo "=== Formatting Python code with black ==="
black nb_runtype

echo "=== Sorting imports in notebooks with isort ==="
nbqa isort tests

echo "=== Formatting notebooks with black ==="
nbqa black tests

echo "=== Formatting completed ==="
