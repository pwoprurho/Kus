import sys
import os

from core.stem_ai import StemAIEngine

def main():
    engine = StemAIEngine()
    result = engine.chat_interact("Simulate a simple pendulum.", "physics")
    design_doc = result["state"].get("design")
    if not design_doc:
        print("ERROR: AI did not produce a design document.")
        return
        
    print(f"Design Doc: {design_doc}")
    print("\nTriggering Stream...")
    for chunk in engine.generate_simulation_stream(design_doc, "physics"):
        print(chunk)

if __name__ == "__main__":
    main()
