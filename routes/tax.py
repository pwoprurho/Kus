# routes/tax.py
"""Authenticated client route for secure tax agent chat."""
from flask import Blueprint, request, jsonify, session, render_template, Response, stream_with_context
from flask_login import current_user
from core.engine import KusmusAIEngine
from services.personas import DEMO_REGISTRY
from rag_tax_law import search_tax_law
from werkzeug.utils import secure_filename
import os
import csv
import json
import secrets
from db import supabase_admin
from utils import get_cipher_suite, encrypt_text, decrypt_text
from services.mailer import send_notification_email
from supa_addmin import ADMIN_EMAIL

tax_bp = Blueprint('tax', __name__)

# In-memory store for demo; replace with DB in production
CLIENT_TABLES = {}
@tax_bp.route('/tax')
def tax_agent_ui():
    # Authenticate: Allow Admin (Flask-Login) OR Client (Session)
    if not (current_user.is_authenticated or (session.get('client_access') and session.get('client_id'))):
        return render_template('403.html')
    return render_template('client/tax_agent.html')

def get_auth_context():
    """Helper to get client_id and ensure auth for Tax routes."""
    if current_user.is_authenticated:
        return f"admin_{current_user.id}"
    if session.get('client_access') and session.get('client_id'):
        return session.get('client_id')
    return None

