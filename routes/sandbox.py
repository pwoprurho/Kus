# routes/sandbox.py
import json
import os
from flask import Blueprint, request, jsonify, session
from core.engine import KusmusAIEngine
from core.security import sign_forensic_trace # NEW
from services.personas import DEMO_REGISTRY
from services.vanguard import calculate_vanguard_score, get_lead_tier
from services.mcp_tools import MCP_TOOLKIT

sandbox_bp = Blueprint('sandbox', __name__)

@sandbox_bp.route("/api/sandbox/chat", methods=["POST"])
def sandbox_chat():
    from app import supabase_admin
    
    # 1. DATA EXTRACTION
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
        demo_id = data.get('demo_id', 'sentinel_monitor')
        user_message = data.get('message', '').strip()
        history_raw = data.get('history', [])
        context_logs = data.get('context_logs', []) # NEW: Get logs from frontend
        uploaded_file = None
    else:
        # Fallback for form data
        demo_id = request.form.get('demo_id', 'sentinel_monitor')
        user_message = request.form.get('message', '').strip()
        history_raw = request.form.get('history', '[]')
        context_logs = []
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

    # 5. EXECUTION WITH THINKING ENGINE
    try:
        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona['model'] # Ensure this is gemini-2.0-flash-thinking-exp in personas.py
        )
        
        # Pass logs and tools to the new engine
        response_text, thought_trace = engine.generate_response(
            user_message, 
            history=history,
            context_logs=context_logs,
            tools=MCP_TOOLKIT 
        )

        # 6. SIGNATURE & INTERCEPT
        trace_sig, _ = sign_forensic_trace(thought_trace, user_message)

        # Premium Intercept: If they are a 'Whale' and we fixed a problem, sell the audit.
        if new_score > 75 and "SUCCESS" in response_text:
            response_text += (
                "\n\n[SYSTEM_NOTE]: Mitigation successful. "
                "I have generated a signed forensic trace of this incident. "
                "I recommend a Phase 1 Formal Audit to secure the logs. "
                "Shall I generate the request?"
            )
        
        # 7. LOGGING (Supabase)
        if supabase_admin:
            supabase_admin.table('sandbox_logs').insert({
                'persona_id': demo_id,
                'user_message_length': len(user_message),
                'vanguard_score': new_score,
                'lead_tier': lead_tier,
                'trace_signature': trace_sig
            }).execute()
        
        return jsonify({
            'response': response_text,
            'thought_trace': thought_trace,
            'trace_signature': trace_sig,
            'v_score': new_score,
            'tier': lead_tier,
            'status': 'linked'
        })

    except Exception as e:
        print(f"Engine Error: {e}")
        return jsonify({'error': "Neural link timeout."}), 500