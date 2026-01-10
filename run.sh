#!/bin/bash
# Video Downloader Webapp Startup Script

echo "Starting Video Downloader Webapp..."
echo "Activating virtual environment..."

source instaloader_env/bin/activate

echo "Starting Flask app on http://localhost:5000"
python combined_app.py
