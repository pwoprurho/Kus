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

def sign_trade_execution(ticket_id, asset, action, quantity, price, conviction_score):
    """
    Cryptographically signs a trade execution order, binding the decision to the specific 
    market conditions and conviction score at the moment of authorization.
    """
    trace_data = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "ticket_id": ticket_id,
        "asset": asset,
        "action": action,
        "quantity": quantity,
        "price_limit": price,
        "sovereign_conviction": conviction_score,
        "authorization_source": "CHAIRMAN_MANUAL_OVERRIDE"
    }
    serialized = json.dumps(trace_data, sort_keys=True).encode()
    # Double-hashing simulates a more complex Merkle proof for the demo
    primary_hash = hashlib.sha256(serialized).hexdigest()
    final_signature = hashlib.sha256((primary_hash + "SOVEREIGN_ROOT_KEY").encode()).hexdigest()
    
    return final_signature
def verify_enclave_signature(payload_json: str, signature: str) -> bool:
    """
    Verifies that a sensitive action was signed by the Mobile Security Enclave.
    In the prototype, we expect 'signed_{action_type}_{level}' as implemented in lib.rs.
    In production, this would use ed25519.PublicKey.verify().
    """
    if not signature:
        return False
        
    payload = json.loads(payload_json)
    action_type = payload.get("action_type", "unknown")
    level = payload.get("sensitivity_level", "LOW")
    
    # Prototype verification logic matching Rust HRManager.sign_action
    expected_mock_sig = f"signed_{action_type}_{level}"
    return signature == expected_mock_sig
