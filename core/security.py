import os
from cryptography.fernet import Fernet

def get_cipher_suite():
    """Retrieves the encryption key from environment or generates a fallback."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode())

def encrypt_text(text):
    """Standardized encryption for sensitive database content."""
    try:
        if not text: return None
        return get_cipher_suite().encrypt(text.encode()).decode()
    except Exception:
        return None

def decrypt_text(encrypted_text):
    """Standardized decryption for UI display."""
    try:
        if not encrypted_text: return ""
        return get_cipher_suite().decrypt(encrypted_text.encode()).decode()
    except Exception:
        return "[CONTENT LOCKED]"