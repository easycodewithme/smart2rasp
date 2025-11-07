#!/usr/bin/env python3
"""
Raspberry Pi optimized HTTPS server
Uses config_raspi.py for RPi-specific settings
"""

import uvicorn
import logging
import sys
import os
from pathlib import Path

# Use Raspberry Pi config
import config_raspi as config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_ssl_files():
    """Check if SSL certificate files exist"""
    cert_file = Path("cert.pem")
    key_file = Path("key.pem")
    
    if not cert_file.exists() or not key_file.exists():
        logger.error("SSL certificate files not found!")
        print()
        print("=" * 70)
        print("❌ ERROR: SSL Certificate Not Found")
        print("=" * 70)
        print()
        print("Generate SSL certificates:")
        print("  python3 generate_ssl_cert.py")
        print()
        print("Or run the setup script:")
        print("  ./setup_raspi.sh")
        print("=" * 70)
        print()
        return False
    
    return True

def get_local_ip():
    """Get local IP address"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "YOUR-IP"

def main():
    """Start the HTTPS server with Raspberry Pi optimizations"""
    
    # Check for SSL files
    if not check_ssl_files():
        sys.exit(1)
    
    local_ip = get_local_ip()
    
    logger.info("=" * 60)
    logger.info("Smart CCTV System - Raspberry Pi 4 (HTTPS)")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Raspberry Pi Optimizations:")
    logger.info(f"  - Detection Model: {config.FACE_DETECTION_MODEL}")
    logger.info(f"  - Detection Workers: {config.DETECTION_WORKERS}")
    logger.info(f"  - Frame Scale: {config.FACE_DETECTION_SCALE}")
    logger.info(f"  - Max Cameras: {config.MAX_CAMERAS}")
    logger.info("")
    logger.info("Server accessible at:")
    logger.info(f"  - Local: https://localhost:{config.SERVER_PORT}")
    logger.info(f"  - Network: https://{local_ip}:{config.SERVER_PORT}")
    logger.info("")
    logger.info("⚠️  Browser Security Warning:")
    logger.info("  Click 'Advanced' → 'Proceed to site'")
    logger.info("")
    logger.info("📱 Mobile Access:")
    logger.info(f"  https://{local_ip}:{config.SERVER_PORT}")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    # Start server with SSL and RPi optimizations
    uvicorn.run(
        "api_server:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem",
        reload=False,  # Disable reload on RPi to save resources
        workers=1,  # Single worker for RPi
        log_level="info"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
