import os
import json
from dotenv import load_dotenv
from core.stem_ai import StemAIEngine
from core.validator import PhysicsCodeValidator

load_dotenv()

def test_full_pipeline():
    engine = StemAIEngine()
    validator = PhysicsCodeValidator()
    
    # Try a few different prompts to see if any pass
    prompts = [
        "A simple ball falling from 10 meters height using gravity.",
        "A complex double pendulum simulation with energy graphs.",
        "Solar system simulation with all planets."
    ]
    
    for design_doc in prompts:
        print(f"\n>>> Testing: {design_doc}")
        try:
            result = engine.generate_simulation(design_doc)
            if "errors" in result:
                print(f"Generation Error: {result['errors']}")
                continue

            print("Generation SUCCESS. Validating code...")
            code = result.get('threejs_code', '')
            validation = validator.validate(code)
            
            if not validation['valid']:
                print("Validation FAILED!")
                print("Issues:", validation['issues'])
            else:
                print("Validation PASSED!")
                print("Security Level:", validation['security_level'])
                
        except Exception as e:
            print(f"Exception during test: {e}")

if __name__ == "__main__":
    test_full_pipeline()