@tax_bp.route('/api/tax/upload', methods=['POST'])
def tax_upload():
    client_id = get_auth_context()
    if not client_id:
        return jsonify({'error': 'Authentication required'}), 401
    statement_file = request.files.get('statementFile')
    receipts_file = request.files.get('receiptsFile')
    
    uploaded_files = []

    try:
        # Clear previous doc context (using server-side file to avoid cookie limits with 200k chars)
        os.makedirs('data', exist_ok=True)
        cache_file = f"data/tax_ctx_{client_id}.txt"
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        for file_obj, label in [(statement_file, 'Bank Statement'), (receipts_file, 'Receipts')]:
            if file_obj:
                filename = secure_filename(file_obj.filename)
                file_path = f"{client_id}/tax_docs/{secrets.token_hex(4)}_{filename}"
                
                # Read file content once
                file_bytes = file_obj.read()
                
                # Suggestion: Extract text for RAG context (increased limit to 200k chars)
                try:
                    text_content = file_bytes.decode('utf-8', errors='ignore')
                    with open(cache_file, 'a', encoding='utf-8') as f:
                        f.write(f"\n\n=== {label} ({filename}) ===\n{text_content[:200000]}\n")
                except Exception:
                    pass

                # Upload to Supabase Storage
                supabase_admin.storage.from_('secure-files').upload(
                    path=file_path,
                    file=file_bytes,
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
        client_id = get_auth_context()
        if not client_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        context_logs = data.get('context_logs', [])
        # Retrieve history from request
        history = data.get('history', [])
        
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
                # Retrieve from server-side cache
                # client_id already fetched above
                user_docs = ""
                try:
                    if client_id and os.path.exists(f"data/tax_ctx_{client_id}.txt"):
                        with open(f"data/tax_ctx_{client_id}.txt", "r", encoding="utf-8") as f:
                            user_docs = f.read()
                except Exception:
                    pass
                
                final_prompt = f"""
                **User Question:** {user_message}

                **User Uploaded Financial Documents:**
                ---
                {user_docs}
                ---

                **Relevant Excerpts from the 2025 Nigerian Tax Framework (Nigeria Tax Act, Nigeria Tax Administration Act, NRS Act, JRB Act):**
                ---
                {rag_context}
                ---

                **Instruction:** You are an expert tax consultant.
                1. Analyze the User's Request and any Uploaded Documents to understand their financial situation.
                   - If no documents are uploaded, look for self-reported income/expenses in the User's Question.
                2. Use the Relevant Excerpts from the Tax Act to determine the applicable tax rules.
                3. Perform the calculation (Gross - Reliefs = Taxable * Rate). 
                4. Cite the page number for each rule used.
                5. If figures are missing (neither uploaded nor stated), ask the user for them.
                """
            except Exception as e:
                print(f"RAG search failed: {e}")
                # Fallback: still inject doc context if RAG fails
                # client_id already fetched
                user_docs = ""
                try:
                    if client_id and os.path.exists(f"data/tax_ctx_{client_id}.txt"):
                        with open(f"data/tax_ctx_{client_id}.txt", "r", encoding="utf-8") as f:
                            user_docs = f.read()
                except Exception:
                    pass
                    
                if user_docs:
                    final_prompt = f"User Documents:\n{user_docs}\n\nQuestion: {user_message}"
                pass

        # Append history to prompt if engine doesn't support stateful chat
        if history:
            transcript = "\n".join([f"{h['role'].upper()}: {h['content']}" for h in history])
            final_prompt = f"PREVIOUS CONVERSATION:\n{transcript}\n\nCURRENT REQUEST:\n{final_prompt}"

        # --- END MODIFICATION ---

        # Explicitly pass empty tools list (initially) to isolate Tax Agent from Sandbox tools
        # BUT enable Google Search for dynamic lookups
        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona.get('model', 'gemini-2.0-flash-exp'),
            tools=[], 
            enable_google_search=True 
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

@tax_bp.route('/api/tax/chat_stream', methods=['POST'])
def tax_chat_stream():
    try:
        # Auth check
        client_id = get_auth_context()
        if not client_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        history = data.get('history', [])
        context_logs = data.get('context_logs', [])
        
        persona = DEMO_REGISTRY.get('tax_compliance_agent')
        
        # ... [RAG Context Construction - same as before] ...
        # (Simplified for brevity, assuming we reuse the logic or refactor it. 
        # For now, I'll copy the critical prompt construction logic to ensure it works)
        
        # RAG Logic Re-implementation (Quick Inline)
        from rag_tax_law import search_tax_law
        rag_context = ""
        try:
            search_results = search_tax_law(user_message, supabase_admin, top_k=3)
            context_chunks = [f"Source (Page {r.get('page_num', '?')}):\n{r.get('chunk_text', '')}" for r in search_results]
            rag_context = "\n\n---\n".join(context_chunks)
        except: pass

        # client_id fetched above
        user_docs = ""
        try:
            if client_id and os.path.exists(f"data/tax_ctx_{client_id}.txt"):
                with open(f"data/tax_ctx_{client_id}.txt", "r", encoding="utf-8") as f:
                    user_docs = f.read()
        except: pass

        final_prompt = f"""
        **User Question:** {user_message}
        **User Uploaded Financial Documents:** {user_docs}
        **Relevant Excerpts from 2025 Tax Acts (Tax Act, Admin Act, NRS, JRB):** {rag_context}
        **Instruction:** You are an expert tax consultant... [Same instructions as main route]
        """
        
        if history:
            transcript = "\n".join([f"{h['role'].upper()}: {h['content']}" for h in history])
            final_prompt = f"PREVIOUS CONVERSATION:\n{transcript}\n\nCURRENT REQUEST:\n{final_prompt}"

        # Initialize Engine with Google Search capability
        engine = KusmusAIEngine(
            system_instruction=persona['instruction'],
            model_name=persona.get('model', 'gemini-2.0-flash-exp'),
            tools=[],
            enable_google_search=True
        )

        def generate():
            for event in engine.generate_response_stream(final_prompt):
                # SSE Format: data: <json>\n\n
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        print(f"Stream Error: {e}")
        return jsonify({'error': str(e)}), 500

@tax_bp.route('/client/chat/sync')
def client_chat_sync():
    """Fetches decrypted chat history for the logged-in client."""
    client_id = get_auth_context()
    if not client_id:
        return jsonify({'error': 'Authentication required'}), 401
    
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
    client_id = get_auth_context()
    if not client_id:
        return jsonify({'error': 'Authentication required'}), 401
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

        # Notify Admin
        msg_preview = text[:50] + "..." if text and len(text) > 50 else (text or "File Uploaded")
        send_notification_email(
            recipient_email=ADMIN_EMAIL,
            title="New Secure Message from Client",
            message=f"Client ID {client_id} sent a message: '{msg_preview}'",
            action_link="https://kusmus.ai/admin", # Update with real URL if needed
            action_text="Go to Admin Dashboard"
        )

        return jsonify({'status': 'sent'})
    except Exception as e:
        print(f"Client Chat Send Error: {e}")
        return jsonify({'error': str(e)}), 500

@tax_bp.route('/api/tax/generate_filing', methods=['POST'])
def generate_tax_filing():
    """Generate professional PDF tax filing document"""
    try:
        client_id = get_auth_context()
        if not client_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        tax_year = data.get('tax_year', 2025)
        
        # Import services
        from services.tax_calculator import TaxCalculator
        from services.pdf_generator import TaxFilingPDFGenerator
        
        # Get user's uploaded document context
        user_docs = ""
        try:
            if os.path.exists(f"data/tax_ctx_{client_id}.txt"):
                with open(f"data/tax_ctx_{client_id}.txt", "r", encoding="utf-8") as f:
                    user_docs = f.read()
        except Exception as e:
            print(f"Error reading user docs: {e}")
        
        # If no manual income data provided, use AI to extract from documents
        income_data = data.get('income_data')
        if not income_data and user_docs:
            # Use Gemini to extract financial data from uploaded documents
            persona = DEMO_REGISTRY.get('tax_compliance_agent')
            engine = KusmusAIEngine(
                system_instruction=persona['instruction'],
                model_name=persona.get('model', 'gemini-2.0-flash-exp')
            )
            
            extraction_prompt = f"""
            Extract the following financial information from these documents:
            
            {user_docs}
            
            Return ONLY a JSON object with this structure:
            {{
                "employment_income": <number>,
                "business_income": <number>,
                "rental_income": <number>,
                "other_income": <number>,
                "pension_contribution": <number>,
                "nhf_contribution": <number>,
                "nhis_contribution": <number>
            }}
            
            If a value is not found, use 0. Return ONLY the JSON, no explanation.
            """
            
            response_text, _ = engine.generate_response(extraction_prompt)
            
            # Parse JSON from response
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    income_data = json.loads(json_match.group())
                else:
                    income_data = {}
            except:
                income_data = {}
        
        # Default income data if extraction failed
        if not income_data:
            income_data = {
                "employment_income": 0,
                "business_income": 0,
                "rental_income": 0,
                "other_income": 0,
                "pension_contribution": 0,
                "nhf_contribution": 0,
                "nhis_contribution": 0
            }
        
        # Calculate tax
        calculator = TaxCalculator()
        tax_result = calculator.calculate_personal_income_tax(income_data)
        
        # Prepare PDF data
        pdf_data = {
            "tax_year": tax_year,
            "taxpayer_info": {
                "name": data.get('taxpayer_name', 'N/A'),
                "tin": data.get('taxpayer_tin', 'N/A'),
                "address": data.get('taxpayer_address', 'N/A'),
                "email": data.get('taxpayer_email', 'N/A'),
                "phone": data.get('taxpayer_phone', 'N/A')
            },
            "income_sources": [
                {"name": "Employment Income", "amount": income_data.get("employment_income", 0)},
                {"name": "Business Income", "amount": income_data.get("business_income", 0)},
                {"name": "Rental Income", "amount": income_data.get("rental_income", 0)},
                {"name": "Other Income", "amount": income_data.get("other_income", 0)}
            ],
            "reliefs": tax_result.get('reliefs', []),
            "tax_calculation": {
                "gross_income": tax_result['gross_income'],
                "total_reliefs": tax_result['total_reliefs'],
                "taxable_income": tax_result['taxable_income'],
                "tax_due": tax_result['tax_due'],
                "wht_paid": data.get('wht_paid', 0),
                "balance_due": tax_result['tax_due'] - data.get('wht_paid', 0)
            },
            "citations": tax_result.get('citations', [])
        }
        
        # Generate PDF
        os.makedirs('data/tax_filings/temp', exist_ok=True)
        filename = f"tax_filing_{tax_year}_{client_id}_{secrets.token_hex(4)}.pdf"
        output_path = f"data/tax_filings/temp/{filename}"
        
        generator = TaxFilingPDFGenerator()
        generator.generate_tax_filing(output_path, pdf_data)
        
        # Return success with download URL
        return jsonify({
            'success': True,
            'pdf_url': f"/downloads/tax_filings/{filename}",
            'summary': {
                'gross_income': tax_result['gross_income'],
                'total_reliefs': tax_result['total_reliefs'],
                'taxable_income': tax_result['taxable_income'],
                'tax_due': tax_result['tax_due'],
                'balance_due': tax_result['tax_due'] - data.get('wht_paid', 0)
            },
            'citations': tax_result.get('citations', [])
        })
        
    except Exception as e:
        print(f"Tax Filing Generation Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate tax filing: {str(e)}'}), 500

@tax_bp.route('/downloads/tax_filings/<filename>')
def download_tax_filing(filename):
    """Serve generated tax filing PDFs"""
    try:
        client_id = get_auth_context()
        if not client_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Security: Verify filename belongs to this client
        if client_id not in filename:
            return jsonify({'error': 'Unauthorized'}), 403
        
        file_path = f"data/tax_filings/temp/{filename}"
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        from flask import send_file
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"Download Error: {e}")
        return jsonify({'error': str(e)}), 500
