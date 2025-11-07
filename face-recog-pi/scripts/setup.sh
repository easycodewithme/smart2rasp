#!/bin/bash
set -e

echo "Updating OS..."
sudo apt update && sudo apt upgrade -y

echo "Install system packages (may ask for sudo password)..."
sudo apt install -y build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev \
    python3-dev python3-pip libjpeg-dev libatlas-base-dev

echo "Increase swap to 1GB for dlib compile (temporary)..."
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile || true
sudo /etc/init.d/dphys-swapfile restart || true

echo "Install pip packages needed for building"
python3 -m pip install --upgrade pip setuptools wheel

echo "Install cmake via pip if missing"
python3 -m pip install cmake

echo "Try pip installing dlib (this will compile if wheel isn't available) - this may take 30-90 minutes on Pi4."
python3 -m pip install dlib || {
  echo "dlib pip install failed. You can try installing a prebuilt dlib wheel for your Pi OS and Python version, or allow the compile to continue manually."
  exit 1
}

echo "Install python requirements"
python3 -m pip install -r requirements.txt

echo "Reset swap back to default (optional but recommended after build)"
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=100/' /etc/dphys-swapfile || true
sudo /etc/init.d/dphys-swapfile restart || true

echo "Done. You can now run: python3 encode_known.py  and python3 face_recog_pi.py"
