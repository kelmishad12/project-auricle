#!/bin/sh
# Wrapper script to run Pylint properly with PYTHONPATH
# This prevents False-Positive Import-Errors when linting local directories.

VENV_PYTHON="./venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at ./venv"
    exit 1
fi

echo "Running Pylint..."
PYTHONPATH=$PWD $VENV_PYTHON -m pylint src/ server.py scripts/ --disable=C0114,C0115,C0116,W0511

exit $?
