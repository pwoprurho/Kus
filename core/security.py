# core/security.py
import os
import hashlib
import json
import datetime
from cryptography.fernet import Fernet

def get_cipher_suite():
    """Retrieves the encryption key from environment or generates a fallback."""
    key = os.environ.get("ENCRYPTION_KEY")
    return Fernet(key.encode()) if key else Fernet(Fernet.generate_key())

def encrypt_text(text):
    """Standardized encryption for sensitive data."""
    try:
        if not text: return None
        return get_cipher_suite().encrypt(text.encode()).decode()
    except Exception:
        return None

def sign_forensic_trace(thought_trace, user_message):
    """
    Creates a tamper-proof SHA-256 signature for the AI's reasoning chain.
    This generates the 'Audit Trail' used for premium verification.
    """
    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "input": user_message,
        "reasoning": thought_trace
    }
    # Sort keys ensures consistent hashing for the signature
    serialized = json.dumps(payload, sort_keys=True).encode()
    signature = hashlib.sha256(serialized).hexdigest()
    return signature, payload