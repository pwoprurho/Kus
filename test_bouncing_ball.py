import sys
import os

from core.stem_ai import StemAIEngine

def main():
    engine = StemAIEngine()
    print("1. Sending Chat Request...")
    result = engine.chat_interact("Simulate a bouncing ball with gravity. No GUI.", "physics")
    
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
            
    with open("bouncing_ball_output.js", "w", encoding="utf-8") as f:
        f.write(full_code)
    print("Code written to bouncing_ball_output.js")
    
    if "return { scene, camera, world, render }" in full_code:
        print("SUCCESS: Code contains proper return statement.")
    else:
        print("ERROR: Missing final return statement.")
        
    if "lil.GUI" in full_code or "new GUI(" in full_code:
        print("ERROR: Code still contains GUI references!")
    else:
        print("SUCCESS: No GUI found in the code.")

if __name__ == "__main__":
    main()
