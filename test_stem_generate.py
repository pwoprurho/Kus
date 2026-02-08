import os
import json
from dotenv import load_dotenv
from core.stem_ai import StemAIEngine
from core.validator import PhysicsCodeValidator

load_dotenv()

def test_full_pipeline():
    engine = StemAIEngine()
    validator = PhysicsCodeValidator()
    design_doc = "A simple ball falling from 10 meters height using gravity."
    
    print(f"Testing full pipeline with design doc: {design_doc}")
    try:
        result = engine.generate_simulation(design_doc)
        if "errors" in result:
            print(f"Generation Error: {result['errors']}")
            return

        print("Success in generation. Validating code...")
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
