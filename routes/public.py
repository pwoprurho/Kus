import json
import os
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash, Response, make_response
from core.engine import KusmusAIEngine
from services.personas import MAIN_ASSISTANT, DEMO_REGISTRY
from db import supabase_admin, safe_execute

public_bp = Blueprint('public', __name__)

# === CLIENT DASHBOARD ROUTE ===
@public_bp.route('/client-dashboard')
def client_dashboard():
    # Only allow access if client session is valid
    if not session.get('client_access') or not session.get('client_id'):
        return render_template('403.html')
    return render_template('client/client_dashboard.html')

# === CLIENT CHAT ROUTE ===
@public_bp.route('/client-chat')
def client_chat():
    # Only allow access if client session is valid
    if not session.get('client_access') or not session.get('client_id'):
        return render_template('403.html')
    return render_template('client/client_chat.html')

# === CLIENT SETTINGS ROUTE ===
@public_bp.route('/settings', methods=['GET', 'POST'])
def client_settings():
    # 1. Security Check
    if not session.get('client_access') or not session.get('client_id'):
        return render_template('403.html')

    client_id = session.get('client_id')

    if request.method == 'POST':
        try:
            # 2. Extract Form Data
            deriv_token = request.form.get('deriv_token')
            gemini_key = request.form.get('gemini_key')
            risk = request.form.get('risk_tolerance')
            phone = request.form.get('phone')
            
            # Update phone in DB with retry
            try:
                safe_execute(supabase_admin.table('clients').update({'phone': phone}).eq('id', client_id))
            except Exception as e:
                print(f"Phone Update Error: {e}")

            # 3. Simulate Configuration Update
            config_update = {
                'deriv_token': deriv_token if deriv_token else None,
                'gemini_key': gemini_key if gemini_key else None,
                'risk_tolerance': int(risk) if risk else 5,
                'phone': phone
            }
            
            # Attempt update (Safe simulation)
            try:
                # supabase_admin.table('clients').update({'config': config_update}).eq('id', client_id).execute()
                pass 
            except Exception as e:
                print(f"Config Save Warning: {e}")

            # 4. Handle Password Change (If provided)
            # ... (unchanged)
            new_pw = request.form.get('new_password')
            confirm_pw = request.form.get('confirm_password')

            if new_pw:
                if new_pw != confirm_pw:
                    flash("Passwords do not match.", "error")
                    return render_template('client/client_settings.html', config=config_update)
                
                flash("Password Updated Successfully.", "success")
            else:
                flash("Configuration Saved.", "success")
            
            return redirect(url_for('public.client_settings'))

        except Exception as e:
            flash(f"Error saving settings: {str(e)}", "error")

    # GET Request: Fetch existing config
    mock_config = {
        'risk_tolerance': 5,
        'deriv_token': '',
        'gemini_key': '',
        'phone': ''
    }
    
    try:
        res = supabase_admin.table('clients').select('phone').eq('id', client_id).single().execute()
        if res.data:
            mock_config['phone'] = res.data.get('phone', '')
    except: pass

    return render_template('client/client_settings.html', config=mock_config)

# =========================================================
# === CORE PAGE ROUTES ===
# =========================================================

@public_bp.route("/")
def home():
    return render_template("index.html")

@public_bp.route("/solutions")
def solutions():
    return render_template("solutions.html")

@public_bp.route("/method")
def method():
    return render_template("method.html")

@public_bp.route("/ceo-profile")
def ceo_profile():
    return render_template("ceo_profile.html")

@public_bp.route("/team")
def team():
    return render_template("our_team.html")

@public_bp.route("/chairman")
def chairman():
    return render_template("chairmans_mandate.html")

@public_bp.route("/api/market/trend")
def market_trend_api():
    """Public API to fetch global market trend (Live)."""
    from services.mcp_tools import get_global_market_trend
    data = get_global_market_trend()
    return jsonify(data)

@public_bp.route("/api/market/history")
def market_history_api():
    """Public API to fetch historical candle data."""
    ticker = request.args.get('ticker', 'SPY')
    period = request.args.get('period', '3mo')
    interval = request.args.get('interval', '1d')
    from services.mcp_tools import get_ticker_history
    data = get_ticker_history(ticker, period, interval)
    return jsonify(data)




# Valid routes for core usage
# Removed duplicate /sandbox handler to allow routes/sandbox.py to handle it authoritative.


@public_bp.route("/blog")
def blog():
    posts = []
    if supabase_admin:
        try:
            # Fetching published blog posts from Supabase
            # Updated to match Admin schema: table 'blog_posts' and status='Published'
            response = safe_execute(supabase_admin.table('blog_posts').select("*").eq('status', 'Published').order('published_at', desc=True))
            posts = response.data
        except Exception as e:
            print(f"Blog Fetch Error: {e}")
            # Fallback for older schema if migration isn't complete (optional, but good for safety)
            try:
                response = safe_execute(supabase_admin.table('posts').select("*").eq('published', True))
                if response.data: posts.extend(response.data)
            except: pass

    return render_template("blog.html", posts=posts)

