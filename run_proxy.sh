#!/bin/bash
# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "python3 could not be found, please install Python."
    exit 1
fi

echo "Installing required packages..."
pip3 install flask requests gunicorn

echo "Starting proxy server with 4 workers..."
python3 run.py --workers 4
