#!/bin/bash

echo "================================================="
echo "Running Auto-Formatter (autopep8)..."
echo "================================================="

VENV_PYTHON="./venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at ./venv"
    exit 1
fi

$VENV_PYTHON -m autopep8 --in-place --recursive --aggressive src/ tests/ server.py test_live.py

echo "✅ Formatting complete!"
echo "Run './venv/bin/python -m pylint src/ server.py' to verify."
