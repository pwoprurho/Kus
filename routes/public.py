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

@public_bp.route("/team")
def team():
    return render_template("our_team.html")

@public_bp.route("/method")
def method():
    return render_template("method.html")

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
            
            key_content = f"""-----BEGIN KUSMUS IDENTITY PROTOCOL-----
ISSUED_TO: {name}
REF_ID: {email}
DATE: {session.get('_creation_time', 'IMMEDIATE')}

PRIVATE_KEY_ACCESS_TOKEN:
{secure_hash_key}

INSTRUCTIONS:
1. Access the Client Portal at /auth/client-access
2. Authenticate using your Email and the PRIVATE_KEY_ACCESS_TOKEN above.
3. Keep this file offline. It is your only proof of identity.
-----END KUSMUS IDENTITY PROTOCOL-----
"""
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
            # 1. Decrypt Text
            if msg.get('encrypted_content'):
                msg['message'] = decrypt_text(msg['encrypted_content'])
                del msg['encrypted_content']
            else:
                msg['message'] = ""

            # 2. Generate Signed URL for Attachments (if any)
            if msg.get('attachment_url'):
                try:
                    # Create a temporary secure link (valid for 1 hour)
                    signed = supabase_admin.storage.from_('secure-files')\
                        .create_signed_url(msg['attachment_url'], 3600)
                    
                    # Supabase returns {'signedURL': '...'} or just the string depending on version
                    # We handle the dict response safely:
                    if isinstance(signed, dict) and 'signedURL' in signed:
                        msg['signed_attachment'] = signed['signedURL']
                    else:
                        msg['signed_attachment'] = signed # Fallback
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
    
    # Handle Form Data (Multipart)
    message_text = request.form.get('message', '')
    uploaded_file = request.files.get('file')
    
    if not message_text and not uploaded_file:
        return jsonify({'error': 'Empty transmission'}), 400

    try:
        attachment_path = None
        attachment_type = None

        # 1. Handle File Upload
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            # Create a unique path: client_id / random_hex / filename
            file_path = f"{client_id}/{secrets.token_hex(4)}_{filename}"
            content_type = uploaded_file.content_type
            
            # Read file bytes
            file_bytes = uploaded_file.read()
            
            # Upload to 'secure-files' bucket
            supabase_admin.storage.from_('secure-files').upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            
            attachment_path = file_path
            attachment_type = 'image' if 'image' in content_type else 'document'

        # 2. Encrypt Text
        encrypted_content = encrypt_text(message_text) if message_text else encrypt_text("[FILE ATTACHMENT]")

        # 3. Insert into Database
        supabase_admin.table('secure_chat_messages').insert({
            'client_id': client_id,
            'sender_type': 'client',
            'encrypted_content': encrypted_content,
            'attachment_url': attachment_path,  # Storing the path, not the public URL
            'attachment_type': attachment_type,
            'is_read': False
        }).execute()
        
        return jsonify({'status': 'sent'})
        
    except Exception as e:
        print(f"Send Error: {e}")
        return jsonify({'error': str(e)}), 500

# =========================================================
# === PUBLIC AI CHAT (Existing) ===
# =========================================================

@public_bp.route("/chat", methods=["POST"])
def chat_ai_assistant():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message: return jsonify({'error': 'No message provided'}), 400
    
    try:
        if not os.getenv("GEMINI_API_KEY"):
            return jsonify({'response': 'AI Core offline (Missing Key).'}), 500

        model = genai.GenerativeModel('gemini-2.5-flash')
        history = session.get('chat_history', [])
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message)

        new_history = []
        for content in chat.history:
            new_history.append({
                "role": content.role,
                "parts": [part.text for part in content.parts]
            })
        session['chat_history'] = new_history
        return jsonify({'response': response.text})

    except Exception as e:
        return jsonify({'response': 'Connection interrupted.'}), 500

@public_bp.route("/chat/reset", methods=["POST"])
def reset_chat():
    session.pop('chat_history', None)
    return jsonify({'status': 'success'})