import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager
from models import User  # Imports the User class

# Import Blueprints
# Blueprints are imported after Supabase initialization to avoid circular imports
# 1. Load Environment Variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")

# 2. Initialize Supabase Client
from db import supabase_admin

# Import Blueprints AFTER Supabase client is configured to avoid circular imports
from routes.sandbox import sandbox_bp
from routes.public import public_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.tax import tax_bp
from routes.physics_sandbox import physics_bp

# 3. Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access the Command Center."
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    if not supabase_admin or not user_id: return None
    try:
        response = supabase_admin.table('user_profiles').select('*').eq('id', user_id).single().execute()
        if response.data:
            data = response.data
            return User(
                id=data['id'],
                full_name=data.get('full_name'),
                email=data.get('email'),
                role=data.get('role'),
                location=data.get('location')
            )
        return None
    except Exception as e:
        print(f"Session Load Error: {e}")
        return None

# --- MOBILE ACCESSIBILITY ENABLED ---
# Gate removed to allow all devices access to research protocols.

# 4. Register Blueprints
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(sandbox_bp)
app.register_blueprint(tax_bp)
app.register_blueprint(physics_bp)

# 5. Error Handlers
@app.errorhandler(403)
def access_forbidden(e): return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e): return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)