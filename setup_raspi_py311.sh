#!/bin/bash
# Raspberry Pi 4 Setup Script - Conda Environment
# Auto-installs Miniconda and creates conda environment with Python 3.11

set -e

echo "========================================================================"
echo "Smart CCTV System - Raspberry Pi 4 Setup (Conda)"
echo "========================================================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if conda is installed
echo "[1/9] Checking for Conda..."

if ! command -v conda &> /dev/null; then
    echo -e "${YELLOW}Conda not found. Installing Miniconda...${NC}"
    echo ""
    
    # Download Miniconda for ARM64 (Raspberry Pi)
    echo "Downloading Miniconda installer..."
    wget -q --show-progress https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O miniconda_installer.sh
    
    # Install Miniconda
    echo "Installing Miniconda (this may take a few minutes)..."
    bash miniconda_installer.sh -b -p $HOME/miniconda3
    
    # Remove installer
    rm miniconda_installer.sh
    
    # Initialize conda
    echo "Initializing Conda..."
    $HOME/miniconda3/bin/conda init bash
    
    # Source bashrc to activate conda
    source $HOME/.bashrc
    
    echo -e "${GREEN}✓ Miniconda installed successfully${NC}"
else
    echo -e "${GREEN}✓ Conda found${NC}"
fi

# Make sure conda is in PATH
export PATH="$HOME/miniconda3/bin:$PATH"
source $HOME/miniconda3/etc/profile.d/conda.sh

echo ""

# Remove existing environment if it exists
echo "[2/9] Setting up Conda environment..."
if conda env list | grep -q "^face-recog "; then
    echo -e "${YELLOW}Removing existing 'face-recog' environment...${NC}"
    conda env remove -n face-recog -y
fi

# Create conda environment with Python 3.11
echo "Creating conda environment with Python 3.11..."
conda create -n face-recog python=3.11 -y

echo -e "${GREEN}✓ Conda environment created${NC}"
echo ""

# Activate conda environment
echo "[3/9] Activating conda environment..."
conda activate face-recog
echo -e "${GREEN}✓ Conda environment activated${NC}"
echo ""

# Upgrade pip and setuptools
echo "[4/9] Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install dependencies
echo "[5/9] Installing Python dependencies..."
echo "This may take 15-30 minutes on Raspberry Pi..."
echo ""

# Install numpy first
echo "Installing numpy..."
pip install numpy==1.24.4

# Install dlib
echo "Installing dlib (this takes the longest)..."
pip install dlib==19.24.6

# Install opencv
echo "Installing opencv..."
pip install opencv-python==4.10.0

# Install face recognition
echo "Installing face-recognition..."
pip install face-recognition==1.3.0
pip install face_recognition_models==0.3.0

# Install web framework
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

# Create directories
echo "[6/9] Creating project directories..."
mkdir -p known alerts static templates logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Generate SSL certificates
echo "[7/9] Generating SSL certificates..."
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
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
echo "IMPORTANT: Restart your terminal or run:"
echo "  source ~/.bashrc"
echo ""
echo "Then start the server:"
echo "  conda activate face-recog"
echo "  python3 run_server_https.py"
echo ""
echo "Or use the quick start script:"
echo "  ./start_server_raspi.sh"
echo ""
echo "Access at: https://$(hostname -I | awk '{print $1}'):8000"
echo "========================================================================"
