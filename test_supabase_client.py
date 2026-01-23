import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Test: List all clients (limit 5)
try:
    res = supabase.table('clients').select('*').limit(5).execute()
    print("Sample clients:")
    for client in res.data:
        print(client)
except Exception as e:
    print(f"Error querying clients table: {e}")
