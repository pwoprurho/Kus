import os
import sys
import time
from dotenv import load_dotenv
from supabase import create_client
from pypdf import PdfReader
from google import genai
from google.genai import types

# Add project root to sys.path to allow sibling imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.key_manager import key_manager

load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("Error: Missing environment variables (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DOCS_DIR = r"c:\Users\Administrator\kus\static\docs"
TABLE_NAME = "tax_law_chunks"

def clear_existing_data():
    print(f"Step 1: Purging legacy data from {TABLE_NAME}...")
    try:
        # service_role key bypasses RLS to allow full purge
        res = supabase.table(TABLE_NAME).delete().neq("id", -1).execute()
        print(f"Database purged successfully.")
    except Exception as e:
        print(f"Warning: Purge failed or table already empty: {e}")

def robust_gemini_call(operation_type, **kwargs):
    """Executes a Gemini call with built-in key rotation, retries, and strict throttling."""
    max_retries = len(key_manager.get_all_keys()) * 2
    if max_retries == 0: max_retries = 1
    
    for attempt in range(max_retries):
        current_api_key = key_manager.get_current_key()
        if not current_api_key:
            print("CRITICAL: No API keys available in KeyManager.")
            return None
            
        try:
            client = genai.Client(api_key=current_api_key)
            if operation_type == "markdown":
                # Using 2.5-flash-lite as requested by user
                response = client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=kwargs['prompt']
                )
                # Mandatory sleep to avoid rate limiting
                time.sleep(2.5)
                return response.text.strip()
            elif operation_type == "embedding":
                # Standard embedding model
                response = client.models.embed_content(
                    model='text-embedding-004',
                    contents=kwargs['text']
                )
                # Mandatory sleep
                time.sleep(2.5)
                return response.embeddings[0].values
        except Exception as e:
            error_msg = str(e).lower()
            print(f"   [Gemini Error] Key Index {key_manager.current_index}: {e}")
            
            # Rotate if rate limited, invalid, or expired
            if any(x in error_msg for x in ["429", "quota", "403", "expired", "invalid", "unsupported", "not found"]):
                print(f"   [System] Key failure or limit hit. Rotating index...")
                key_manager.rotate_key()
                time.sleep(1) # Grace period
                continue
            else:
                # For transient network errors, stay on key but wait a moment
                print(f"   [System] Transient network error. Retrying in 5s...")
                time.sleep(5)
                continue
                
    return None

def convert_to_markdown(raw_text, act_name, page_num):
    """Uses Gemini 2.5 Flash Lite to transform raw legal text into high-fidelity Markdown."""
    prompt = f"""
    You are a legal document formatter. Convert the following RAW text from the '{act_name}' (Page {page_num}) into clean, structured Markdown.
    
    Guidelines:
    - Retain all legal sections, subsections, and numerical data exactly.
    - Use Markdown headers (#, ##, ###) for parts, sections, and chapters.
    - Format lists and tables correctly.
    - Do NOT add any preamble or commentary. Only return the converted Markdown content.
    - Ensure readability while maintaining 100% legal accuracy.

    RAW TEXT:
    {raw_text}
    """
    return robust_gemini_call("markdown", prompt=prompt) or raw_text

def get_embedding(text):
    return robust_gemini_call("embedding", text=text)

def process_pdf(file_path):
    print(f"\n--- Processing: {os.path.basename(file_path)} ---")
    reader = PdfReader(file_path)
    filename = os.path.basename(file_path)
    act_name = filename.replace(".pdf", "").replace("-", " ").replace("_", " ")
    chunks_to_insert = []
    
    total_pages = len(reader.pages)
    print(f"Total pages to index: {total_pages}")

    for i, page in enumerate(reader.pages):
        raw_text = page.extract_text()
        if not raw_text or len(raw_text.strip()) < 10:
            print(f"Skipping page {i+1} (empty or too short)")
            continue
            
        # 1. Convert to Markdown
        print(f"[{i+1}/{total_pages}] Converting Page {i+1} to Markdown (2.5-Flash-Lite)...")
        md_text = convert_to_markdown(raw_text.strip(), act_name, i+1)
        
        indexed_content = f"ACT: {act_name} | PAGE: {i+1}\n\n{md_text}"

        # 2. Get Embedding
        print(f"[{i+1}/{total_pages}] Vectorizing Page {i+1} (text-embedding-004)...")
        embedding = get_embedding(indexed_content)
        if embedding:
            chunks_to_insert.append({
                "chunk_text": indexed_content,
                "page_num": i + 1,
                "embedding": embedding
            })
        else:
            print(f"   [FAILED] Could not get embedding for Page {i+1}. Skipping.")
        
        # Insert in batches of 5 to manage safety and rate limits
        if len(chunks_to_insert) >= 5:
            try:
                supabase.table(TABLE_NAME).insert(chunks_to_insert).execute()
                print(f"Success: Batch committed up to page {i+1} (Key Index: {key_manager.current_index})")
                chunks_to_insert = []
                time.sleep(2) # DB Batch pause
            except Exception as e:
                print(f"Insert Error on batch: {e}")
                # Retry once after delay
                time.sleep(5)
                try:
                    supabase.table(TABLE_NAME).insert(chunks_to_insert).execute()
                    print(f"Recovery Success: Batch committed on retry.")
                    chunks_to_insert = []
                except:
                    print("Critical: Batch recovery failed. Data for this segment will be missing.")
                    chunks_to_insert = []
            
    # Final insert
    if chunks_to_insert:
        try:
            supabase.table(TABLE_NAME).insert(chunks_to_insert).execute()
            print(f"Final batch complete for {filename}.")
        except Exception as e:
            print(f"Final batch error: {e}")

def main():
    print(f"Sovereign Ingestion Engine (V4 - Throttled 2.5-Flash): Initializing...")
    print(f"Key Pool Size: {len(key_manager.get_all_keys())}")
    
    clear_existing_data()
    
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("CRITICAL: No source PDF files found in docs directory.")
        return
        
    for pdf in pdf_files:
        full_path = os.path.join(DOCS_DIR, pdf)
        process_pdf(full_path)
        
    print("\n[SUCCESS] 2025 Tax Acts fully vectorized. Pipeline Halted.")

if __name__ == "__main__":
    main()
