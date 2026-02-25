# db.py
import os
from dotenv import load_dotenv
from flask import g
from supabase import create_client
import socket
from urllib.parse import urlparse

# Load Environment Variables
load_dotenv(override=True)

# Initialize Supabase Client with hostname validation to provide clearer errors
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

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
            supabase_admin = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
            supabase_admin = None

def safe_execute(query_builder):
    """
    Executes a Supabase query with built-in retry logic for transient errors.
    Usage: safe_execute(supabase_admin.table('name').select('*').eq('id', 1))
    """
    import time
    for attempt in range(3):
        try:
            return query_builder.execute()
        except Exception as e:
            error_msg = str(e).lower()
            # Retry on known transient errors
            if "illegal request line" in error_msg or "connection" in error_msg or "timeout" in error_msg:
                if attempt < 2:
                    time.sleep(0.5)
                    continue
            raise e

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