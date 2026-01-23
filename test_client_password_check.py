import os
from supabase import create_client
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

# Load environment variables from .env
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --- CHANGE THESE FOR YOUR TEST ---
TEST_EMAIL = 'akporurho@yahoo.com'
TEST_PASSWORD = 'Ejiro2828!'

try:
    res = supabase.table('clients').select('*').eq('email', TEST_EMAIL).single().execute()
    if not res.data:
        print(f"No client found with email: {TEST_EMAIL}")
    else:
        client = res.data
        print(f"Client found: {client['email']}")
        print(f"Password hash: {client['password_hash']}")
        match = check_password_hash(client['password_hash'], TEST_PASSWORD)
        print(f"Password match: {match}")
except Exception as e:
    print(f"Error: {e}")
