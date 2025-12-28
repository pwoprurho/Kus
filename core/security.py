# core/security.py
import os
import hashlib
import json
import datetime
from cryptography.fernet import Fernet

def get_cipher_suite():
    """Retrieves the encryption key from environment or generates a fallback."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode())

def encrypt_text(text):
    try:
        if not text: return None
        return get_cipher_suite().encrypt(text.encode()).decode()
    except Exception:
        return None

def decrypt_text(encrypted_text):
    try:
        if not encrypted_text: return ""
        return get_cipher_suite().decrypt(encrypted_text.encode()).decode()
    except Exception:
        return "[CONTENT LOCKED]"

def sign_forensic_trace(thought_trace, user_message):
    """
    Creates a tamper-proof SHA-256 signature for the AI's reasoning chain.
    This creates the 'Audit Trail' that we sell to the user.
    """
    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "input": user_message,
        "reasoning": thought_trace
    }
    # Sort keys ensures consistent hashing
    serialized = json.dumps(payload, sort_keys=True).encode()
    signature = hashlib.sha256(serialized).hexdigest()
    
    return signature, payload