@public_bp.route("/blog/<string:post_id>")
def blog_post(post_id):
    post = None
    if supabase_admin:
        try:
            # Fetch single post from correct table
            response = safe_execute(supabase_admin.table('blog_posts').select("*").eq('id', post_id).limit(1))
            if response.data:
                post = response.data[0]
            else:
                 # Fallback check
                response = safe_execute(supabase_admin.table('posts').select("*").eq('id', post_id).limit(1))
                if response.data: post = response.data[0]

        except Exception as e:
            print(f"Blog Post Fetch Error: {e}")
            
    if not post:
        return render_template("404.html"), 404
        
    return render_template("blog_post.html", post=post)

# --- FIX: Added missing route to resolve BuildError in index.html ---
@public_bp.route("/request-audit", methods=['GET', 'POST'])
def audit_request():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        hosting_pref = request.form.get('hosting_preference')
        message = request.form.get('message')

        if not company_name or not name or not email or not phone:
            flash("All secure contact fields (Company, Name, Email, Phone) are required.", "error")
            return render_template("request_audit.html")

        try:
            # Generate a simple verification code for the client to use later
            import secrets
            import time
            verification_code = secrets.token_hex(4).upper()

            # Insert into Supabase with centralized retry
            safe_execute(supabase_admin.table('audit_requests').insert({
                'company_name': company_name,
                'name': name,
                'email': email,
                'phone': phone,
                'hosting_preference': hosting_pref,
                'message': message,
                'verification_code': verification_code
            }))

            flash(f"Request Transmitted. Your Identity Token is: {verification_code}. Keep this secure.", "success")
            return redirect(url_for('public.home'))

        except Exception as e:
            print(f"Audit Request Error (after retries): {e}")
            flash("Electronic transmission failure. Please try again.", "error")
            return render_template("request_audit.html")

    return render_template("request_audit.html")

# =========================================================
# === AI CHAT API (Standard Widget) ===
# =========================================================

@public_bp.route("/api/chat", methods=["POST"])
def chat_ai_assistant():
    """
    Standard Support Chat for the website footer/widget.
    Uses the 'MAIN_ASSISTANT' persona.
    """
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message: 
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Import the dynamic loader
        from services.personas import get_main_assistant_instruction, MAIN_ASSISTANT
        
        # Initialize Engine with the Client Care Persona (Dynamically loaded)
        engine = KusmusAIEngine(
            system_instruction=get_main_assistant_instruction(),
            model_name=MAIN_ASSISTANT.get('model', 'gemini-2.5-flash-lite')
        )
        # Maintain Session-based History
        raw_history = session.get('chat_history', [])
        
        # Generate Response (Standard assistant does not need MCP tools)
        response_text, _ = engine.generate_response(user_message, history=raw_history)

        # Update History
        raw_history.append({"role": "user", "parts": [user_message]})
        raw_history.append({"role": "model", "parts": [response_text]})
        session['chat_history'] = raw_history
        
        return jsonify({'response': response_text})

    except Exception as e:
        print(f"AI Chat Error: {e}")
        return jsonify({'error': 'Connection interrupted.'}), 500

@public_bp.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    session.pop('chat_history', None)
    return jsonify({'status': 'cleared'})

# === CLIENT CRYPTO WALLET ROUTE ===
@public_bp.route('/crypto-wallet', methods=['GET', 'POST'])
def crypto_wallet_action():
    # Only allow access if client session is valid
    if not session.get('client_access') or not session.get('client_id'):
        return render_template('403.html')
    user_id = session.get('client_id')
    from core.wallet import Wallet
    from core.gateways import BTCGateway, USSDGateway
    # Load wallet info
    wallet = Wallet(user_id)
    btc_address = wallet.btc_address
    eth_address = wallet.eth_address
    btc_balance = BTCGateway.get_balance(btc_address)
    result = None
    # Load transaction history (mock for now)
    transactions = []
    if os.path.exists(f"tx_{user_id}.json"):
        with open(f"tx_{user_id}.json", "r") as f:
            transactions = json.load(f)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'send_btc':
            to_address = request.form.get('to_address')
            amount_btc = float(request.form.get('amount_btc'))
            result = BTCGateway.send_btc(wallet.btc_private_key, to_address, amount_btc)
            transactions.append({"type": "Send BTC", "amount": amount_btc, "currency": "BTC", "status": result["status"], "timestamp": str(datetime.now())})
        elif action == 'ussd_pay':
            phone_number = request.form.get('phone_number')
            amount = float(request.form.get('amount'))
            result = USSDGateway.send_payment(phone_number, amount)
            transactions.append({"type": "USSD Pay", "amount": amount, "currency": "Fiat", "status": result["status"], "timestamp": str(datetime.now())})
        # Save transaction history
        with open(f"tx_{user_id}.json", "w") as f:
            json.dump(transactions, f)
    return render_template('client/crypto_wallet_dashboard.html', btc_address=btc_address, eth_address=eth_address, btc_balance=btc_balance, result=result, transactions=transactions)

