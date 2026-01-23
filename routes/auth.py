
import os
import secrets
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from db import supabase_admin
from models import User, ClientUser 
from services.mailer import send_recovery_otp

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# === RECOVERY OTP ENDPOINT ===
@auth_bp.route('/send-recovery', methods=['POST'])
def send_recovery():
    email = request.json.get('email')
    if not email: return jsonify({'error': 'Email required'}), 400
    
    try:
        # Check if client exists
        client_res = supabase_admin.table('clients').select('id').eq('email', email).execute()
        if client_res.data and len(client_res.data) > 0:
            # Generate 6-digit OTP
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            session['recovery_otp'] = otp
            session['recovery_email'] = email
            
            # Send Email
            from services.mailer import send_recovery_otp
            send_recovery_otp(email, otp)
            
            return jsonify({'success': True, 'message': 'Recovery code sent'})
        else:
            return jsonify({'error': 'Email not authorized in system'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === CLIENT TOKEN HANDSHAKE ROUTE ===
@auth_bp.route('/client-token', methods=['POST'])
def client_token():
    # Only allow if client session is valid
    if not session.get('client_access') or not session.get('client_id'):
        return jsonify({'error': 'Not authenticated'}), 401
    # Generate a secure token and store in session
    token = secrets.token_urlsafe(32)
    session['client_token'] = token
    return jsonify({'client_token': token, 'client_id': session.get('client_id')})

# Helper: Create a temp client (Safe)
def get_auth_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") 
    if not url or not key: return None
    return create_client(url, key)

# --- ADMIN LOGIN (UNCHANGED) ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            temp_client = get_auth_client()
            auth_res = temp_client.auth.sign_in_with_password({"email": email, "password": password})
            if auth_res.user:
                response = supabase_admin.table('user_profiles').select('*').eq('id', auth_res.user.id).single().execute()
                if response.data:
                    data = response.data
                    user = User(data['id'], data.get('full_name'), data.get('email'), data.get('role', 'intern'), data.get('location'))
                    login_user(user)
                    return redirect(url_for('admin.dashboard')) 
                else: flash('User profile not found.', 'error')
            else: flash('Invalid credentials.', 'error')
        except Exception as e: flash(f'Login failed: {str(e)}', 'error')
    return render_template('admin/login.html') 

# =========================================================
# === SECURE CLIENT PROTOCOLS ===
# =========================================================

@auth_bp.route('/client-access', methods=['GET', 'POST'])
def client_access():
    if request.method == 'POST':
        email = request.form.get('email')
        auth_input = request.form.get('auth_input').strip()
        print(f"[DEBUG] Received email: {email}")
        print(f"[DEBUG] Received auth_input: {auth_input}")
        
        
        try:
            # Check for existing client
            client_res = supabase_admin.table('clients').select('*').eq('email', email).execute()
            
            if client_res.data and len(client_res.data) > 0:
                client_data = client_res.data[0]
                print(f"[DEBUG] DB client_data: {client_data}")
                # Check for Valid Session OTP (OR Master Key)
                session_otp = session.get('recovery_otp')
                is_valid_otp = session_otp and auth_input == session_otp and session.get('recovery_email') == email
                # Case 1: RECOVERY (OTP or Key)
                if is_valid_otp or auth_input == client_data['recovery_key']:
                    print(f"[DEBUG] OTP valid: {is_valid_otp}, Recovery key match: {auth_input == client_data['recovery_key']}")
                    session['temp_client_email'] = email
                    session['temp_client_key'] = auth_input # Generic truthy verification token
                    if is_valid_otp:
                        session.pop('recovery_otp', None) # Consume OTP
                        flash("Identity Verified. Proceed to Credential Reset.", "info")
                    else:
                        flash("Master Key Accepted. Proceed to Credential Reset.", "info")
                    return redirect(url_for('auth.client_setup')) 
                # Case 2: LOGIN (Entered Password)
                print(f"[DEBUG] Password hash from DB: {client_data['password_hash']}")
                pw_check = check_password_hash(client_data['password_hash'], auth_input)
                print(f"[DEBUG] check_password_hash result: {pw_check}")
                if pw_check:
                    session['client_access'] = True
                    session['client_id'] = client_data['id'] # CRITICAL: Lock ID into session
                    session['client_email'] = email
                    flash("Secure Channel Established.", "success")
                    return redirect(url_for('public.client_dashboard'))
                else:
                    flash("Access Denied: Invalid Password or Key.", "error")
            else:
                # Case 3: FIRST TIME REGISTRATION
                audit_res = supabase_admin.table('audit_requests')\
                    .select('*').eq('email', email).eq('verification_code', auth_input).execute()
                
                if audit_res.data and len(audit_res.data) > 0:
                    session['temp_client_email'] = email
                    session['temp_client_key'] = auth_input
                    session['temp_client_name'] = audit_res.data[0]['name']
                    
                    flash("Identity Verified. Initialize Security Protocol.", "success")
                    return redirect(url_for('auth.client_setup'))
                else:
                     flash("Access Denied: Identity Token Invalid.", "error")

        except Exception as e:
            print(f"Auth Error: {e}")
            flash("System Error during handshake.", "error")

    return render_template('client/client_access.html')

@auth_bp.route('/client-setup', methods=['GET', 'POST'])
def client_setup():
    # Security Gate
    if not session.get('temp_client_email') or not session.get('temp_client_key'):
        return redirect(url_for('auth.client_access'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for('auth.client_setup'))
            
        hashed_pw = generate_password_hash(password)
        email = session.get('temp_client_email')
        key = session.get('temp_client_key')
        name = session.get('temp_client_name', 'Valued Client')
        
        
        try:
            existing = supabase_admin.table('clients').select('id').eq('email', email).execute()
            client_id = None
            
            if existing.data:
                # UPDATE (Password Reset)
                supabase_admin.table('clients').update({
                    'password_hash': hashed_pw
                }).eq('email', email).execute()
                
                client_id = existing.data[0]['id']
                flash("Credentials Updated. Logging in...", "success")
            else:
                # INSERT (New Registration)
                # We execute and return data to get the new UUID immediately
                insert_res = supabase_admin.table('clients').insert({
                    'email': email,
                    'password_hash': hashed_pw,
                    'full_name': name,
                    'recovery_key': key
                }).execute()
                
                if insert_res.data:
                    client_id = insert_res.data[0]['id']
                
                # Mark audit request as registered
                supabase_admin.table('audit_requests').update({'is_registered': True}).eq('email', email).execute()
                flash("Protocol Initialized. Account Secured.", "success")

            # Finalize Session
            if client_id:
                session.pop('temp_client_email', None)
                session.pop('temp_client_key', None)
                session['client_access'] = True
                session['client_id'] = client_id # CRITICAL: ID is now available for Chat API
                session['client_email'] = email
            
                return redirect(url_for('public.client_dashboard'))
            else:
                flash("Error: Could not retrieve secure ID. Please contact support.", "error")
                return redirect(url_for('auth.client_access'))
            
        except Exception as e:
            print(f"Setup Error: {e}")
            flash("Database Write Error.", "error")

    return render_template('client/client_setup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear() 
    flash('Session Terminated.', 'info')
    return redirect(url_for('auth.login'))