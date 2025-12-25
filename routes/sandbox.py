import json
import os
from flask import Blueprint, request, jsonify, session
from core.engine import KusmusAIEngine
from services.personas import DEMO_REGISTRY
from services.vanguard import calculate_vanguard_score, get_lead_tier
from services.mcp_tools import MCP_TOOLKIT  # NEW: Import Toolkit

sandbox_bp = Blueprint('sandbox', __name__)

@sandbox_bp.route("/api/sandbox/chat", methods=["POST"])
def sandbox_chat():
    from app import supabase_admin
    
    # 1. DATA EXTRACTION
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

    try:
        history = json.loads(history_raw) if isinstance(history_raw, str) else history_raw
    except:
        history = []

    # 2. VANGUARD LEAD SCORING
    current_score = session.get('vanguard_score', 0)
    new_score = calculate_vanguard_score(user_message, bool(uploaded_file), current_score)
    session['vanguard_score'] = new_score
    lead_tier = get_lead_tier(new_score)

    # 3. FILE CONTEXT INTEGRATION
    if uploaded_file:
        user_message += f"\n\n[SYSTEM NOTIFICATION: User has uploaded file '{uploaded_file.filename}']"

    if not user_message and not uploaded_file:
        return jsonify({'error': 'Directive required.'}), 400

    # 4. PERSONA SELECTION
    persona = DEMO_REGISTRY.get(demo_id)
    if not persona:
        return jsonify({'error': 'Neural protocol undefined.'}), 404

    # 5. TELEMETRY LOGGING
    try:
        if supabase_admin:
            supabase_admin.table('sandbox_logs').insert({
                'persona_id': demo_id,
                'user_message_length': len(user_message),
                'has_attachment': bool(uploaded_file),
                'vanguard_score': new_score,
                'lead_tier': lead_tier
            }).execute()
    except Exception as e:
        print(f"Telemetry Error: {e}")

    # 6. EXECUTION
    try:
        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona['model']
        )
        
        # FIX: Pass the MCP_TOOLKIT to the engine so it can execute tools
        response_text, thought_trace = engine.generate_response(
            user_message, 
            history=history,
            tools=MCP_TOOLKIT 
        )
        
        return jsonify({
            'response': response_text,
            'thought_trace': thought_trace,
            'v_score': new_score,
            'tier': lead_tier,
            'status': 'linked'
        })
    except Exception as e:
        print(f"Engine Error: {e}")
        return jsonify({'error': "Neural link timeout."}), 500