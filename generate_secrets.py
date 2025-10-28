#!/usr/bin/env python3
"""
Generate Secure Secrets for CI/CD Helper

This script generates cryptographically secure random secrets
for use in your .env file.

Usage:
    python generate_secrets.py

The script will output SECRET_KEY and SESSION_SECRET values
that you can copy directly into your .env file.
"""

import secrets
import sys

def generate_secret(length=32):
    """Generate a URL-safe random secret"""
    return secrets.token_urlsafe(length)

def main():
    print("=" * 70)
    print("🔐 CI/CD Helper - Secure Secret Generator")
    print("=" * 70)
    print()
    print("Copy these values to your .env file:")
    print()
    print("-" * 70)
    
    # Generate SECRET_KEY
    secret_key = generate_secret(32)
    print(f"SECRET_KEY={secret_key}")
    
    # Generate SESSION_SECRET
    session_secret = generate_secret(32)
    print(f"SESSION_SECRET={session_secret}")
    
    print("-" * 70)
    print()
    print("✅ Secrets generated successfully!")
    print()
    print("Important Security Notes:")
    print("  • Keep these secrets secure and never commit them to version control")
    print("  • Use different secrets for different environments (dev, staging, prod)")
    print("  • Rotate secrets regularly (every 90 days recommended)")
    print("  • Each deployment should have unique secrets")
    print()
    
    # Additional secrets that might be useful
    print("Optional Additional Secrets:")
    print("-" * 70)
    print(f"API_KEY_SALT={generate_secret(16)}")
    print(f"CSRF_SECRET={generate_secret(24)}")
    print(f"WEBHOOK_SECRET={generate_secret(24)}")
    print("-" * 70)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)