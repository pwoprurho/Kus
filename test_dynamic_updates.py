import sys
import os
import json

from core.stem_ai import StemAIEngine

def main():
    engine = StemAIEngine()
    
    # Simulate first turn
    print("----- TURN 1 -----")
    result1 = engine.chat_interact("Simulate a simple pendulum.", "physics")
    design_doc1 = result1["state"].get("design")
    context_logs = [
        {"role": "user", "content": "Simulate a simple pendulum."},
        {"role": "assistant", "content": result1["response"]}
    ]
    
    # Simulate second turn
    print("----- TURN 2 (Follow-up) -----")
    result2 = engine.chat_interact("increase the radius of the ball and make it blue", "physics", context_logs=context_logs)
    design_doc2 = result2["state"].get("design")
    context_logs.append({"role": "user", "content": "increase the radius of the ball and make it blue"})
    context_logs.append({"role": "assistant", "content": result2["response"]})
    
    print("\nDesign Doc 2:", design_doc2)
    
    chat_context = "\n".join([f"{h['role']}: {h['content']}" for h in context_logs])
    
    print("\nGenerating final JSON for Follow-up...")
    full_code = ""
    for chunk in engine.generate_simulation_stream(design_doc2, "physics", chat_context=chat_context):
        if chunk["type"] == "content":
            full_code += chunk["content"]
            
    # Extract JSON
    json_str = full_code
    if "```json" in full_code:
        json_str = full_code.split("```json")[1].split("```")[0].strip()
        
    try:
        config = json.loads(json_str)
        print("\nSUCCESS: Parsed valid JSON configuration.")
        for ent in config.get("entities", []):
            if ent.get("type") == "sphere":
                print(f"Sphere Radius: {ent.get('radius')}")
                print(f"Sphere Color: {ent.get('color')}")
    except json.JSONDecodeError as e:
        print("ERROR: Output is not valid JSON.", e)

if __name__ == "__main__":
    main()
