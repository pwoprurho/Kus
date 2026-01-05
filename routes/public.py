
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

@public_bp.route("/sandbox")
def sandbox_home():
    raw = request.args.get('demo')
    # Resolve demo key safely: accept canonical keys or short aliases
    short_map = {'sentinel': 'sentinel_monitor', 'concierge': 'strategic_concierge', 'robotics': 'surge_vla'}
    def resolve(raw_demo):
        if not raw_demo: return None
        if raw_demo in DEMO_REGISTRY: return raw_demo
        if raw_demo in short_map: return short_map[raw_demo]
        safe = ''.join(c for c in raw_demo if c.isalnum() or c == '_')
        return short_map.get(safe)

    demo_key = resolve(raw)
    if demo_key:
        demo_entry = DEMO_REGISTRY.get(demo_key)
        return render_template("sandbox.html", demo_key=demo_key, demo_entry=demo_entry)

    # Otherwise render the demo selector and pass available demos
    return render_template("select_demo.html", demos=DEMO_REGISTRY)


@public_bp.route("/sandbox/view")
def sandbox_view():
    """Render the sandbox demo page. Accepts optional ?demo=<name> query param."""
    return render_template("sandbox.html")

@public_bp.route("/blog")
def blog():
    posts = []
    if supabase_admin:
        try:
            # Fetching published blog posts from Supabase
            response = supabase_admin.table('posts').select("*").eq('published', True).execute()
            posts = response.data
        except Exception as e:
            print(f"Blog Fetch Error: {e}")
    return render_template("blog.html", posts=posts)

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
            model_name=MAIN_ASSISTANT.get('model', 'gemini-2.0-flash-thinking-exp')
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