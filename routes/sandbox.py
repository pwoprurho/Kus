# routes/sandbox.py
import json
import os
from flask import Blueprint, request, jsonify, session, render_template, redirect
from utils import role_required
# routes/sandbox.py
from core.engine import KusmusAIEngine
from core.security import sign_forensic_trace
from services.personas import DEMO_REGISTRY
from services.vanguard import calculate_vanguard_score, get_security_posture, get_latency_metrics
from services.vanguard import get_threat_level
import datetime
from db import supabase_admin

sandbox_bp = Blueprint('sandbox', __name__)


@sandbox_bp.route("/sandbox")
def sandbox_view():
    """
    Handles the transition from select_demo to the actual sandbox.
    Includes Phase 4 Mobile Gate and Session Initialization.
    """
    # 1. MOBILE GATE
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(x in user_agent for x in ['iphone', 'android', 'blackberry', 'windowsphone'])
    if is_mobile:
        return render_template('demo_mobile.html')

    # 2. DEMO VALIDATION & RESOLUTION
    short_map = {
        'sentinel': 'sentinel_monitor',
        'concierge': 'strategic_concierge',
        'robotics': 'surge_vla'
    }

    selected_demo = request.args.get('demo', '')

    def resolve_demo_key(raw):
        if not raw:
            return 'sentinel_monitor'
        if raw in DEMO_REGISTRY:
            return raw
        if raw in short_map:
            return short_map[raw]
        # sanitize: allow only alphanumeric and underscore
        safe = ''.join(c for c in raw if c.isalnum() or c == '_')
        return short_map.get(safe, 'sentinel_monitor')

    backend_id = resolve_demo_key(selected_demo)

    # Store in session for the API chat route to reference
    session['active_demo_id'] = backend_id
    session['v_score'] = 100

    return render_template('sandbox.html', demo_key=backend_id)


