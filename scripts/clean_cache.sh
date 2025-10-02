#!/bin/bash
echo "🧹 Cleaning project caches..."

# Remove Python bytecode caches
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.py[co]" -delete

# Remove common Python tool caches
rm -rf .pytest_cache
rm -rf .mypy_cache
rm -rf .ruff_cache
rm -rf .ipynb_checkpoints

# Remove build artifacts
rm -rf build dist *.egg-info

echo "✅ All caches cleaned."
