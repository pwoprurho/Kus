from flask import session, request
from flask_login import current_user
from extensions import socketio
from flask_socketio import join_room, emit
from db import supabase_admin
from utils import decrypt_text

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('join_client_room')
def on_join_client_room():
    """Client joins their own private room."""
    client_id = session.get('client_id')
    if client_id:
        join_room(f"client_{client_id}")
        print(f"Client {client_id} joined room client_{client_id}")
        
        # Optionally send history on join (match previous implementation)
        try:
            res = supabase_admin.table('secure_chat_messages').select('*').eq('client_id', client_id).order('created_at', desc=False).execute()
            if res.data:
                chat_history = res.data
                for msg in chat_history:
                    msg['message'] = decrypt_text(msg.get('encrypted_content'))
                    if msg.get('attachment_url'):
                        signed = supabase_admin.storage.from_('secure-files').create_signed_url(msg['attachment_url'], 3600)
                        msg['signed_attachment'] = signed.get('signedURL') if isinstance(signed, dict) else signed
                emit('chat_history', chat_history)
        except Exception as e:
            print(f"History Fetch Error: {e}")

@socketio.on('join_admin_room')
def on_join_admin_room(data):
    """Admin joins a specific client's room."""
    if not current_user.is_authenticated:
        return
    
    client_id = data.get('client_id')
    if client_id:
        join_room(f"client_{client_id}")
        print(f"Admin {current_user.id} joined room client_{client_id}")
        
        # Send history and context
        audit_context = {'original_challenge': 'N/A', 'date_filed': 'N/A'}
        try:
            client_res = supabase_admin.table('clients').select('email').eq('id', client_id).single().execute()
            if client_res.data:
                client_email = client_res.data['email']
                audit_res = supabase_admin.table('audit_requests').select('message, created_at').eq('email', client_email).order('created_at', desc=True).limit(1).execute()
                if audit_res.data:
                    audit_context['original_challenge'] = audit_res.data[0].get('message', 'N/A')
                    audit_context['date_filed'] = audit_res.data[0].get('created_at', 'N/A').split('T')[0]
            
            res = supabase_admin.table('secure_chat_messages').select('*').eq('client_id', client_id).order('created_at', desc=False).execute()
            chat_history = []
            if res.data:
                chat_history = res.data
                for msg in chat_history:
                    msg['message'] = decrypt_text(msg.get('encrypted_content'))
                    if msg.get('attachment_url'):
                        signed = supabase_admin.storage.from_('secure-files').create_signed_url(msg['attachment_url'], 3600)
                        msg['signed_attachment'] = signed.get('signedURL') if isinstance(signed, dict) else signed
            
            emit('chat_history', {'history': chat_history, 'context': audit_context, 'client_id': client_id})
        except Exception as e:
            print(f"Admin History Error: {e}")
