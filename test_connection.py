import os
import sys
from dotenv import load_dotenv
from google import genai

# Load environment
load_dotenv(override=True)
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL: GEMINI_API_KEY is missing from environment variables.")
    sys.exit(1)

print(f"Authenticated with Key: {api_key[:8]}******")

client = genai.Client(api_key=api_key)

# 1. Test Specific Models
candidates = [
    "gemini-2.5-flash-lite",  # User requested
    "gemini-2.0-flash-exp",   # Experimental 2.0
    "gemini-1.5-flash",       # Stable Fallback
    "gemini-1.5-pro"
]

print("\n=== SYSTEM CONNECTIVITY TEST ===")
valid_model = None

for model_id in candidates:
    print(f"\n[TESTING] {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="Ping. Reply with 'Pong'."
        )
        print(f"✅ SUCCESS: {model_id} is ACTIVE.")
        print(f"   Response: {response.text}")
        if not valid_model: valid_model = model_id
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"❌ FAILED: {model_id} does not exist (404).")
        else:
            print(f"⚠️ ERROR: {model_id} failed with: {error_msg}")

print("\n=== COMPLETE MODEL LIST ===")
try:
    # Attempt to list all available models
    count = 0
    for m in client.models.list():
        if "gemini" in m.name:
            print(f" - {m.name}")
            count += 1
    if count == 0:
        print("No models containing 'gemini' found in list.")
except Exception as e:
    print(f"Could not list models: {e}")
