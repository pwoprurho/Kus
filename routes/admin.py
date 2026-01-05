import os
import json
import secrets
import datetime
import google.generativeai as genai
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_mail import Message
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from db import supabase_admin
from utils import role_required, get_cipher_suite, encrypt_text, decrypt_text
from core.key_manager import key_manager

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# =========================================================
# === DASHBOARD (Command Center) ===
# =========================================================

@admin_bp.route('/')
@login_required
@role_required('supa_admin', 'admin', 'editor')
def dashboard():
    
    # Pagination Logic for Sandbox Logs
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page - 1

    audit_requests = []
    draft_posts = []
    sandbox_logs = []
    sandbox_count = 0

    try:
        # 1. Fetch Audit Requests (Leads)
        lead_res = supabase_admin.table('audit_requests').select('*').order('created_at', desc=True).limit(5).execute()
        if lead_res.data: audit_requests = lead_res.data

        # 2. FIX: Fetch ALL Blog Posts (Published & Draft)
        post_res = supabase_admin.table('blog_posts').select('*').order('created_at', desc=True).execute()
        if post_res.data: draft_posts = post_res.data

        # 3. Fetch Paged Sandbox Logs
        log_res = supabase_admin.table('sandbox_logs').select('*').order('created_at', desc=True).range(start, end).execute()
        if log_res.data: sandbox_logs = log_res.data

        # 4. Total Count for Pagination and Stats
        stats_res = supabase_admin.table('sandbox_logs').select('id', count='exact').execute()
        sandbox_count = stats_res.count if stats_res.count else 0
            
    except Exception as e:
        print(f"Dashboard Data Error: {e}")
    
    return render_template('admin/dashboard.html', 
                           audit_requests=audit_requests, 
                           draft_posts=draft_posts, 
                           sandbox_logs=sandbox_logs,
                           sandbox_count=sandbox_count,
                           current_page=page,
                           total_pages=(sandbox_count // per_page) + 1)
# =========================================================
# === SANDBOX ANALYTICS ===
# =========================================================

@admin_bp.route('/sandbox-analytics')
@login_required
@role_required('supa_admin', 'admin')
def sandbox_analytics():
    """Complete view of AI Sandbox engagement metrics."""
    analytics = {'total_interactions': 0, 'persona_distribution': {}, 'recent_activity': []}

    try:
        res = supabase_admin.table('sandbox_logs').select('*').order('created_at', desc=True).limit(100).execute()
        if res.data:
            analytics['total_interactions'] = len(res.data)
            for entry in res.data:
                p_id = entry['persona_id']
                analytics['persona_distribution'][p_id] = analytics['persona_distribution'].get(p_id, 0) + 1
            analytics['recent_activity'] = res.data[:15]
    except Exception as e:
        flash("Could not retrieve real-time sandbox metrics.", "error")

    return render_template('admin/sandbox_stats.html', stats=analytics)


# =========================================================
# === SUPA ADMIN INTERFACE (Privilege Management + Zoho Chat)
# =========================================================


@admin_bp.route('/supa-admin')
@login_required
@role_required('supa_admin')
def supa_admin():
    users = []
    try:
        res = supabase_admin.table('users').select('id, full_name, email, role').order('created_at', desc=False).execute()
        if res.data: users = res.data
    except Exception as e:
        print(f"Load Supa Admin Users Error: {e}")
    return render_template('admin/supa_admin.html', users=users)


@admin_bp.route('/supa-admin/modify-role', methods=['POST'])
@login_required
@role_required('supa_admin')
def modify_role():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    new_role = data.get('new_role')
    if not user_id or not new_role:
        return jsonify({'error': 'Missing parameters'}), 400
    try:
        supabase_admin.table('users').update({'role': new_role}).eq('id', user_id).execute()
        return jsonify({'status': 'updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/supa-admin/send-zoho', methods=['POST'])
@login_required
@role_required('supa_admin')
def supa_send_zoho():
    from services.mailer import send_verification_email
    data = request.get_json() or {}
    email = data.get('email')
    link = data.get('link') or url_for('admin.dashboard', _external=True)
    if not email:
        return jsonify({'error': 'Missing email'}), 400
    ok = send_verification_email(email, link)
    return jsonify({'status': 'sent' if ok else 'failed'})


# =========================================================
# === Calendar Management (Admin-only) ====================
# =========================================================


@admin_bp.route('/calendar/create', methods=['POST'])
@login_required
@role_required('supa_admin')
def admin_calendar_create():
    """Create a calendar event via the server-side calendar tool and persist a local record."""
    try:
        payload = request.get_json() or {}
        event = payload.get('event', {})
        calendar_id = payload.get('calendar_id', 'primary')
        demo_id = payload.get('demo_id') or None

        # lazy import of calendar helper
        try:
            from services.calendar_tool import create_calendar_event
        except Exception:
            return jsonify({'error': 'calendar_tool_unavailable'}), 500

        result = create_calendar_event(event, calendar_id=calendar_id)

        # persist a local audit record for manual viewing/edit
        import uuid
        record = {
            'id': uuid.uuid4().hex,
            'demo_id': demo_id,
            'event_request': event,
            'calendar_id': calendar_id,
            'result': result,
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        try:
            os.makedirs('data', exist_ok=True)
            path = os.path.join('data', 'calendar_events.jsonl')
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
        except Exception:
            pass

        return jsonify({'status': 'ok', 'record': record})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/calendar/events', methods=['GET', 'POST'])
@login_required
@role_required('supa_admin')
def admin_calendar_events():
    """Viewer/editor for locally persisted calendar events (stored in data/calendar_events.jsonl)."""
    try:
        path = os.path.join('data', 'calendar_events.jsonl')
        events = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        continue

        if request.method == 'POST':
            # Expect JSON with 'id' and fields to update
            payload = request.get_json() or {}
            eid = payload.get('id')
            updated = payload.get('update', {})
            if not eid:
                return jsonify({'error': 'missing_id'}), 400

            changed = False
            for ev in events:
                if ev.get('id') == eid:
                    ev.update(updated)
                    ev['modified_at'] = datetime.datetime.utcnow().isoformat()
                    changed = True
                    break

            if changed:
                # write back file
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        for ev in events:
                            f.write(json.dumps(ev) + '\n')
                except Exception:
                    pass
                return jsonify({'status': 'ok', 'updated': True})
            return jsonify({'status': 'not_found'}), 404

        # GET -> render simple template
        return render_template('calendar_events.html', events=events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================================================
# === SECURE LIVE CHAT (ADMIN TERMINAL) ===
# =========================================================

@admin_bp.route('/live-chat')
@login_required
@role_required('supa_admin', 'admin')
def live_chat():
    clients = []
    try:
        res = supabase_admin.table('clients').select('id, full_name, email').order('created_at', desc=True).execute()
        if res.data: clients = res.data
    except Exception as e:
        print(f"Chat Load Error: {e}")
    return render_template('admin/live_chat.html', clients=clients)

@admin_bp.route('/api/chat/<string:client_id>')
@login_required
def get_chat_history(client_id):
    """Fetches history, DECRYPTS text, and SIGNS file URLs for viewing."""
    audit_context = {'original_challenge': 'N/A', 'date_filed': 'N/A'}
    
    try:
        client_res = supabase_admin.table('clients').select('email').eq('id', client_id).single().execute()
        if client_res.data:
            client_email = client_res.data['email']
            audit_res = supabase_admin.table('audit_requests').select('message, created_at').eq('email', client_email).order('created_at', desc=True).limit(1).execute()
            if audit_res.data:
                audit_context['original_challenge'] = audit_res.data[0].get('message', 'N/A')
                audit_context['date_filed'] = audit_res.data[0].get('created_at', 'N/A').split('T')[0]
    except Exception: pass

    chat_history = []
    try:
        res = supabase_admin.table('secure_chat_messages').select('*').eq('client_id', client_id).order('created_at', desc=False).execute()
        if res.data:
            chat_history = res.data
            for msg in chat_history:
                msg['message'] = decrypt_text(msg.get('encrypted_content'))
                if msg.get('attachment_url'):
                    signed = supabase_admin.storage.from_('secure-files').create_signed_url(msg['attachment_url'], 3600)
                    msg['signed_attachment'] = signed.get('signedURL') if isinstance(signed, dict) else signed
    except Exception as e: print(f"Chat History Error: {e}")

    return jsonify({'history': chat_history, 'context': audit_context})

@admin_bp.route('/api/chat/send', methods=['POST'])
@login_required
def send_admin_message():
    """Handles Admin Text AND File Uploads."""
    client_id = request.form.get('client_id')
    text = request.form.get('message')
    uploaded_file = request.files.get('file')
    
    try:
        attachment_path, attachment_type = None, None
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            file_path = f"{client_id}/admin_uploads/{secrets.token_hex(4)}_{filename}"
            supabase_admin.storage.from_('secure-files').upload(path=file_path, file=uploaded_file.read(), file_options={"content-type": uploaded_file.content_type})
            attachment_path = file_path
            attachment_type = 'image' if 'image' in uploaded_file.content_type else 'document'

        encrypted_content = encrypt_text(text if text else "[FILE SENT]")
        supabase_admin.table('secure_chat_messages').insert({
            'client_id': client_id, 'admin_id': current_user.id, 'sender_type': 'admin',
            'encrypted_content': encrypted_content, 'attachment_url': attachment_path, 'attachment_type': attachment_type
        }).execute()
        return jsonify({'status': 'sent'})
    except Exception as e: return jsonify({'error': str(e)}), 500

# =========================================================
# === CMS & LEAD MANAGEMENT (FULL RESTORATION) ===
# =========================================================

@admin_bp.route('/lead/view/<string:lead_id>')
@login_required
@role_required('supa_admin', 'admin', 'editor')
def view_lead(lead_id):
    try:
        res = supabase_admin.table('audit_requests').select('*').eq('id', lead_id).limit(1).execute()
        if res.data: return render_template('admin/view_lead.html', lead=res.data[0])
    except Exception: pass
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/lead/delete/<string:lead_id>')
@login_required
@role_required('supa_admin', 'admin')
def delete_lead(lead_id):
    try:
        supabase_admin.table('audit_requests').delete().eq('id', lead_id).execute()
        flash("Lead removed from database.", "info")
    except Exception as e: flash(f"Delete failed: {e}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/post/new', methods=['GET', 'POST'])
@login_required
@role_required('supa_admin', 'admin', 'editor')
def new_post():
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
        if res.data: return render_template('admin/new_post.html', post=res.data[0])
    except Exception: pass
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/post/publish/<string:post_id>')
@login_required
@role_required('supa_admin', 'admin', 'editor')
def publish_post(post_id):
    try:
        supabase_admin.table('blog_posts').update({"status": "Published", "published_at": "now()"}).eq('id', post_id).execute()
        flash("Insight deployed to live site.", "success")
    except Exception as e: flash(f"Deploy failed: {e}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/post/delete/<string:post_id>')
@login_required
@role_required('supa_admin', 'admin')
def delete_post(post_id):
    try:
        supabase_admin.table('blog_posts').delete().eq('id', post_id).execute()
        flash("Insight deleted permanently.", "info")
    except Exception as e: flash(f"Delete failed: {str(e)}", "error")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/generate', methods=['POST'])
@login_required
def generate_content():
    """Restored AI content generator for blog posts."""
    data = request.get_json()
    try:
        prompt = f"Write a blog post about {data.get('topic')}. Return ONLY JSON with 'summary' and 'content' keys."
        
        # Retry logic with key rotation
        max_retries = len(key_manager.get_all_keys()) * 2
        if max_retries == 0: max_retries = 1
        
        last_exc = None
        
        for attempt in range(max_retries):
            current_key = key_manager.get_current_key()
            try:
                genai.configure(api_key=current_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                return jsonify(json.loads(response.text))
            except Exception as e:
                last_exc = e
                error_str = str(e)
                if any(x in error_str.lower() for x in ["429", "quota", "403", "leaked", "expired", "invalid"]):
                    key_manager.rotate_key()
                    continue
                else:
                    key_manager.rotate_key()
                    continue
        
        return jsonify({'error': f"Failed to generate content after retries: {str(last_exc)}"}), 500

    except Exception as e: return jsonify({'error': str(e)}), 500