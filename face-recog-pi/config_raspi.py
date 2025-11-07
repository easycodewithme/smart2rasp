"""
Raspberry Pi 4 specific configuration
Use this instead of config.py on Raspberry Pi for optimized performance
"""

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# Database
DATABASE_FILE = "cctv_system.db"

# Directories
KNOWN_FACES_DIR = "known"
ALERT_SNAPSHOT_DIR = "alerts"
STATIC_DIR = "static"
TEMPLATES_DIR = "templates"
LOGS_DIR = "logs"

# Face Recognition Settings (Optimized for Raspberry Pi 4)
FACE_DETECTION_MODEL = "hog"  # Use HOG instead of CNN for better performance on RPi
FACE_RECOGNITION_TOLERANCE = 0.6  # Slightly higher tolerance for RPi
FACE_DETECTION_SCALE = 0.25  # Lower resolution for faster processing on RPi

# Video Processing (Optimized for Raspberry Pi 4)
FRAME_SKIP = 2  # Process every 2nd frame to reduce CPU load
MAX_FRAME_QUEUE_SIZE = 5  # Smaller queue for limited memory
DETECTION_INTERVAL = 3  # Process frames every 3 seconds instead of 2

# Camera Settings
MAX_CAMERAS = 2  # Limit concurrent cameras on RPi 4
CAMERA_TIMEOUT = 10
CAMERA_RECONNECT_DELAY = 5

# Threading (Optimized for Raspberry Pi 4)
DETECTION_WORKERS = 2  # RPi 4 has 4 cores, use 2 for detection
CAMERA_WORKERS = 2

# Performance Settings
ENABLE_GPU = False  # No GPU acceleration on standard RPi
LOW_MEMORY_MODE = True  # Enable memory optimizations
REDUCE_IMAGE_SIZE = True  # Reduce image sizes before processing

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "logs/cctv_system.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3
