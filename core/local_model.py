"""
Local Model Integration for Kusmus AI STEM Sandbox
Supports DeepSeek Coder via Ollama for offline code generation
"""

import requests
import json
from typing import Dict, Optional

class LocalModelClient:
    """Client for interacting with Ollama-hosted local models"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model_name = "deepseek-coder:1.3b"
        
    def is_available(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(m['name'] == self.model_name for m in models)
            return False
        except:
            return False
    
    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> Dict:
        """Generate code using local DeepSeek Coder model"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 2048,  # Max tokens to generate
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60  # 60 second timeout for generation
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "text": result.get('response', ''),
                    "model": self.model_name,
                    "local": True
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Local model timeout (>60s). Try again or use cloud fallback."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Local model error: {str(e)}"
            }
    
    def pull_model(self) -> Dict:
        """Pull DeepSeek Coder model (if not already downloaded)"""
        try:
            payload = {"name": self.model_name}
            response = requests.post(
                f"{self.base_url}/api/pull",
                json=payload,
                stream=True,
                timeout=600  # 10 minute timeout for download
            )
            
            if response.status_code == 200:
                # Stream progress updates
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if 'status' in data:
                            print(f"[Ollama] {data['status']}")
                
                return {"success": True, "message": "Model pulled successfully"}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
