import os
import glob
import time
import random
import pymupdf4llm
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from core.key_manager import key_manager

# 1. Load Environment Variables
load_dotenv(override=True)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("Error: Missing keys. Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.")
    exit()

if not key_manager.get_all_keys():
    print("Error: No Gemini API keys found.")
    exit()

print(f"--- Loaded {len(key_manager.get_all_keys())} Gemini API Keys ---")

# 2. Initialize Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure initial key
genai.configure(api_key=key_manager.get_current_key())

def clear_existing_data():
    """Deletes all existing rows in the tax_law_chunks table."""
    print("--- Clearing existing data from 'tax_law_chunks' ---")
    try:
        # Delete all rows (neq 0 is a hack to select all if id is numeric, or use a different filter)
        # Better: use delete().neq('id', -1) assuming id is positive
        supabase.table('tax_law_chunks').delete().neq('id', -1).execute()
        print("    Data cleared successfully.")
    except Exception as e:
        print(f"    Warning: Could not clear data (Table might be empty or missing): {e}")

def clean_text(text):
    """Basic text cleaning."""
    if not text: return ""
    return " ".join(text.split())

def embed_with_retry(content, title, max_retries=10):
    """
    Tries to generate an embedding. If it hits a Rate Limit (429),
    it rotates the API key and retries immediately.
    """
    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=content,
                task_type="retrieval_document",
                title=title
            )
            return result['embedding']
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                print(f"   [Rate Limit Hit] ", end="", flush=True)
                key_manager.rotate_key()
                genai.configure(api_key=key_manager.get_current_key())
                time.sleep(1) # Short pause to let config settle
            elif any(x in error_str.lower() for x in ["403", "leaked", "400", "expired", "invalid"]):
                print(f"   [Key Invalid/Expired] ", end="", flush=True)
                key_manager.rotate_key()
                genai.configure(api_key=key_manager.get_current_key())
                time.sleep(1)
            else:
                # If it's not a rate limit error (e.g., connection lost), print and give up on this chunk
                print(f"   [Error] Failed to embed: {e}")
                return None
    
    print("   [Failed] Exceeded max retries for this page.")
    return None

def process_pdfs():
    # Looks for PDFs in the knowledge_base folder
    pdf_files = glob.glob("static/docs/*.pdf")
    
    if not pdf_files:
        print("No PDF files found in 'static/docs/' folder.")
        return

    # Clear old data before processing
    clear_existing_data()

    print(f"--- Found {len(pdf_files)} PDF(s). Starting Smart Processing... ---")

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"\nProcessing File: {filename}")
        
        try:
            # Get total pages using pymupdf (fitz) via pymupdf4llm helper or just try/except
            # pymupdf4llm doesn't easily give page count without opening doc.
            # Let's open with fitz to get page count, or just iterate until error?
            # Better: Use pymupdf directly to get page count.
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            for i in range(total_pages):
                page_num = i + 1
                
                # Convert to Markdown using local library (No API cost)
                print(f"  Converting Page {page_num} to Markdown...", end="", flush=True)
                try:
                    markdown_content = pymupdf4llm.to_markdown(pdf_path, pages=[i])
                except Exception as md_err:
                    print(f" [Error] {md_err}")
                    continue
                
                print(" Done.")

                if len(markdown_content) < 50:
                    print(f"  Skipping Page {page_num} (Text too short)")
                    continue

                # Embed the entire page
                chunk_label = f"{filename} - Page {page_num}"
                print(f"  Embedding {chunk_label}...", end="", flush=True)
                
                embedding = embed_with_retry(markdown_content, chunk_label)
                
                if embedding:
                    # Insert into Supabase tax_law_chunks table
                    data = {
                        "chunk_text": markdown_content,
                        "page_num": page_num,
                        "embedding": embedding
                    }
                    try:
                        supabase.table("tax_law_chunks").insert(data).execute()
                        print(" Done.")
                    except Exception as db_err:
                        print(f" DB Error: {db_err}")
                
                # Rate limit protection (only for embedding now)
                time.sleep(1)

        except Exception as e:
            print(f"Failed to read PDF {filename}: {e}")

    print("\n--- Knowledge Base Update Complete ---")

if __name__ == "__main__":
    process_pdfs()