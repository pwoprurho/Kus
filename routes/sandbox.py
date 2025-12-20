import json
import os
from flask import Blueprint, request, jsonify
from core.engine import KusmusAIEngine
from services.personas import DEMO_REGISTRY

sandbox_bp = Blueprint('sandbox', __name__)

@sandbox_bp.route("/api/sandbox/chat", methods=["POST"])
def sandbox_chat():
    from app import supabase_admin
    
    # 1. DATA EXTRACTION
    # Handles both standard JSON and FormData (for file uploads)
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
        demo_id = data.get('demo_id', 'strategic_concierge')
        user_message = data.get('message', '').strip()
        history_raw = data.get('history', [])
        uploaded_file = None
    else:
        demo_id = request.form.get('demo_id', 'strategic_concierge')
        user_message = request.form.get('message', '').strip()
        history_raw = request.form.get('history', '[]')
        uploaded_file = request.files.get('file')

    # Parse History
    try:
        history = json.loads(history_raw) if isinstance(history_raw, str) else history_raw
    except:
        history = []

    # 2. FILE CONTEXT INTEGRATION
    if uploaded_file:
        # In a demo context, we inform the AI that a file was provided
        user_message += f"\n\n[SYSTEM NOTIFICATION: User has uploaded file '{uploaded_file.filename}' for your analysis. Use your specialized training to interpret any technical logs or data within.]"

    if not user_message and not uploaded_file:
        return jsonify({'error': 'Directive required.'}), 400

    # 3. PROTOCOL LOOKUP
    persona = DEMO_REGISTRY.get(demo_id)
    if not persona:
        return jsonify({'error': 'Neural protocol undefined.'}), 404

    # 4. TELEMETRY LOGGING
    try:
        if supabase_admin:
            supabase_admin.table('sandbox_logs').insert({
                'persona_id': demo_id,
                'user_message_length': len(user_message),
                'has_attachment': bool(uploaded_file)
            }).execute()
    except Exception as e:
        print(f"Telemetry Error: {e}")

    # 5. EXECUTION
    try:
        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona['model']
        )
        
        # Engine returns tuple: (response_text, thought_trace)
        response_text, thought_trace = engine.generate_response(user_message, history=history)
        
        return jsonify({
            'response': response_text,
            'thought_trace': thought_trace,
            'persona_name': persona['name'],
            'status': 'linked'
        })
    except Exception as e:
        print(f"Engine Failure: {e}")
        return jsonify({'error': "Neural link timeout. Quota or API handshake issue."}), 500