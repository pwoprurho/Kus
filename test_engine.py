
import os
from dotenv import load_dotenv
import sys

load_dotenv(override=True)

try:
    from core.engine import KusmusAIEngine
    print("Import successful")
    
    engine = KusmusAIEngine(system_instruction="Test")
    print("Initialization successful")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
