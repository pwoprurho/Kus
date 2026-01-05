import os
from functools import wraps
from flask import abort, current_app, redirect, url_for
from flask_login import current_user
from supabase import create_client, Client
from cryptography.fernet import Fernet

def role_required(*roles):
    """
    Decorator to restrict access based on user roles (e.g., 'admin', 'editor').
    If the user is logged in but lacks the role, it returns a 403 Forbidden error.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                # If not logged in, redirect to the Admin Login page
                return redirect(url_for('admin.login'))
            
            if current_user.role not in roles:
                # If logged in but wrong role
                abort(403) # Forbidden
                
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# --- Supabase Client Helper ---

# This helper is needed if a temporary client (using ANON key) is required elsewhere.
def get_anon_client():
    """Returns a new Supabase client using the ANON key for public/auth tasks."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") 
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
    return create_client(url, key)

def get_cipher_suite():
    """Retrieves the encryption key."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        # Fallback for dev safety
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode())

def encrypt_text(text):
    """Encrypts database content."""
    try:
        if not text: return None
        return get_cipher_suite().encrypt(text.encode()).decode()
    except Exception as e:
        print(f"Encryption Error: {e}")
        return None

def decrypt_text(encrypted_text):
    """Decrypts database content."""
    try:
        if not encrypted_text: return ""
        return get_cipher_suite().decrypt(encrypted_text.encode()).decode()
    except Exception:
        return "[CONTENT LOCKED]"