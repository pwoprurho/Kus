import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from supabase import create_client
from models import User  # Imports the User class with the critical __eq__ fix
# Add this import
from routes.sandbox import sandbox_bp



# 1. Load Environment Variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")

# 2. Initialize Supabase Client (Global Admin Access)
# We prefer the SERVICE ROLE KEY for the admin app to bypass RLS, 
# but will fall back to the ANON KEY if that's all that is available.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("CRITICAL WARNING: Supabase credentials not found in .env file.")
    supabase_admin = None
else:
    supabase_admin = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Redirects here if user isn't logged in
login_manager.login_message = "Please log in to access the Command Center."
login_manager.login_message_category = "error"
login_manager.init_app(app)

# --- USER LOADER (Critical for preventing RecursionError) ---
@login_manager.user_loader
def load_user(user_id):
    """
    Reloads the user object from the session.
    Includes robust error handling to prevent infinite loops.
    """
    if not supabase_admin or not user_id:
        return None

    try:
        # Query the 'user_profiles' table for the active session user
        response = supabase_admin.table('user_profiles').select('*').eq('id', user_id).single().execute()
        
        if response.data:
            data = response.data
            # Return the User object defined in models.py
            return User(
                id=data['id'],
                full_name=data.get('full_name'),
                email=data.get('email'),
                role=data.get('role'),
                location=data.get('location')
            )
        return None # User ID not found in database

    except Exception as e:
        # Log the error but return None to stop the recursion loop
        print(f"Session Load Error: {e}")
        return None

# 4. Register Blueprints
# Imports are placed here to avoid circular dependency with supabase_admin
from routes.public import public_bp
from routes.auth import auth_bp
from routes.admin import admin_bp

app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# 5. Error Handlers (Custom Pages)
@app.errorhandler(403)
def access_forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Register the sandbox blueprint
app.register_blueprint(sandbox_bp)


# 6. Run Application
if __name__ == "__main__":
    # debug=True allows hot-reloading during development
    app.run(debug=True, host="0.0.0.0", port=8000)