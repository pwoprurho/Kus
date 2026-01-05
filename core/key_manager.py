import os
import random
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

class KeyManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeyManager, cls).__new__(cls)
            cls._instance._initialize_keys()
        return cls._instance
    
    def _initialize_keys(self):
        self.keys = []
        
        # 1. Check for GEMINI_API_KEY
        primary_key = os.environ.get("GEMINI_API_KEY")
        if primary_key:
            self.keys.append(primary_key)
            
        # 2. Check for GEMINI_API_KEYS (JSON list string)
        import json
        json_keys = os.environ.get("GEMINI_API_KEYS")
        if json_keys:
            try:
                parsed = json.loads(json_keys)
                if isinstance(parsed, list):
                    self.keys.extend(parsed)
                elif isinstance(parsed, str):
                    self.keys.append(parsed)
            except:
                pass
                
        # 3. Check for GEMINI_KEY_0 to GEMINI_KEY_20
        for i in range(20):
            key = os.environ.get(f"GEMINI_KEY_{i}")
            if key:
                self.keys.append(key)
                
        # Remove duplicates and filter empty
        self.keys = list(set([k for k in self.keys if k and k.strip()]))
        self.current_index = 0
        
        if not self.keys:
            print("WARNING: No Gemini API keys found in environment variables.")

    def get_current_key(self):
        if not self.keys:
            return None
        return self.keys[self.current_index]
    
    def get_all_keys(self):
        return self.keys
        
    def rotate_key(self):
        if not self.keys:
            return None
        self.current_index = (self.current_index + 1) % len(self.keys)
        new_key = self.keys[self.current_index]
        # print(f"   [System] Rotating to API Key Index {self.current_index}")
        return new_key

# Global instance
key_manager = KeyManager()
