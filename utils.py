import os
from functools import wraps
from flask import abort, current_app, redirect, url_for
from flask_login import current_user
from supabase import create_client, Client

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