@sandbox_bp.route("/api/sandbox/chat", methods=["POST"])
def sandbox_chat():
    try:
        data = request.get_json()
        # Use session-stored ID if not provided in JSON
        demo_id = data.get('demo_id') or session.get('active_demo_id', 'sentinel_monitor')
        user_message = data.get('message', '').strip()
        context_logs = data.get('context_logs', [])

        persona = DEMO_REGISTRY.get(demo_id, DEMO_REGISTRY['sentinel_monitor'])

        # --- RAG for Tax Accountant Persona ---
        if demo_id == "strategic_concierge":
            try:
                from rag_tax_law import search_tax_law
                rag_chunks = search_tax_law(user_message, supabase_admin, top_k=3)
                if rag_chunks and isinstance(rag_chunks, list):
                    law_context = "\n\n--- Relevant Nigeria Tax Law Excerpts ---\n"
                    for c in rag_chunks:
                        page = c.get('page_num', '?')
                        chunk = c.get('chunk_text', '')
                        law_context += f"[Page {page}] {chunk}\n"
                    user_message_aug = f"{user_message}\n{law_context}"
                else:
                    user_message_aug = user_message
            except Exception as e:
                user_message_aug = user_message + f"\n[Tax Law RAG Error: {str(e)}]"
        else:
            user_message_aug = user_message

        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona.get('model', 'gemini-2.5-flash-thinking-exp')
        )

        response_text, thought_trace = engine.generate_response(user_message_aug, context_logs=context_logs)

        # Build a demo-specific log entry using persona log signature if present
        demo_log = None
        if 'log_signature' in persona:
            ts = datetime.datetime.utcnow().strftime('%H:%M:%S')
            demo_log = f"[{ts}] {persona['log_signature']}"
            # append to session context logs for continuity
            context_logs.append(demo_log)
            # keep only recent 50
            session['context_logs'] = context_logs[-50:]

        is_mitigated = any(x in response_text.upper() for x in ["SUCCESS", "MITIGATED", "NEUTRALIZED"])

        current_score = session.get('v_score', 100)
        new_score = calculate_vanguard_score(
            current_score=current_score,
            context_logs=context_logs,
            is_mitigated=is_mitigated
        )
        session['v_score'] = new_score
        threat_level = get_threat_level(new_score, context_logs)

        # Decide on self-heal: always run when vanguard score drops below 50,
        # and also run after positive mitigation when posture indicates secured.
        self_heal_result = None
        posture = get_security_posture(new_score)

        # Always trigger self-heal automatically if score indicates high risk
        if new_score < 50:
            try:
                from services.mcp_tools import perform_self_heal
                self_heal_result = perform_self_heal(demo_id)
            except Exception:
                self_heal_result = {'status': 'FAILED', 'actions': []}

            # Append self-heal summary to logs and session
            if self_heal_result:
                sh_log = f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [AUTO_SELF_HEAL_LOW_VS] {self_heal_result.get('status')}"
                context_logs.append(sh_log)
                session['context_logs'] = context_logs[-200:]

        # Also run self-heal after mitigation if posture indicates secured
        elif is_mitigated and (new_score >= 90 or posture.startswith('SECURED')):
            try:
                self_heal_result = perform_self_heal(demo_id)
                if self_heal_result:
                    sh_log = f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] [SELF_HEAL] {self_heal_result.get('status')}"
                    context_logs.append(sh_log)
                    session['context_logs'] = context_logs[-200:]
            except Exception:
                self_heal_result = {'status': 'FAILED', 'actions': []}

        # Persist telemetry immediately (signed) and ALWAYS append to local file.
        telemetry_saved = False
        wrote_local = False
        try:
            sig, signed_payload = sign_forensic_trace(thought_trace, user_message)
            telemetry_record = {
                'demo_id': demo_id,
                'demo_log': demo_log,
                'thought_trace': json.dumps(thought_trace),
                'context_logs': json.dumps(context_logs),
                'v_score': new_score,
                'threat_level': threat_level,
                'signature': sig,
                'signed_payload': json.dumps(signed_payload),
                'client_ts': data.get('client_send_ts'),
                'rtt': None,
                'self_heal': json.dumps(self_heal_result) if self_heal_result else None,
                'created_at': datetime.datetime.utcnow().isoformat()
            }
            
            if supabase_admin:
                try:
                    supabase_admin.table('sandbox_telemetry').insert(telemetry_record).execute()
                    telemetry_saved = True
                except Exception:
                    telemetry_saved = False

            # Always append to local file as a durable fallback and audit trail.
            try:
                os.makedirs('data', exist_ok=True)
                # prefix each local telemetry line with demo_id to make grepping by target easier
                with open('data/sandbox_telemetry.log', 'a', encoding='utf-8') as f:
                    f.write(f"{demo_id} " + json.dumps(telemetry_record) + '\n')
                wrote_local = True
            except Exception:
                wrote_local = False

        except Exception:
            telemetry_saved = False
            wrote_local = False

        return jsonify({
            'response': response_text,
            'thought_trace': thought_trace,
            'demo_log': demo_log,
            'self_heal': self_heal_result,
            'v_score': new_score,
            'threat_level': threat_level,
            'status': get_security_posture(new_score),
            'latency': get_latency_metrics(context_logs),
            'telemetry_saved': telemetry_saved,
            'telemetry_written_local': wrote_local
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@sandbox_bp.route('/api/sandbox/telemetry', methods=['POST'])
def persist_telemetry():
    """Persist telemetry (thought_trace, logs, v_score, threat_level) to Supabase or local file fallback."""
    try:
        payload = request.get_json() or {}
        demo_id = payload.get('demo_id') or session.get('active_demo_id', 'sentinel_monitor')
        user_message = payload.get('user_message', '')
        thought_trace = payload.get('thought_trace', [])
        context_logs = payload.get('context_logs', [])
        v_score = payload.get('v_score')
        threat_level = payload.get('threat_level')
        client_ts = payload.get('client_send_ts')
        rtt = payload.get('rtt')
        demo_log = payload.get('demo_log')
        self_heal = payload.get('self_heal')

        # Create tamper-proof signature for reasoning
        signature, signed_payload = sign_forensic_trace(thought_trace, user_message)

        record = {
            'demo_id': demo_id,
            'demo_log': demo_log,
            'thought_trace': json.dumps(thought_trace),
            'context_logs': json.dumps(context_logs),
            'v_score': v_score,
            'threat_level': threat_level,
            'signature': signature,
            'signed_payload': json.dumps(signed_payload),
            'client_ts': client_ts,
            'rtt': rtt,
            'self_heal': json.dumps(self_heal) if self_heal else None,
            'created_at': datetime.datetime.utcnow().isoformat()
        }

        # import supabase client lazily to avoid circular import with app

        # Try to insert to Supabase if available; always append locally as well.
        try:
            if supabase_admin:
                try:
                    supabase_admin.table('sandbox_telemetry').insert(record).execute()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            os.makedirs('data', exist_ok=True)
            # prefix each local telemetry line with demo_id for quick identification
            with open('data/sandbox_telemetry.log', 'a', encoding='utf-8') as f:
                f.write(f"{record.get('demo_id','unknown')} " + json.dumps(record) + '\n')
        except Exception:
            # nothing more we can do here; return success to caller
            pass

        return jsonify({'status': 'ok', 'signature': signature})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@sandbox_bp.route('/api/mcp/invoke', methods=['POST'])
def invoke_mcp_tool():
    """Invoke a whitelisted MCP tool from the server-side toolkit."""
    try:
        payload = request.get_json() or {}
        tool = payload.get('tool')
        args = payload.get('args', {})
        # lazy import registry
        from services.mcp_tools import MCP_TOOLKIT
        fn = MCP_TOOLKIT.get(tool)
        if not fn:
            return jsonify({'error': 'unknown_tool', 'tool': tool}), 400

        # allow either dict kwargs or list/tuple positional args
        if isinstance(args, dict):
            result = fn(**args)
        elif isinstance(args, (list, tuple)):
            result = fn(*args)
        else:
            result = fn(args)

        # append result to session logs and return
        session_logs = session.get('context_logs', [])
        session_logs.append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] TOOL:{tool} => {str(result)[:200]}")
        session['context_logs'] = session_logs[-200:]

        return jsonify({'status': 'ok', 'tool': tool, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Calendar admin endpoints moved to routes/admin.py