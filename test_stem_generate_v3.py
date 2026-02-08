import os
import json
import re
from dotenv import load_dotenv
from core.engine import KusmusAIEngine
from core.stem_ai import STEM_GENERATION_PROMPT

load_dotenv()

def test_raw_failures():
    engine = KusmusAIEngine(
        system_instruction=STEM_GENERATION_PROMPT,
        model_name="gemini-2.5-flash"
    )
    
    prompts = [
        "A simple ball falling from 10 meters height using gravity.",
        "A complex double pendulum simulation with energy graphs.",
        "Solar system simulation with all planets."
    ]
    
    for design_doc in prompts:
        print(f"\n>>> Testing: {design_doc}")
        message = f"Generate the full STEM simulation code for this design: {design_doc}"
        try:
            response_text, thought_trace = engine.generate_response(message)
            
            # Manual parse attempt
            data = None
            json_pattern = r'```json\s*({.*?})\s*```'
            match = re.search(json_pattern, response_text, flags=re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    print("SUCCESS: Parsed JSON from block.")
                except Exception as e:
                    print(f"FAILURE: Json block found but malformed: {e}")
                    print("--- RAW BLOCK ---")
                    print(match.group(1))
            else:
                try:
                    data = json.loads(response_text)
                    print("SUCCESS: Parsed whole text as JSON.")
                except Exception as e:
                    print(f"FAILURE: No JSON block and whole text is not JSON: {e}")
                    print("--- RAW RESPONSE START ---")
                    print(response_text)
                    print("--- RAW RESPONSE END ---")
                    
        except Exception as e:
            print(f"Exception during test: {e}")

if __name__ == "__main__":
    test_raw_failures()
