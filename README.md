# smart2rasp

Smart2Rasp is a Raspberry Pi focused project that provides a small server and supporting code for running smart/IoT and computer-vision (face recognition) workloads on Raspberry Pi devices. The repository contains a Python server, a setup script targeted at Python 3.11, and a dedicated face recognition subfolder for camera-based features.

> NOTE: This README is written from the available repository structure. Inspect `raspi_server.py` and the `face-recog-pi/` folder to confirm exact runtime flags, endpoints, and configuration names, and update this README accordingly.

## Table of contents
- [Features](#features)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Quick start (Raspberry Pi)](#quick-start-raspberry-pi)
- [Configuration](#configuration)
- [Running the server](#running-the-server)
- [Face recognition module](#face-recognition-module)
- [Usage examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Development and Contributing](#development-and-contributing)
- [License & Acknowledgements](#license--acknowledgements)
- [Contact](#contact)

## Features
- Lightweight Python server intended to run on Raspberry Pi.
- Setup script to install Python 3.11 and required system/packages on Raspberry Pi.
- Face recognition module (in `face-recog-pi/`) for camera-based detection or identification.
- Includes assets in HTML/JS/CSS (suggests a web UI or control dashboard).

## Architecture (high level)
- raspi_server.py — main server process that exposes APIs or a web UI for interacting with Pi hardware and face recognition features.
- face-recog-pi/ — module and scripts that handle camera capture, feature extraction, and face recognition workflows (likely using OpenCV, dlib, or face-recognition libraries).
- setup_raspi_py311.sh — automation for preparing the system environment with Python 3.11 and dependencies.
- Static web assets (HTML/JavaScript/CSS) — optional web frontend served by the Python server.

## Repository layout (extracted)
- raspi_server.py
- setup_raspi_py311.sh
- face-recog-pi/ (directory)
- (potential static assets or other scripts inside repo)

Open these files to learn exact implementation details and endpoints:
- Inspect `raspi_server.py` for server port, routes/APIs, and how it interfaces with face-recog module.
- Inspect `face-recog-pi/` to see the models, configuration, and sample scripts.

## Requirements
- Raspberry Pi (recommended Raspberry Pi 4 or newer for best face recognition performance).
- Raspberry Pi OS (or Debian-based distro).
- Camera (Raspberry Pi Camera Module or compatible USB webcam).
- Internet connection to install packages.
- The setup script targets Python 3.11 — the included `setup_raspi_py311.sh` should be used to prepare the environment.

Typical system packages the project may require (based on common face-recognition stacks):
- python3.11
- python3.11-venv / pip
- build-essential, cmake, libatlas-base-dev (for OpenCV or numeric libs)
- libjpeg-dev, libtiff-dev, libavcodec-dev, libavformat-dev (for camera/ffmpeg support)

Check `setup_raspi_py311.sh` for the exact list of packages installed by this project.

## Quick start (Raspberry Pi)
1. Clone the repository:
   git clone https://github.com/easycodewithme/smart2rasp.git
   cd smart2rasp

2. Inspect the setup script and make it executable:
   chmod +x setup_raspi_py311.sh
   ./setup_raspi_py311.sh

   - The script will attempt to install Python 3.11, create/activate virtual environments, and install required Python packages. Read the script before running it, especially if you have existing Python installations.

3. Prepare camera and hardware:
   - Enable the Raspberry Pi camera interface in `raspi-config` if using the official camera module.
   - Confirm device path (e.g., `/dev/video0`) if using a USB webcam.

4. Start the server:
   python3.11 raspi_server.py
   - If the project uses a virtual environment, first activate it: `source .venv/bin/activate` (or the venv path created by the setup script).

## Configuration
The server and face recognition module typically read configuration via:
- Environment variables (recommended for service deployment).
- A local config file (e.g., config.json or .env) — check the repo for config examples.

Suggested environment variables (common patterns — verify in code):
- PORT — port for the server to listen on (default: 8000 or 5000).
- HOST — host binding (default: 0.0.0.0 to accept external connections).
- CAMERA_DEVICE — camera device path (default: /dev/video0).
- MODEL_PATH — path to face recognition model or embeddings directory.

Please open `raspi_server.py` and files inside `face-recog-pi/` to confirm exact variable names.

## Running the server (example)
- From the repo root, after running the setup script and activating venv:
  python3.11 raspi_server.py

- To run in background (systemd example snippet — adapt to your environment):
  Create /etc/systemd/system/smart2rasp.service:
  [Unit]
  Description=Smart2Rasp Server
  After=network.target

  [Service]
  User=pi
  WorkingDirectory=/home/pi/smart2rasp
  Environment=PORT=8000
  ExecStart=/home/pi/smart2rasp/.venv/bin/python3.11 /home/pi/smart2rasp/raspi_server.py
  Restart=always

  [Install]
  WantedBy=multi-user.target

  Then:
  sudo systemctl daemon-reload
  sudo systemctl enable --now smart2rasp

## Face recognition module (face-recog-pi/)
- The face recognition folder likely contains:
  - Camera capture script(s)
  - Model files or instructions to download a model
  - Training/embedding generation scripts
  - README or examples for enrolling/recognizing faces

How to proceed:
- Read `face-recog-pi/README` (if present) or open the main face recognition script to see dependencies (OpenCV, face_recognition, dlib, etc.).
- If models are not included, follow scripts to download or generate embeddings.

## Usage examples
- Access web UI: http://<raspberry-pi-ip>:<PORT>/ (if raspi_server serves a frontend)
- Call API endpoints (replace with exact paths after inspecting the server):
  curl http://raspberrypi:8000/api/status
  curl -X POST http://raspberrypi:8000/api/recognize -F "image=@/path/to/photo.jpg"

## Troubleshooting
- Camera not detected:
  - Ensure the camera is enabled (raspi-config → Interface Options → Camera).
  - Confirm device is available: ls /dev/video*
- Python 3.11 install errors:
  - Check the setup script logs and install missing system dependencies.
  - Some libraries (dlib / face-recognition) require additional build tools.
- Performance issues:
  - Face recognition is CPU-intensive. Use a Raspberry Pi 4/Compute Module or offload model inference to an accelerator (e.g., Coral TPU) if needed.

## Development and Contributing
- Clone the repo and create a branch for changes:
  git checkout -b feat/describe-feature
- Run tests (if any) and add unit tests when modifying core logic.
- Provide clear PR descriptions and include screenshots when UI changes are made.
- If you add new dependencies, update `setup_raspi_py311.sh` or provide alternative installation instructions.

## Suggested improvements (small checklist)
- Add a top-level README (this file) — done.
- Add a LICENSE file (Apache-2.0 / MIT or other).
- Add per-module READMEs: `face-recog-pi/README.md`.
- Provide an example configuration file (example.env or config.example.json).
- Add systemd unit or Dockerfile for easier deployment.

## License & Acknowledgements
- No LICENSE file detected. Add a license file (e.g., MIT) to clarify reuse rights.

## Contact
- Repository owner: https://github.com/easycodewithme

If you want, I can:
- Open and analyze `raspi_server.py` and files inside `face-recog-pi/` to extract exact endpoints, environment variables, and dependency lists, then update the README with precise commands and examples.
- Draft a systemd unit, Dockerfile, or an improved setup script with explicit dependency handling.
