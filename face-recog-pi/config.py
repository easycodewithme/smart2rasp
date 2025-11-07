"""
Configuration file for Multi-Camera CCTV System
"""
import os

# Server Configuration
SERVER_HOST = "0.0.0.0"  # Listen on all interfaces for network access
SERVER_PORT = 8000
DEBUG_MODE = True

# Database Configuration
DATABASE_FILE = "cctv_system.db"

# Face Recognition Configuration
KNOWN_ENCODINGS_FILE = "known_encodings.npy"
FACE_DETECTION_MODEL = "hog"  # "hog" or "cnn"
FACE_RECOGNITION_TOLERANCE = 0.5
FACE_DETECTION_SCALE = 0.5  # Scale factor for faster processing

# Video Processing Configuration
PROCESS_EVERY_N_FRAMES = 2  # Process every Nth frame for performance
MAX_QUEUE_SIZE = 100  # Maximum frames in processing queue per camera
FRAME_BUFFER_SIZE = 30  # Number of frames to keep in memory for streaming

# Camera Configuration
DEFAULT_CAMERA_FPS = 25
CAMERA_RECONNECT_DELAY = 5  # Seconds to wait before reconnecting
CAMERA_TIMEOUT = 10  # Seconds before considering camera disconnected

# Alert Configuration
ALERT_COOLDOWN = 30  # Seconds between alerts for same person on same camera
SAVE_ALERT_SNAPSHOTS = True
ALERT_SNAPSHOT_DIR = "alerts"

# Directories
STATIC_DIR = "static"
TEMPLATES_DIR = "templates"
LOGS_DIR = "logs"

# Create necessary directories
for directory in [ALERT_SNAPSHOT_DIR, STATIC_DIR, TEMPLATES_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(LOGS_DIR, "cctv_system.log")
