
#!/usr/bin/env python3
"""
HTTPS Server for Multi-Camera CCTV System
Enables secure camera access from mobile devices
"""

import uvicorn
import logging
import sys
import os
from pathlib import Path

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

def main():
    """Start the HTTPS server"""
    
    # Check for SSL files
    if not check_ssl_files():
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Starting Multi-Camera CCTV System (HTTPS)")
    logger.info("=" * 60)
    
    # Get local IP
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "YOUR-IP"
    
    logger.info("Server will be accessible at:")
    logger.info(f"  - Local: https://localhost:8000")
    logger.info(f"  - Network: https://{local_ip}:8000")
    logger.info("")
    logger.info("⚠️  IMPORTANT: Browser Security Warning")
    logger.info("  Your browser will show a security warning")
    logger.info("  This is NORMAL for self-signed certificates")
    logger.info("  Click 'Advanced' → 'Proceed to site'")
    logger.info("")
    logger.info("📱 Mobile Access:")
    logger.info(f"  Open browser and go to: https://{local_ip}:8000")
    logger.info("  Accept the certificate warning")
    logger.info("  Camera access will now work!")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)
    
    # Start server with SSL
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem",
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutting down HTTPS server...")
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
