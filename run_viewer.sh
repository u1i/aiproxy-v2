#!/bin/bash
if ! command -v python3 &> /dev/null; then
  echo "python3 required."
  exit 1
fi

echo "Starting Log Viewer on port 5002..."
python3 viewer.py
