#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for HTTPS access
Run this once to create SSL certificates for secure camera access
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import socket
import ipaddress

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def generate_self_signed_cert():
    """
    Generate a self-signed SSL certificate
    """
    print("=" * 70)
    print("Generating Self-Signed SSL Certificate")
    print("=" * 70)
    print()
    
    # Generate private key
    print("[1/4] Generating private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    print("✓ Private key generated")
    print()
    
    # Get local IP
    local_ip = get_local_ip()
    print(f"[2/4] Detected local IP: {local_ip}")
    print()
    
    # Create certificate
    print("[3/4] Creating certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CCTV System"),
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName(local_ip),
            x509.IPAddress(ipaddress.IPv4Address(local_ip)),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    print("✓ Certificate created")
    print()
    
    # Write certificate to file
    print("[4/4] Writing files...")
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print("✓ Created: cert.pem")
    
    # Write private key to file
    with open("key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("✓ Created: key.pem")
    print()
    
    print("=" * 70)
    print("✅ SSL Certificate Generated Successfully!")
    print("=" * 70)
    print()
    print("Files created:")
    print("  📄 cert.pem - SSL certificate")
    print("  🔑 key.pem  - Private key")
    print()
    print("=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Start HTTPS server:")
    print("   python run_server_https.py")
    print()
    print("2. Access from browser:")
    print(f"   https://localhost:8000")
    print(f"   https://{local_ip}:8000")
    print()
    print("3. Browser Security Warning:")
    print("   - Browser will show 'Not Secure' or 'Your connection is not private'")
    print("   - This is NORMAL for self-signed certificates")
    print("   - Click 'Advanced' → 'Proceed to site' (or similar)")
    print("   - This is SAFE - it's your own certificate")
    print()
    print("4. On Mobile:")
    print("   - You may need to accept the certificate once")
    print("   - After that, camera access will work!")
    print()
    print("=" * 70)

if __name__ == "__main__":
    try:
        generate_self_signed_cert()
    except ImportError:
        print("❌ Error: 'cryptography' module not installed")
        print()
        print("Install it with:")
        print("  pip install cryptography")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        import traceback
        traceback.print_exc()