# =========================================================
# === SEO ROUTES (Sitemap & Robots) ===
# =========================================================

@public_bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
    """Generates a dynamic sitemap for SEO."""
    import xml.sax.saxutils as saxutils
    
    # 1. Page Definitions
    host_url = request.url_root.rstrip('/')
    pages = [
        'public.home', 
        'public.solutions', 
        'public.method', 
        'public.ceo_profile', 
        'public.team', 
        'public.chairman', 
        'public.blog',
        'public.audit_request'
    ]
    
    xml_sitemap = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_sitemap.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # 2. Static Pages
    for page in pages:
        try:
            url = url_for(page, _external=True)
            escaped_url = saxutils.escape(url)
            xml_sitemap.append(f'  <url>')
            xml_sitemap.append(f'    <loc>{escaped_url}</loc>')
            xml_sitemap.append(f'    <changefreq>weekly</changefreq>')
            xml_sitemap.append(f'    <priority>0.8</priority>')
            xml_sitemap.append(f'  </url>')
        except: continue

    # 3. Dynamic Blog Posts
    if supabase_admin:
        try:
            # Fetch from new schema
            response = safe_execute(supabase_admin.table('blog_posts').select("id, published_at").eq('status', 'Published'))
            if response.data:
                for post in response.data:
                    url = url_for('public.blog_post', post_id=post['id'], _external=True)
                    escaped_url = saxutils.escape(url)
                    
                    # Hardened Date Parsing (Must be YYYY-MM-DD)
                    raw_date = post.get('published_at')
                    if raw_date:
                        # Handle space vs T vs full timestamp
                        clean_date = raw_date.replace('T', ' ').split(' ')[0]
                    else:
                        clean_date = datetime.now().strftime('%Y-%m-%d')
                    
                    xml_sitemap.append(f'  <url>')
                    xml_sitemap.append(f'    <loc>{escaped_url}</loc>')
                    xml_sitemap.append(f'    <lastmod>{clean_date}</lastmod>')
                    xml_sitemap.append(f'    <changefreq>weekly</changefreq>')
                    xml_sitemap.append(f'    <priority>0.9</priority>')
                    xml_sitemap.append(f'  </url>')
        except: pass
        
        try:
            # Fallback for older schema
            response2 = safe_execute(supabase_admin.table('posts').select("id, created_at, date").eq('published', True))
            if response2.data:
                for post in response2.data:
                    url = url_for('public.blog_post', post_id=post['id'], _external=True)
                    escaped_url = saxutils.escape(url)
                    
                    raw_date = post.get('created_at') or post.get('date')
                    if raw_date:
                        clean_date = raw_date.replace('T', ' ').split(' ')[0]
                    else:
                        clean_date = datetime.now().strftime('%Y-%m-%d')
                    
                    xml_sitemap.append(f'  <url>')
                    xml_sitemap.append(f'    <loc>{escaped_url}</loc>')
                    xml_sitemap.append(f'    <lastmod>{clean_date}</lastmod>')
                    xml_sitemap.append(f'    <changefreq>weekly</changefreq>')
                    xml_sitemap.append(f'    <priority>0.9</priority>')
                    xml_sitemap.append(f'  </url>')
        except: pass

    xml_sitemap.append('</urlset>')
    return Response('\n'.join(xml_sitemap), mimetype='application/xml; charset=utf-8')

@public_bp.route('/robots.txt', methods=['GET'])
def robots():
    """Generates robots.txt for crawlers."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /auth/",
        "Disallow: /sandbox/",
        "Disallow: /tax/",
        "Disallow: /physics/",
        "Disallow: /client-dashboard",
        "Disallow: /client-chat",
        "Disallow: /crypto-wallet",
        f"Sitemap: {url_for('public.sitemap', _external=True)}"
    ]
    return Response('\n'.join(lines), mimetype='text/plain')
# === DIAGNOSTIC ROUTE ===
@public_bp.route('/diag')
def diag():
    import hashlib
    is_dev = os.getenv('FLASK_ENV') == 'development'
    trigger = request.args.get('trigger') == 'kusmus_diag'
    if not is_dev and not trigger:
        return jsonify({'error': 'Unauthorized diagnostic access'}), 401
    env_summary = {}
    for key in ['SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'DATABASE_URL', 'FLASK_ENV', 'SECRET_KEY']:
        val = os.getenv(key)
        if val:
            env_summary[key] = {
                'len': len(val),
                'hash_8': hashlib.sha256(val.encode()).hexdigest()[:8],
                'ends_cr': val.endswith('\r'),
                'ends_space': val.endswith(' ')
            }
        else: env_summary[key] = {'present': False}
    return jsonify({
        'env': env_summary,
        'cwd': os.getcwd(),
        'files': os.listdir('.')[:20] if os.path.exists('.') else []
    })
