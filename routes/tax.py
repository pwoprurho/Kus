# routes/tax.py
"""Authenticated client route for secure tax agent chat."""
from flask import Blueprint, request, jsonify, session, render_template
from core.engine import KusmusAIEngine
from services.personas import DEMO_REGISTRY
from rag_tax_law import search_tax_law
from werkzeug.utils import secure_filename
import os
import csv
import secrets
from db import supabase_admin
from utils import get_cipher_suite, encrypt_text, decrypt_text

tax_bp = Blueprint('tax', __name__)

# In-memory store for demo; replace with DB in production
CLIENT_TABLES = {}
@tax_bp.route('/tax')
def tax_agent_ui():
    # Use client session keys for authentication
    if not session.get('client_access') or not session.get('client_id'):
        return render_template('403.html')
    return render_template('client/tax_agent.html')

@tax_bp.route('/api/tax/upload', methods=['POST'])
def tax_upload():
    # Use client session keys for authentication
    if not session.get('client_access') or not session.get('client_id'):
        return jsonify({'error': 'Authentication required'}), 401
    client_id = session.get('client_id')
    statement_file = request.files.get('statementFile')
    receipts_file = request.files.get('receiptsFile')
    
    uploaded_files = []

    try:
        for file_obj, label in [(statement_file, 'Bank Statement'), (receipts_file, 'Receipts')]:
            if file_obj:
                filename = secure_filename(file_obj.filename)
                file_path = f"{client_id}/tax_docs/{secrets.token_hex(4)}_{filename}"
                
                # Upload to Supabase Storage
                supabase_admin.storage.from_('secure-files').upload(
                    path=file_path,
                    file=file_obj.read(),
                    file_options={"content-type": file_obj.content_type}
                )
                uploaded_files.append({'name': filename, 'type': label, 'path': file_path})

        return jsonify({'success': True, 'files': uploaded_files})
    except Exception as e:
        print(f"Tax Upload Error: {e}")
        return jsonify({'error': str(e)}), 400

from rag_tax_law import search_tax_law

@tax_bp.route('/api/tax/chat', methods=['POST'])
def tax_chat():
    try:
        # Use client session keys for authentication
        if not session.get('client_access') or not session.get('client_id'):
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        context_logs = data.get('context_logs', [])
        
        # --- MODIFICATION: RAG Integration ---
        persona = DEMO_REGISTRY.get('tax_compliance_agent')
        if not persona:
            return jsonify({'error': 'Tax agent persona not found.'}), 500
            
        tools_allowed = persona.get('tools_allowed', [])

        final_prompt = user_message
        rag_context = ""

        if 'search_tax_law' in tools_allowed:
            try:
                # 1. Use the user's message to search the tax law DB
                search_results = search_tax_law(user_message, supabase_admin, top_k=3)
                
                # 2. Format the results into a context block
                context_chunks = []
                for result in search_results:
                    context_chunks.append(f"Source (Page {result.get('page_num', 'N/A')}):\n{result.get('chunk_text', '')}")
                
                rag_context = "\n\n---\n".join(context_chunks)
                
                # 3. Construct a new prompt that includes the RAG context
                final_prompt = f"""
                **User Question:** {user_message}

                **Relevant Excerpts from the Nigerian Tax Act 2025:**
                ---
                {rag_context}
                ---

                **Instruction:** Based *only* on the provided excerpts, please answer the user's question. Cite the page number for each piece of information you use. If the answer is not in the excerpts, state that clearly.
                """
            except Exception as e:
                print(f"RAG search failed: {e}")
                # Fallback to non-RAG response if search fails
                pass

        # --- END MODIFICATION ---

        # Explicitly pass empty tools list to isolate Tax Agent from Sandbox tools
        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona.get('model', 'gemini-2.5-flash'),
            tools=[] 
        )
        
        # Use the potentially modified prompt
        response_text, thought_trace = engine.generate_response(final_prompt, context_logs=context_logs)
        
        return jsonify({
            'response': response_text,
            'thought_trace': thought_trace,
            'rag_context': rag_context # Optional: return context for debugging
        })
    except Exception as e:
        print(f"Tax Chat Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'System Error: {str(e)}'}), 500

@tax_bp.route('/client/chat/sync')
def client_chat_sync():
    """Fetches decrypted chat history for the logged-in client."""
    if not session.get('client_access') or not session.get('client_id'):
        return jsonify({'error': 'Authentication required'}), 401
    client_id = session['client_id']
    
    try:
        res = supabase_admin.table('secure_chat_messages').select('*').eq('client_id', client_id).order('created_at', desc=False).execute()
        chat_history = res.data or []
        
        for msg in chat_history:
            msg['message'] = decrypt_text(msg.get('encrypted_content'))
            if msg.get('attachment_url'):
                signed = supabase_admin.storage.from_('secure-files').create_signed_url(msg['attachment_url'], 3600)
                msg['signed_attachment'] = signed.get('signedURL') if isinstance(signed, dict) else signed
        
        return jsonify(chat_history)
    except Exception as e:
        print(f"Client Chat Sync Error: {e}")
        return jsonify({'error': 'Could not sync messages.'}), 500

@tax_bp.route('/client/chat/send', methods=['POST'])
def client_chat_send():
    """Handles Client Text AND File Uploads, saving them encrypted."""
    if not session.get('client_access') or not session.get('client_id'):
        return jsonify({'error': 'Authentication required'}), 401
    
    client_id = session['client_id']
    text = request.form.get('message')
    uploaded_file = request.files.get('file')

    try:
        attachment_path, attachment_type = None, None
        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)
            # Create a unique path for the client's upload
            file_path = f"{client_id}/client_uploads/{secrets.token_hex(4)}_{filename}"
            
            # Upload to Supabase Storage
            supabase_admin.storage.from_('secure-files').upload(
                path=file_path,
                file=uploaded_file.read(),
                file_options={"content-type": uploaded_file.content_type}
            )
            attachment_path = file_path
            attachment_type = 'image' if 'image' in uploaded_file.content_type else 'document'

        # Encrypt the text content
        encrypted_content = encrypt_text(text if text else "[FILE SENT]")

        # Insert the message record
        supabase_admin.table('secure_chat_messages').insert({
            'client_id': client_id,
            'sender_type': 'client', # Message is FROM the client
            'encrypted_content': encrypted_content,
            'attachment_url': attachment_path,
            'attachment_type': attachment_type
        }).execute()

        return jsonify({'status': 'sent'})
    except Exception as e:
        print(f"Client Chat Send Error: {e}")
        return jsonify({'error': str(e)}), 500
