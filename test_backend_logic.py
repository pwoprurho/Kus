import os
import sys
import json
from dotenv import load_dotenv
from core.engine import KusmusAIEngine
from services.personas import DEMO_REGISTRY

# 1. Setup Environment
load_dotenv(override=True)

# 2. Configuration
persona = DEMO_REGISTRY['tax_compliance_agent']
print(f"Testing Persona: {persona['name']}")
print(f"Model ID: {persona['model']}")

# 3. Instantiate Engine
print("\n--- Initializing Engine ---")
try:
    engine = KusmusAIEngine(
        system_instruction=persona['instruction'],
        model_name=persona['model'],
        tools=[], 
        enable_google_search=True 
    )
    print("Engine initialized successfully.")
except Exception as e:
    print(f"CRITICAL: Engine initialization failed: {e}")
    sys.exit(1)

# 4. Run Logic Test (Stream)
print("\n--- Starting Stream Generation Test ---")
test_message = "I earned 10 million naira. Calculate my tax."

try:
    # Use the generator
    stream_generator = engine.generate_response_stream(test_message)
    
    print("Stream generator created. Iterating...")
    event_count = 0
    
    for event in stream_generator:
        event_count += 1
        print(f"Event {event_count}: {json.dumps(event)[:100]}...") # Truncate for readability
        
        if event.get('type') == 'error':
            print(f"❌ ERROR DETECTED IN STREAM: {event.get('content')}")
        
    print(f"\n✅ Stream finished. Total events received: {event_count}")

except Exception as e:
    print(f"\n❌ EXCEPTION during stream iteration: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Test Complete ---")
