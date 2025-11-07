#!/bin/bash
# Raspberry Pi 4 Setup Script for Smart CCTV System
# Auto-setup and start script

set -e

echo "========================================================================"
echo "Smart CCTV System - Raspberry Pi 4 Setup"
echo "========================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Python version
echo "[1/6] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 not found!${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Create virtual environment
echo "[2/6] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi
echo ""

# Activate virtual environment
echo "[3/6] Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo "[4/6] Upgrading pip..."
pip install --upgrade pip
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install dependencies
echo "[5/6] Installing Python dependencies..."
echo "This may take 15-30 minutes on Raspberry Pi..."
echo ""

# Install numpy first (required by many packages)
echo "Installing numpy..."
pip install numpy==1.24.4

# Install dlib dependencies and dlib
echo "Installing dlib (this takes the longest)..."
pip install dlib==19.24.6

# Install opencv
echo "Installing opencv..."
pip install opencv-python==4.10.0

# Install face recognition
echo "Installing face-recognition..."
pip install face-recognition==1.3.0
pip install face_recognition_models==0.3.0

# Install web framework dependencies
echo "Installing FastAPI and dependencies..."
pip install fastapi==0.121.0
pip install uvicorn==0.33.0
pip install python-multipart==0.0.20
pip install websockets==13.1
pip install aiofiles==24.1.0

# Install other dependencies
echo "Installing remaining dependencies..."
pip install cryptography==46.0.3
pip install pydantic==2.10.6
pip install pydantic_core==2.27.2
pip install starlette==0.44.0
pip install click==8.1.8
pip install h11==0.16.0
pip install httptools==0.6.4
pip install python-dotenv==1.0.1
pip install PyYAML==6.0.3
pip install pillow==10.4.0
pip install watchfiles==0.24.0
pip install cffi==1.17.1
pip install pycparser==2.23
pip install annotated-types==0.7.0
pip install anyio==4.5.2
pip install sniffio==1.3.1
pip install typing_extensions==4.13.2
pip install idna==3.11
pip install colorama==0.4.6

echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""

# Create necessary directories
echo "[6/6] Creating project directories..."
mkdir -p known
mkdir -p alerts
mkdir -p static
mkdir -p templates
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Generate SSL certificates if not exists
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "Generating SSL certificates..."
    python3 generate_ssl_cert.py
    echo -e "${GREEN}✓ SSL certificates generated${NC}"
else
    echo -e "${YELLOW}SSL certificates already exist${NC}"
fi
echo ""

echo "========================================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================================================"
echo ""
echo "To start the server:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start HTTPS server: python3 run_server_https.py"
echo ""
echo "Access the system:"
echo "  - Local: https://localhost:8000"
echo "  - Network: https://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "========================================================================"
