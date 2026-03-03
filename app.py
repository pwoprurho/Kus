import eventlet
eventlet.monkey_patch()

import os
import traceback
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from models import User  # Imports the User class

# Import Blueprints
# Blueprints are imported after Supabase initialization to avoid circular imports
# 1. Load Environment Variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")

# --- DOMAIN & SEO CONFIGURATION ---
# Set SERVER_NAME in production (e.g., kusmus.org) to ensure correct absolute URLs
# Use PREFERRED_URL_SCHEME (e.g., https) for secure links
if os.getenv("PREFERRED_URL_SCHEME"):
    app.config["PREFERRED_URL_SCHEME"] = os.getenv("PREFERRED_URL_SCHEME")

# --- SESSION & CSRF CONFIGURATION ---
is_prod = os.getenv('FLASK_ENV', 'development') == 'production'

# Flask-level session cookie settings (authoritative over Talisman)
app.config['SESSION_COOKIE_SECURE'] = is_prod
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CSRF Settings: Disable SSL strict check to avoid issues behind reverse proxies
# (Railway/Cloudflare terminate SSL, so the app sees HTTP internally)
app.config['WTF_CSRF_SSL_STRICT'] = False
# Allow CSRF tokens to remain valid for 2 hours (default is session lifetime)
app.config['WTF_CSRF_TIME_LIMIT'] = 7200

# --- PRODUCTION SECURITY HARDENING ---
csrf = CSRFProtect(app)
# Talisman handles HSTS, HTTPS redirect, and basic security headers.
# We disable CSP and force_https if not in production to allow local testing.
Talisman(app, 
    content_security_policy=None, # Lenient CSP to avoid breaking Socket.IO/Inter
    force_https=is_prod,
    session_cookie_secure=is_prod,
    session_cookie_http_only=True,
    session_cookie_samesite='Lax'
)

# --- PROXY FIX FOR SEO ---
# Ensures url_for generates correct https URLs behind proxies (e.g., Railway/Cloudflare)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 2. Initialize Extensions
from extensions import socketio
socketio.init_app(app)

# 2. Initialize Supabase Client
from db import supabase_admin, safe_execute

# Import Blueprints AFTER Supabase client is configured to avoid circular imports
from routes.sandbox import sandbox_bp
from routes.public import public_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.tax import tax_bp
from routes.physics_sandbox import physics_bp

# 3. Setup Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.client_access'
login_manager.login_message = "Authentication required to proceed."
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    if not supabase_admin or not user_id: return None
    
    # Security Hardening: Verify Supabase JWT for admin users
    if session.get('supabase_token'):
        try:
            # This verifies the token is valid with Supabase directly
            auth_user = supabase_admin.auth.get_user(session['supabase_token'])
            if not auth_user or auth_user.user.id != user_id:
                print(f"JWT Verification Failed for user_id: {user_id}")
                return None
        except Exception as jwt_err:
            print(f"JWT Verification Error: {jwt_err}")
            return None

    try:
        response = safe_execute(supabase_admin.table('user_profiles').select('*').eq('id', user_id).single())
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
        traceback.print_exc()
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

# 5. Register Socket Events
import socket_events

# 6. Error Handlers
@app.errorhandler(403)
def access_forbidden(e): return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e): return render_template('500.html'), 500

# 7. Strict Crawling Security Hook
@app.after_request
def add_security_headers(response):
    sensitive_prefixes = ('/admin', '/auth', '/sandbox', '/tax', '/physics', '/client')
    if getattr(request, 'path', '').startswith(sensitive_prefixes):
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=8000)