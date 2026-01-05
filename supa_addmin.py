import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Must use Service Role to bypass RLS

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    exit()

# 2. Initialize High-Privilege Client
supabase: Client = create_client(url, key)

# 3. Define the Admin User Credentials
ADMIN_EMAIL = "akporurho@proton.me"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    print("Error: ADMIN_PASSWORD not found in .env")
    exit()
ADMIN_NAME = "System Administrator"

def create_admin():
    print(f"--- Creating Admin User: {ADMIN_EMAIL} ---\n")
    
    user_id = None

    # --- STEP A: Create or Get Auth User ---
    try:
        # Try creating the user
        user = supabase.auth.admin.create_user({
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "email_confirm": True,
            "user_metadata": {"full_name": ADMIN_NAME}
        })
        user_id = user.user.id
        print(f" -> Auth User Created (ID: {user_id})")
        
    except Exception as e:
        # If user already exists, we need to get their ID.
        print(f" -> Auth Note: User likely exists. Fetching ID...")
        try:
            # We sign in just to get the UID of the existing user
            session = supabase.auth.sign_in_with_password({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
            user_id = session.user.id
            print(f" -> Found Existing User ID: {user_id}")
        except Exception as login_error:
            print(f"CRITICAL FAILURE: Could not retrieve User ID. {login_error}")
            return

    # --- STEP B: Update Public Profile ---
    # We update the 'user_profiles' table. 
    # REMOVED: 'password', 'spoken_languages' (These don't exist in your new schema)
    # CHANGED: 'volunteers' -> 'user_profiles'
    # CHANGED: 'supa_user' -> 'supa_admin' (To match your SQL check constraint)
    
    if user_id:
        profile_data = {
            "id": user_id,
            "full_name": ADMIN_NAME,
            "email": ADMIN_EMAIL,
            "role": "supa_admin"  # Matches the check constraint in your SQL
        }
        
        try:
            # Upsert ensures we create it if missing, or update it if present
            supabase.table("user_profiles").upsert(profile_data).execute()
            print("\nSUCCESS! Super Admin Profile Synced.")
            print(f"Table: user_profiles | Role: supa_admin")
            print("You may now log in at /auth/login")
            
        except Exception as db_error:
            print(f"\nCRITICAL FAILURE during DB Update: {db_error}")

if __name__ == "__main__":
    create_admin()