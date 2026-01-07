"""
RAG retrieval for Nigeria Tax Law using Supabase pgvector and Google embeddings.
Requires: google-cloud-aiplatform, supabase, requests
"""

import os
import json
import requests
from supabase import create_client, Client
import google.generativeai as genai
from core.key_manager import key_manager
import time

EMBED_MODEL = "models/text-embedding-004"

# --- Embed query with self-healing Gemini key rotation ---
def embed_query(text):
    max_retries = len(key_manager.get_all_keys()) * 2
    if max_retries == 0: max_retries = 1
    
    last_exc = None
    
    for attempt in range(max_retries):
        current_key = key_manager.get_current_key()
        try:
            genai.configure(api_key=current_key)
            resp = genai.embed_content(
                model=EMBED_MODEL,
                content=text,
                task_type="retrieval_query"
            )
            return resp['embedding']
        except Exception as e:
            last_exc = e
            error_str = str(e)
            if any(x in error_str.lower() for x in ["429", "quota", "403", "leaked", "expired", "invalid"]):
                # print(f"   [RAG Error] {e}. Rotating key...")
                key_manager.rotate_key()
                time.sleep(0.5)
                continue
            else:
                key_manager.rotate_key()
                continue
                
    raise last_exc or Exception("No valid Gemini API key for embedding.")

def judge_relevance(query, results):
    """
    Uses Gemini Flash to filter search results for relevance.
    Returns a list of relevant result objects.
    """
    if not results:
        return []

    # Construct a batch prompt
    prompt = f"""You are a helpful legal assistant.
    
    User Query: "{query}"
    
    Evaluate the following text chunks from the Nigeria Tax Act. 
    Return a JSON object with a key 'relevant_indices' containing a list of the 0-based indices of chunks that might be RELEVANT or HELPFUL to the query.
    
    - If a chunk mentions keywords related to the query, include it.
    - If a chunk is a section header related to the query, include it.
    - Only exclude chunks that are clearly completely unrelated (like a different topic entirely).
    
    Chunks to evaluate:
    """
    
    for i, res in enumerate(results):
        # Send more context (1000 chars) to the judge
        text_snippet = res.get('chunk_text', '')[:1000].replace('\n', ' ')
        prompt += f"\n[Index {i}] (Page {res.get('page_num')}): {text_snippet}\n"
        
    prompt += "\nReturn ONLY the JSON. Example: {'relevant_indices': [0, 2]}"

    # Call Gemini with Key Rotation
    max_retries = len(key_manager.get_all_keys()) * 2
    if max_retries == 0: max_retries = 1
    
    for attempt in range(max_retries):
        current_key = key_manager.get_current_key()
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text)
            indices = data.get('relevant_indices', [])
            
            # Filter results
            validated = [results[i] for i in indices if 0 <= i < len(results)]
            return validated

        except Exception as e:
            error_str = str(e)
            if any(x in error_str.lower() for x in ["429", "quota", "403", "leaked", "expired", "invalid"]):
                key_manager.rotate_key()
                time.sleep(0.5)
                continue
            else:
                # If it's a parsing error or other non-auth error, maybe just return the top 3 original
                # to avoid breaking the flow.
                print(f"   [Judge Error] {e}")
                return results[:3] # Fallback

    return results[:3] # Fallback if all fails

# --- Vector search ---
def search_tax_law(query, supa_client, top_k=3):
    """
    Performs a vector search on the 'tax_law_chunks' table in Supabase.
    Fetches a wider pool of results (low threshold) and then uses an AI Judge to filter them.

    Args:
        query (str): The search query.
        supa_client (Client): An initialized Supabase client.
        top_k (int, optional): The number of results to return. Defaults to 3.

    Returns:
        list: A list of search results.
    """
    emb = embed_query(query)
    
    # 1. Wide Net: Fetch more results (15) with a lower threshold (0.25)
    # This ensures we don't miss anything that might be relevant but has poor vector overlap.
    res = supa_client.rpc('match_tax_documents', {
        'query_embedding': emb, 
        'match_threshold': 0.25, 
        'match_count': 15 
    }).execute()
    
    raw_results = res.data if hasattr(res, 'data') else []
    
    if not raw_results:
        return []

    # 2. AI Judge: Filter for true relevance
    # This removes "hallucinated" matches or irrelevant keyword hits.
    validated_results = judge_relevance(query, raw_results)
    
    # 3. Return requested amount
    return validated_results[:top_k]

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in environment variables.")

    supa_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    q = input("Enter your tax law question: ")
    results = search_tax_law(q, supa_client)
    
    print("\n--- Search Results ---")
    if results:
        for r in results:
            print(f"Page {r.get('page_num', 'N/A')}: {r.get('chunk_text', 'No text available')[:250]}...\n---\n")
    else:
        print("No results found.")
