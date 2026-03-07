# db.py
import os
from dotenv import load_dotenv
from flask import g
from supabase import create_client, ClientOptions
import socket
import httpx
from urllib.parse import urlparse

# Load Environment Variables
# override=False ensures that variables set in the Render/Terminal environment
# take precedence over any local .env file.
load_dotenv(override=False)

# Initialize Supabase Client with hostname validation
# We use .strip() and str() to ensure no hidden characters from .env files interfere
SUPABASE_URL = str(os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()

def _resolve_hostname(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or url
        # Try to resolve DNS for the host
        socket.getaddrinfo(host, None)
        return True
    except Exception:
        return False

if not SUPABASE_URL or not SUPABASE_KEY:
    print("CRITICAL WARNING: Supabase credentials not found in .env file. Set SUPABASE_URL and SUPABASE_KEY.")
    supabase_admin = None
else:
    # Validate hostname resolution before attempting client creation
    if not _resolve_hostname(SUPABASE_URL):
        print(f"Supabase host resolution failed for '{SUPABASE_URL}'. Check network/DNS and SUPABASE_URL value.")
        supabase_admin = None
    else:
        try:
            # Enforce HTTP/1.1 to prevent "Illegal Request Line" errors on Render's proxy
            options = ClientOptions().replace(httpx_client=httpx.Client(http2=False))
            supabase_admin = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
            supabase_admin = None

def safe_execute(query_builder):
    """
    Executes a Supabase query.
    Retry logic removed for security best practices; 
    HTTP/1.1 stabilization handles proxy connectivity.
    """
    return query_builder.execute()

def close_db_connection(e=None):
    """
    Placeholder for database teardown logic.

    This function is registered with app.teardown_appcontext to ensure
    resources are cleaned up at the end of every request, regardless of errors.
    """
    # 1. Check Flask's global state (g) for a raw database connection object
    # The '.pop' method safely retrieves and removes the 'db' variable.
    db = g.pop('db', None)
    
    # 2. If a connection object was stored, close it.
    # This is relevant only if a raw driver like psycopg was used.
    if db is not None:
        # If we were using psycopg, the actual closing code would be here:
        # db.close() 
        pass