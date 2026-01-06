
import os
import sys
from services.personas import DEMO_REGISTRY
from core.engine import KusmusAIEngine
from dotenv import load_dotenv

# Load env for API keys
load_dotenv()

def test_robotics_stream():
    print("--- TESTING ROBOTICS STREAM ---")
    
    # 1. Load Persona
    persona_id = 'surge_vla'
    persona = DEMO_REGISTRY.get(persona_id)
    
    if not persona:
        print(f"ERROR: Persona {persona_id} not found!")
        return

    print(f"Loaded Persona: {persona['name']}")
    print(f"Model: {persona['model']}")

    # 2. Initialize Engine
    engine = KusmusAIEngine(
        system_instruction=persona['instruction'],
        model_name=persona['model']
    )

    # 3. Stream Request
    user_message = "Analyze the latest vision feed. I see a red light blinking on Servo-4."
    print(f"\nUser Message: {user_message}\n")
    print("--- STREAM OUTPUT ---")

    try:
        # We pass empty logs for the test
        stream = engine.generate_response_stream(user_message, context_logs=[])
        
        full_response = ""
        thought_count = 0
        
        for event in stream:
            # Event is a dict: {'type': 'thought'|'content'|'error', 'content':Str}
            if event['type'] == 'thought':
                print(f"[THOUGHT]: {event['content'][:50]}...") # truncate for display
                thought_count += 1
            elif event['type'] == 'content':
                chunk = event['content']
                print(chunk, end="", flush=True)
                full_response += chunk
            elif event['type'] == 'error':
                print(f"\n[ERROR]: {event['content']}")
        
        print("\n\n--- TEST SUMMARY ---")
        print(f" thoughts received: {thought_count}")
        print(f" response length: {len(full_response)}")
        
        if len(full_response) > 0:
            print("SUCCESS: Stream generated content.")
        else:
            print("FAILURE: No content generated.")

    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_robotics_stream()
