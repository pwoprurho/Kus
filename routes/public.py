
import json
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from core.engine import KusmusAIEngine
from services.personas import MAIN_ASSISTANT, DEMO_REGISTRY
from db import supabase_admin

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
            response = supabase_admin.table('blog_posts').select("*").eq('status', 'Published').order('published_at', desc=True).execute()
            posts = response.data
        except Exception as e:
            print(f"Blog Fetch Error: {e}")
            # Fallback for older schema if migration isn't complete (optional, but good for safety)
            try:
                response = supabase_admin.table('posts').select("*").eq('published', True).execute()
                if response.data: posts.extend(response.data)
            except: pass

    return render_template("blog.html", posts=posts)

@public_bp.route("/blog/<string:post_id>")
def blog_post(post_id):
    post = None
    if supabase_admin:
        try:
            # Fetch single post from correct table
            response = supabase_admin.table('blog_posts').select("*").eq('id', post_id).limit(1).execute()
            if response.data:
                post = response.data[0]
            else:
                 # Fallback check
                response = supabase_admin.table('posts').select("*").eq('id', post_id).limit(1).execute()
                if response.data: post = response.data[0]

        except Exception as e:
            print(f"Blog Post Fetch Error: {e}")
            
    if not post:
        return render_template("404.html"), 404
        
    return render_template("blog_post.html", post=post)

# --- FIX: Added missing route to resolve BuildError in index.html ---
@public_bp.route("/request-audit")
def audit_request():
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
        # Initialize Engine with the Client Care Persona
        engine = KusmusAIEngine(
            system_instruction=MAIN_ASSISTANT['instruction'],
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