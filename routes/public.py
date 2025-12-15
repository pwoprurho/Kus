from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session, Response
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
import google.generativeai as genai
import os
import secrets
import json

# Define the Public Blueprint
public_bp = Blueprint('public', __name__)

# =========================================================
# === HIGH-LEVEL ENCRYPTION ENGINE (AES-128 via Fernet) ===
# =========================================================

def get_cipher_suite():
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        print("WARNING: 'ENCRYPTION_KEY' not found. Using ephemeral key.")
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode())

def encrypt_text(text):
    try:
        if not text: return None
        cipher = get_cipher_suite()
        return cipher.encrypt(text.encode()).decode()
    except Exception as e:
        print(f"Encryption Failure: {e}")
        return None

def decrypt_text(encrypted_text):
    try:
        if not encrypted_text: return ""
        cipher = get_cipher_suite()
        return cipher.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        return "[CONTENT LOCKED]"

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
        res = supabase_admin.table('blog_posts').select('*').eq('id', post_id).limit(1).execute()
        if res.data: post = res.data[0]
    except: pass
    
    if post and post.get('status') == 'Published':
        return render_template("blog_post.html", post=post)
    else:
        flash("Insight not found or access restricted.", "error")
        return redirect(url_for('public.blog'))

# =========================================================
# === STRATEGIC AUDIT & KEY GENERATION ===
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
# === SECURE DASHBOARD & ENCRYPTED CHAT API ===
# =========================================================

@public_bp.route("/secure-dashboard")
def client_dashboard():
    if not session.get('client_access'):
        flash("Unauthorized access attempt.", "error")
        return redirect(url_for('auth.client_access'))
    return render_template("client/client_dashboard.html")

@public_bp.route("/api/client/chat/sync", methods=["GET"])
def client_sync_chat():
    """Fetches DECRYPTED history + Generates Signed URLs for files."""
    if not session.get('client_access'): return jsonify([]), 403
    
    client_id = session.get('client_id')
    if not client_id: return jsonify([]), 403

    from app import supabase_admin
    try:
        res = supabase_admin.table('secure_chat_messages')\
            .select('*')\
            .eq('client_id', client_id)\
            .order('created_at', desc=False)\
            .execute()
        
        messages = res.data if res.data else []
        
        for msg in messages:
            if msg.get('encrypted_content'):
                msg['message'] = decrypt_text(msg['encrypted_content'])
                del msg['encrypted_content']
            else:
                msg['message'] = ""

            if msg.get('attachment_url'):
                try:
                    signed = supabase_admin.storage.from_('secure-files')\
                        .create_signed_url(msg['attachment_url'], 3600)
                    
                    if isinstance(signed, dict) and 'signedURL' in signed:
                        msg['signed_attachment'] = signed['signedURL']
                    else:
                        msg['signed_attachment'] = signed
                except Exception as ex:
                    print(f"Signing Error: {ex}")
                    msg['signed_attachment'] = None

        return jsonify(messages)
    except Exception as e:
        print(f"Sync Error: {e}")
        return jsonify([])

@public_bp.route("/api/client/chat/send", methods=["POST"])
def client_send_msg():
    """Handles Text (Encrypted) AND File Uploads."""
    if not session.get('client_access'): return jsonify({'error': 'Unauthorized'}), 403
    
    client_id = session.get('client_id')
    if not client_id: return jsonify({'error': 'Client ID missing'}), 403

    from app import supabase_admin
    
    message_text = request.form.get('message', '')
    uploaded_file = request.files.get('file')
    
    if not message_text and not uploaded_file:
        return jsonify({'error': 'Empty transmission'}), 400

    try:
        attachment_path = None
        attachment_type = None

        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            file_path = f"{client_id}/{secrets.token_hex(4)}_{filename}"
            content_type = uploaded_file.content_type
            
            file_bytes = uploaded_file.read()
            
            supabase_admin.storage.from_('secure-files').upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            
            attachment_path = file_path
            attachment_type = 'image' if 'image' in content_type else 'document'

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
        print(f"Send Error: {e}")
        return jsonify({'error': str(e)}), 500

# =========================================================
# === PUBLIC AI CHAT API (WIDGET BACKEND) ===
# =========================================================

@public_bp.route("/api/chat", methods=["POST"])
def chat_ai_assistant():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message: return jsonify({'error': 'No message provided'}), 400
    
    try:
        # 1. Verify API Key
        if not os.getenv("GEMINI_API_KEY"):
            return jsonify({'error': 'System Error: AI Key Missing'}), 500
        
        # 2. Configure Model (CORRECTED MODEL NAME)
        SYSTEM_INSTRUCTION = (
            "You are the 'Kusmus AI Client Care Assistant.' "
            "Your tone is premium, polite, and authoritative ('Engineering Certainty'). "
            "Function: Provide quick, accurate answers about company services. "
            "Direct users to: Solutions, Audit Request, or Client Portal. "
            "Keep answers short and professional."
        )

        # FIX: Changed from 'gemini-2.5-flash' to 'gemini-1.5-flash'
        model = genai.GenerativeModel(
            'gemini-2.5-flash', 
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # 3. Handle History (Using Simple Dictionaries)
        raw_history = session.get('chat_history', [])
        formatted_history = []
        
        # Ensure history is in the correct format for the SDK
        for turn in raw_history:
            if 'role' in turn and 'parts' in turn:
                formatted_history.append({
                    "role": turn['role'],
                    "parts": turn['parts']
                })

        # 4. Generate Response
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_message)

        # 5. Save History (Serializable Format)
        new_turn_user = {"role": "user", "parts": [user_message]}
        new_turn_model = {"role": "model", "parts": [response.text]}
        
        formatted_history.append(new_turn_user)
        formatted_history.append(new_turn_model)
        
        session['chat_history'] = formatted_history
        
        return jsonify({'response': response.text})

    except Exception as e:
        # Logs specific error to console for debugging
        print(f"AI Chat Error: {e}")
        return jsonify({'error': 'Connection interrupted or System Integrity compromised.'}), 500

@public_bp.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    session.pop('chat_history', None)
    return jsonify({'status': 'success'})

@public_bp.route("/chat", methods=["POST"])
def old_chat_redirect():
    return redirect(url_for('public.chat_ai_assistant'), code=307)