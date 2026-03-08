import sys
import os
import json

from core.stem_ai import StemAIEngine

def main():
    engine = StemAIEngine()
    print("1. Sending Chat Request...")
    result = engine.chat_interact("Simulate a simple pendulum.", "physics")
    
    print("AI Chat Response:", result["response"])
    print("State:", result["state"])
    
    design_doc = result["state"].get("design")
    if not design_doc:
        print("ERROR: AI did not produce a design document.")
        return
        
    print("\n2. Triggering Code Generation Stream...")
    full_code = ""
    for chunk in engine.generate_simulation_stream(design_doc, "physics"):
        if chunk["type"] == "content":
            full_code += chunk["content"]
            
    with open("pendulum_output.json", "w", encoding="utf-8") as f:
        f.write(full_code)
    print("Output written to pendulum_output.json")
    
    # Extract JSON
    json_str = full_code
    if "```json" in full_code:
        json_str = full_code.split("```json")[1].split("```")[0].strip()
        
    try:
        config = json.loads(json_str)
        print("SUCCESS: Parsed valid JSON configuration.")
        print("Entities:", [e.get("id") for e in config.get("entities", [])])
        print("Constraints:", len(config.get("constraints", [])))
    except json.JSONDecodeError as e:
        print("ERROR: Output is not valid JSON.", e)
        print("Raw output:", json_str[:500])

if __name__ == "__main__":
    main()
