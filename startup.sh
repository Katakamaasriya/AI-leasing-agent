#!/bin/bash
# Azure Web App startup script
# This script sets up the Python path correctly for the Azure environment

# Determine the actual working directory (Azure extracts to temp directories)
if [ -d "/tmp" ]; then
    # Use the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    cd "$SCRIPT_DIR"
else
    cd /home/site/wwwroot
fi

# Add the current directory to Python path
export PYTHONPATH=$(pwd):$PYTHONPATH

# Execute the original startup command
exec streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8000