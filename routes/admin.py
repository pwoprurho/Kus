from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_mail import Message
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from utils import role_required
import google.generativeai as genai
import os
import secrets
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/control-v3')

# =========================================================
# === ENCRYPTION & SECURITY UTILS ===
# =========================================================

def get_cipher_suite():
    """Retrieves the encryption key."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        # Fallback for dev safety
        return Fernet(Fernet.generate_key())
    return Fernet(key.encode())

def encrypt_text(text):
    """Encrypts database content."""
    try:
        if not text: return None
        return get_cipher_suite().encrypt(text.encode()).decode()
    except Exception as e:
        print(f"Encryption Error: {e}")
        return None

def decrypt_text(encrypted_text):
    """Decrypts database content."""
    try:
        if not encrypted_text: return ""
        return get_cipher_suite().decrypt(encrypted_text.encode()).decode()
    except Exception:
        return "[CONTENT LOCKED]"

# =========================================================
# === DASHBOARD (Command Center) ===
# =========================================================

@admin_bp.route('/')
@login_required
@role_required('supa_admin', 'admin', 'editor')
def dashboard():
    from app import supabase_admin
    audit_requests = []
    draft_posts = []

    try:
        # 1. Fetch Audit Requests (Leads)
        lead_res = supabase_admin.table('audit_requests').select('*').order('created_at', desc=True).limit(5).execute()
        if lead_res.data: audit_requests = lead_res.data

        # 2. Fetch Blog Posts (CMS)
        post_res = supabase_admin.table('blog_posts').select('*').order('created_at', desc=True).limit(10).execute()
        if post_res.data: draft_posts = post_res.data
            
    except Exception as e:
        print(f"Dashboard Data Error: {e}")
    
    return render_template('admin/dashboard.html', audit_requests=audit_requests, draft_posts=draft_posts)


# =========================================================
# === SECURE LIVE CHAT (ADMIN TERMINAL) ===
# =========================================================

@admin_bp.route('/live-chat')
@login_required
@role_required('supa_admin', 'admin')
def live_chat():
    from app import supabase_admin
    clients = []
    try:
        # Fetch all registered clients
        res = supabase_admin.table('clients').select('id, full_name, email').order('created_at', desc=True).execute()
        if res.data:
            clients = res.data
    except Exception as e:
        print(f"Chat Load Error: {e}")
        
    return render_template('admin/live_chat.html', clients=clients)

@admin_bp.route('/api/chat/<string:client_id>')
@login_required
def get_chat_history(client_id):
    """Fetches history, DECRYPTS text, and SIGNS file URLs for viewing."""
    from app import supabase_admin
    
    # 1. Fetch Client Email & Context
    audit_context = {'original_challenge': 'N/A', 'date_filed': 'N/A'}
    try:
        client_res = supabase_admin.table('clients').select('email').eq('id', client_id).single().execute()
        if client_res.data:
            client_email = client_res.data['email']
            # Fetch Audit Context
            audit_res = supabase_admin.table('audit_requests')\
                .select('message, created_at')\
                .eq('email', client_email)\
                .order('created_at', desc=True).limit(1).execute()
            if audit_res.data:
                audit_context['original_challenge'] = audit_res.data[0].get('message', 'N/A')
                audit_context['date_filed'] = audit_res.data[0].get('created_at', 'N/A').split('T')[0]
    except Exception:
        pass

    # 2. Fetch & Decrypt Conversation History (FROM SECURE TABLE)
    chat_history = []
    try:
        res = supabase_admin.table('secure_chat_messages')\
            .select('*')\
            .eq('client_id', client_id)\
            .order('created_at', desc=False)\
            .execute()
            
        if res.data:
            chat_history = res.data
            for msg in chat_history:
                # A. Decrypt Message Text
                msg['message'] = decrypt_text(msg['encrypted_content'])
                if 'encrypted_content' in msg:
                    del msg['encrypted_content']
                
                # B. Generate Signed URL for Attachments (Fixes visibility issue)
                if msg.get('attachment_url'):
                    try:
                        # Create a temporary secure link (valid for 1 hour)
                        signed = supabase_admin.storage.from_('secure-files')\
                            .create_signed_url(msg['attachment_url'], 3600)
                        
                        # Handle Supabase response format (dict vs string)
                        if isinstance(signed, dict) and 'signedURL' in signed:
                            msg['signed_attachment'] = signed['signedURL']
                        else:
                            msg['signed_attachment'] = signed
                    except Exception as ex:
                        print(f"Signing Error: {ex}")
                        msg['signed_attachment'] = None
                        
    except Exception as e:
        print(f"Chat History Error: {e}")

    return jsonify({
        'history': chat_history,
        'context': audit_context
    })

@admin_bp.route('/api/chat/send', methods=['POST'])
@login_required
def send_admin_message():
    """Handles Admin Text AND File Uploads."""
    from app import supabase_admin
    
    # Use form data to support file uploads
    client_id = request.form.get('client_id')
    text = request.form.get('message')
    uploaded_file = request.files.get('file')
    
    admin_id = current_user.id 
    
    if not client_id or (not text and not uploaded_file):
        return jsonify({'error': 'Missing data'}), 400
    
    try:
        attachment_path = None
        attachment_type = None

        # 1. Handle Admin File Upload
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            # Save in admin subfolder: client_id/admin_uploads/filename
            file_path = f"{client_id}/admin_uploads/{secrets.token_hex(4)}_{filename}"
            content_type = uploaded_file.content_type
            
            # Read and upload
            file_bytes = uploaded_file.read()
            
            supabase_admin.storage.from_('secure-files').upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            
            attachment_path = file_path
            attachment_type = 'image' if 'image' in content_type else 'document'

        # 2. Encrypt Text (or placeholder if only file sent)
        final_text = text if text else "[FILE SENT]"
        encrypted_content = encrypt_text(final_text)
        
        if not encrypted_content: 
            return jsonify({'error': 'Encryption Failed'}), 500

        # 3. Insert into SECURE TABLE
        supabase_admin.table('secure_chat_messages').insert({
            'client_id': client_id,
            'admin_id': admin_id,
            'sender_type': 'admin',
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
# === CMS & LEAD MANAGEMENT (PRESERVED) ===
# =========================================================

@admin_bp.route('/lead/reply/<string:lead_id>')
@login_required
@role_required('supa_admin', 'admin')
def reply_lead(lead_id):
    from app import supabase_admin, mail 
    try:
        res = supabase_admin.table('audit_requests').select('name, email').eq('id', lead_id).limit(1).execute()
        if not res.data: return redirect(url_for('admin.dashboard'))
        lead = res.data[0]
        
        msg = Message(
            subject=f"Protocol Acknowledged: Your Kusmus AI Strategic Audit Request",
            recipients=[lead['email']],
            body=f"""Dear {lead['name']},\n\nThank you for contacting Kusmus AI. This automated response confirms we have securely received your request.\n\nReference ID: #{lead_id}\n\n---\nKusmus AI Strategy Team"""
        )
        # mail.send(msg) 
        flash(f"Automated reply sent to {lead['email']} (Simulated).", "success")
    except Exception as e:
        flash("Automated email transmission failed.", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/post/new', methods=['GET', 'POST'])
@login_required
@role_required('supa_admin', 'admin', 'editor')
def new_post():
    from app import supabase_admin
    if request.method == 'POST':
        try:
            supabase_admin.table('blog_posts').insert({
                "title": request.form.get('title'), "summary": request.form.get('summary'),
                "content_html": request.form.get('content'), "author_id": current_user.id, "status": "Draft"
            }).execute()
            flash("Insight created successfully.", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e: flash(f"Error saving post: {e}", "error")
    return render_template('admin/new_post.html', post=None)

@admin_bp.route('/post/edit/<string:post_id>', methods=['GET', 'POST'])
@login_required
@role_required('supa_admin', 'admin', 'editor')
def edit_post(post_id):
    from app import supabase_admin
    if request.method == 'POST':
        try:
            supabase_admin.table('blog_posts').update({
                "title": request.form.get('title'), "summary": request.form.get('summary'),
                "content_html": request.form.get('content'), "updated_at": "now()"
            }).eq('id', post_id).execute()
            flash("Insight updated successfully.", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e: flash(f"Error updating post: {e}", "error")

    try:
        res = supabase_admin.table('blog_posts').select('*').eq('id', post_id).limit(1).execute()
        if res.data: post = res.data[0]
        else: return redirect(url_for('admin.dashboard'))
    except Exception: return redirect(url_for('admin.dashboard'))
    return render_template('admin/new_post.html', post=post)

@admin_bp.route('/post/publish/<string:post_id>')
@login_required
@role_required('supa_admin', 'admin', 'editor')
def publish_post(post_id):
    from app import supabase_admin
    try:
        supabase_admin.table('blog_posts').update({"status": "Published", "published_at": "now()"}).eq('id', post_id).execute()
        flash("Insight deployed to live site.", "success")
    except Exception as e: flash(f"Deploy failed: {e}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/post/delete/<string:post_id>')
@login_required
@role_required('supa_admin', 'admin')
def delete_post(post_id):
    from app import supabase_admin
    try:
        supabase_admin.table('blog_posts').delete().eq('id', post_id).execute()
        flash("Insight deleted permanently.", "info")
    except Exception as e: flash(f"Delete failed: {str(e)}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/lead/view/<string:lead_id>')
@login_required
@role_required('supa_admin', 'admin', 'editor')
def view_lead(lead_id):
    from app import supabase_admin
    try:
        res = supabase_admin.table('audit_requests').select('*').eq('id', lead_id).limit(1).execute()
        if res.data: lead = res.data[0]
        else: return redirect(url_for('admin.dashboard'))
    except Exception: return redirect(url_for('admin.dashboard'))
    return render_template('admin/view_lead.html', lead=lead)

@admin_bp.route('/lead/delete/<string:lead_id>')
@login_required
@role_required('supa_admin', 'admin')
def delete_lead(lead_id):
    from app import supabase_admin
    try:
        supabase_admin.table('audit_requests').delete().eq('id', lead_id).execute()
        flash("Lead removed from database.", "info")
    except Exception as e: flash(f"Delete failed: {e}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/generate', methods=['POST'])
@login_required
def generate_content():
    data = request.get_json()
    try:
        if not os.getenv("GEMINI_API_KEY"): return jsonify({'error': 'Gemini API Key missing'}), 500
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Write a blog post about {data.get('topic')}. Return ONLY JSON with 'summary' and 'content' keys."""
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return jsonify(json.loads(response.text))
    except Exception as e: return jsonify({'error': str(e)}), 500