from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session, Response
from werkzeug.utils import secure_filename
import secrets
import os

# --- NEW IMPORTS ---
from core.security import encrypt_text, decrypt_text
from core.engine import KusmusAIEngine
from services.personas import MAIN_ASSISTANT

public_bp = Blueprint('public', __name__)

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

# =========================================================
# === BLOG / INSIGHTS ===
# =========================================================

@public_bp.route("/blog")
def blog():
    from app import supabase_admin
    posts = []
    if supabase_admin:
        try:
            # Added 'id' to the select query to ensure links work
            response = supabase_admin.table('blog_posts')\
                .select('id, title, summary, published_at')\
                .eq('status', 'Published')\
                .order('published_at', desc=True)\
                .execute()
            if response.data: posts = response.data
        except Exception as e: print(f"Blog Fetch Error: {e}")
    return render_template("blog.html", posts=posts)

@public_bp.route("/blog/<int:post_id>")
def blog_post(post_id):
    from app import supabase_admin
    post = None
    try:
        # Fetching by ID
        res = supabase_admin.table('blog_posts').select('*').eq('id', post_id).limit(1).execute()
        if res.data: post = res.data[0]
    except Exception as e: 
        print(f"Post Detail Error: {e}")
    
    if post and post.get('status') == 'Published':
        return render_template("blog_post.html", post=post)
    else:
        flash("Insight not found or access restricted.", "error")
        return redirect(url_for('public.blog'))

# =========================================================
# === STRATEGIC AUDIT ===
# =========================================================
@public_bp.route("/request-audit", methods=["GET", "POST"])
def audit_request():
    if request.method == "POST":
        from app import supabase_admin
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        
        if not name or not email:
            flash("Missing identification protocols.", "error")
            return redirect(url_for("public.audit_request"))
            
        try:
            raw_token = secrets.token_hex(32) 
            secure_hash_key = f"0x{raw_token}"

            data = {
                "name": name, "email": email, "message": message,
                "status": "Pending", "verification_code": secure_hash_key, "is_registered": False
            }
            supabase_admin.table("audit_requests").insert(data).execute()
            
            key_content = f"""-----BEGIN KUSMUS IDENTITY PROTOCOL-----\nISSUED_TO: {name}\nREF_ID: {email}\nDATE: {session.get('_creation_time', 'IMMEDIATE')}\n\nPRIVATE_KEY_ACCESS_TOKEN:\n{secure_hash_key}\n\nINSTRUCTIONS:\n1. Access the Client Portal at /auth/client-access\n2. Authenticate using your Email and the PRIVATE_KEY_ACCESS_TOKEN above.\n3. Keep this file offline. It is your only proof of identity.\n-----END KUSMUS IDENTITY PROTOCOL-----"""
            
            return Response(
                key_content,
                mimetype="text/plain",
                headers={"Content-Disposition": "attachment;filename=kusmus-private-key.txt"}
            )
        except Exception as e:
            print(f"Audit Error: {e}")
            flash("Transmission interrupted. Handshake failed.", "error")
            return redirect(url_for("public.audit_request"))
            
    return render_template("request_audit.html")

# =========================================================
# === SECURE DASHBOARD ===
# =========================================================

@public_bp.route("/secure-dashboard")
def client_dashboard():
    if not session.get('client_access'):
        flash("Unauthorized access attempt.", "error")
        return redirect(url_for('auth.client_access'))
    return render_template("client/client_dashboard.html")

@public_bp.route("/api/client/chat/sync", methods=["GET"])
def client_sync_chat():
    if not session.get('client_access'): return jsonify([]), 403
    client_id = session.get('client_id')
    if not client_id: return jsonify([]), 403

    from app import supabase_admin
    try:
        res = supabase_admin.table('secure_chat_messages').select('*').eq('client_id', client_id).order('created_at', desc=False).execute()
        messages = res.data if res.data else []
        
        for msg in messages:
            if msg.get('encrypted_content'):
                msg['message'] = decrypt_text(msg['encrypted_content'])
                del msg['encrypted_content']
            else:
                msg['message'] = ""

            if msg.get('attachment_url'):
                try:
                    signed = supabase_admin.storage.from_('secure-files').create_signed_url(msg['attachment_url'], 3600)
                    msg['signed_attachment'] = signed['signedURL'] if isinstance(signed, dict) and 'signedURL' in signed else signed
                except: msg['signed_attachment'] = None

        return jsonify(messages)
    except Exception as e:
        print(f"Sync Error: {e}")
        return jsonify([])

@public_bp.route("/api/client/chat/send", methods=["POST"])
def client_send_msg():
    if not session.get('client_access'): return jsonify({'error': 'Unauthorized'}), 403
    client_id = session.get('client_id')
    if not client_id: return jsonify({'error': 'Client ID missing'}), 403

    from app import supabase_admin
    message_text = request.form.get('message', '')
    uploaded_file = request.files.get('file')
    
    if not message_text and not uploaded_file: return jsonify({'error': 'Empty transmission'}), 400

    try:
        attachment_path = None
        attachment_type = None

        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            file_path = f"{client_id}/{secrets.token_hex(4)}_{filename}"
            supabase_admin.storage.from_('secure-files').upload(
                path=file_path,
                file=uploaded_file.read(),
                file_options={"content-type": uploaded_file.content_type}
            )
            attachment_path = file_path
            attachment_type = 'image' if 'image' in uploaded_file.content_type else 'document'

        final_message = message_text if message_text else "[FILE ATTACHMENT]"
        
        encrypted_content = encrypt_text(final_message)

        supabase_admin.table('secure_chat_messages').insert({
            'client_id': client_id,
            'sender_type': 'client',
            'encrypted_content': encrypted_content,
            'attachment_url': attachment_path,
            'attachment_type': attachment_type,
            'is_read': False
        }).execute()
        
        return jsonify({'status': 'sent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================================================
# === AI CHAT API ===
# =========================================================

@public_bp.route("/api/chat", methods=["POST"])
def chat_ai_assistant():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message: return jsonify({'error': 'No message provided'}), 400
    
    try:
        engine = KusmusAIEngine(
            system_instruction=MAIN_ASSISTANT['instruction'],
            model_name=MAIN_ASSISTANT['model']
        )
        
        raw_history = session.get('chat_history', [])
        response_text = engine.generate_response(user_message, history=raw_history)

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
    return jsonify({'status': 'success'})

@public_bp.route("/sandbox")
def sandbox_home():
    return render_template("sandbox.html")