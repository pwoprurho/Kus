import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("--- DIAGNOSTIC START ---")

# 2. Check Key Existence
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing from environment/file.")
    exit()

print(f"✅ API Key found: {api_key[0:-1]} (length: {len(api_key)})")

# 3. Configure API
try:
    genai.configure(api_key=api_key)
    print("✅ Configuration successful.")
except Exception as e:
    print(f"❌ Configuration Failed: {e}")
    exit()

# 4. Test Model Connection
# Note: Changing to 'gemini-1.5-flash' for the test. 
# If 'gemini-2.5-flash' does not exist yet, that is likely your root cause.
MODEL_NAME = 'gemini-2.5-flash' 

print(f"📡 Attempting to connect using model: {MODEL_NAME}...")

try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content("Reply with 'System Operational' if you receive this.")
    
    if response and response.text:
        print("\n🎉 SUCCESS! API Response Received:")
        print("-" * 30)
        print(response.text)
        print("-" * 30)
    else:
        print("⚠️ Connection made, but response was empty.")

except Exception as e:
    print("\n❌ API CALL FAILED.")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    
    if "403" in str(e):
        print("\n🔎 DIAGNOSIS: API Key is invalid or blocked (Leak detected).")
    elif "404" in str(e):
        print(f"\n🔎 DIAGNOSIS: Model '{MODEL_NAME}' not found. Check the model name.")
    elif "500" in str(e):
        print("\n🔎 DIAGNOSIS: Google Server Error. Try again later.")

print("--- DIAGNOSTIC END ---")