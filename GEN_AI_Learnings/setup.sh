#!/bin/bash

# Check if .venv directory exists
if [ ! -d ".venv" ]; then
    echo ".venv not found. Creating virtual environment..."
    python -m venv .venv
fi

# Activate the virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "Error: Virtual environment activation script not found."
    exit 1
fi

# Install dependencies
pip install -r requirements.github.txt
