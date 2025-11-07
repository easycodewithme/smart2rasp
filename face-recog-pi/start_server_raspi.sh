#!/bin/bash
# Quick start script for Raspberry Pi

set -e

echo "========================================================================"
echo "Starting Smart CCTV System on Raspberry Pi"
echo "========================================================================"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found!"
    echo "Run ./setup_raspi.sh first"
    exit 1
fi

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "Server will be accessible at:"
echo "  - Local: https://localhost:8000"
echo "  - Network: https://$LOCAL_IP:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================================================"
echo ""

# Start HTTPS server
python3 run_server_https.py
