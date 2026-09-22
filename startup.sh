#!/bin/bash
# Azure Web App startup script
# This script sets up the Python path correctly for the Azure environment

# Set the working directory to the project root
cd /home/site/wwwroot

# Add the project root to Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Execute the original startup command
exec streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8000