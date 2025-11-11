#!/usr/bin/env python3
"""
CCTV Server Status Viewer
Displays server status messages (no actual server start).
Exits only when Ctrl+C is pressed.
"""

import time
import logging
import sys
import socket
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_ssl_files():
    """Check if SSL certificate files exist"""
    cert_file = Path("cert.pem")
    key_file = Path("key.pem")

    if not cert_file.exists() or not key_file.exists():
        print()
        print("=" * 70)
        print("❌ ERROR: SSL Certificate Not Found")
        print("=" * 70)
        print()
        print("You need to generate SSL certificates first.")
        print()
        print("Run this command:")
        print("  python generate_ssl_cert.py")
        print()
        print("Then run this script again.")
        print("=" * 70)
        print()
        return False

    return True

def show_status():
    """Print server status messages only"""
    print("=" * 60)
    print("Starting Multi-Camera CCTV System (HTTPS)")
    print("=" * 60)
    
    # Try to get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "YOUR-IP"

    print("Server will be accessible at:")
    print(f"  - Local: https://localhost:8000")
    print(f"  - Network: https://{local_ip}:8000")
    print("")
    print("⚠️  IMPORTANT: Browser Security Warning")
    print("  Your browser will show a security warning")
    print("  This is NORMAL for self-signed certificates")
    print("  Click 'Advanced' → 'Proceed to site'")
    print("")
    print("📱 Mobile Access:")
    print(f"  Open browser and go to: https://{local_ip}:8000")
    print("  Accept the certificate warning")
    print("  Camera access will now work!")
    print("")
    print("Press Ctrl+C to stop this status display")
    print("=" * 60)

def main():
    """Main loop showing static status until Ctrl+C"""
    if not check_ssl_files():
        sys.exit(1)

    show_status()
    print()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down status viewer...")
        print("Exited gracefully ✅")

if __name__ == "__main__":
    main()
