# db.py
import os
from dotenv import load_dotenv
from flask import g
from supabase import create_client

# Load Environment Variables
load_dotenv(override=True)

# Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("CRITICAL WARNING: Supabase credentials not found in .env file.")
    supabase_admin = None
else:
    try:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}")
        supabase_admin = None

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