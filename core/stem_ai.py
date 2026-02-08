# core/stem_ai.py
"""
STEM AI Engine (Conversational)
Handles iterative planning and Gemini 2.5 Flash code generation.
"""

import json
import re
from core.engine import KusmusAIEngine
from core.key_manager import key_manager

# The system prompt for the "Planning" phase
STEM_PLANNING_PROMPT = """
You are a STEM Research Assistant. Your goal is to help the user design a high-fidelity 3D physics, chemistry, biology, or maths simulation.

YOUR MISSION:
1.  **Interrogate**: Identify missing parameters. If a user asks for "falling ball", ask about height, mass, material, and air resistance.
2.  **Educational Fidelity**: Ensure the design follows real scientific principles.
3.  **Detail First**: You are FORBIDDEN from generating code until you have enough details for a "premium" result, UNLESS the user says "just fill the gaps", "surprise me", or "go".
4.  **Identify Subject**: Determine if the request is Physics, Chemistry, Maths, or Biology.

RESPONSE FORMAT:
Always respond in a helpful, conversational tone. If you are ready to generate, tell the user you have enough info.
If missing info, list what you need.

INTERNAL STATE:
Always include a hidden state at the end of your response in this format:
[STATE: { "subject": "physics", "ready": false, "missing": ["height", "mass"] }]
"""

# The system prompt for the "Generation" phase (Gemini 2.5 Flash)
STEM_GENERATION_PROMPT = """
You are a STEM Simulation Architect powered by Gemini 2.5 Flash.
Convert the following research design into 100% executable Three.js + Cannon-es code.

CODE GUIDELINES:
1.  **Premium Aesthetics**: Use lights, shadows, and refined materials (MeshStandardMaterial).
2.  **Cannon-es Math**: Use Cannon.js for all physical calculations.
3.  **Environment Awareness**: The 3D scene is a "Graph Environment". 
    - **Distance**: 1 unit = 1 meter. Use the grid (1m squares) for positioning.
    - **Time**: A built-in timer HUD is available. Ensure simulations reflect real-world time.
4.  **Interactivity**: The code MUST return an object with:
    - `updateGravity(x, y, z)`
    - `updateObjectParameter(index, param, value)`
    - `reset()`
5.  **Visual Aids**: Include force vectors, paths, or labels to aid understanding.

JSON OUTPUT FORMAT:
```json
{
    "title": "...",
    "description": "...",
    "concept": "...",
    "threejs_code": "...",
    "config": { "gravity": [0, -9.81, 0], "timeScale": 1.0 },
    "objects": [ { "name": "...", "adjustable": { "param": { "min": 0, "max": 1, "value": 0.5 } } } ],
    "parameters": { "global": { "min": 0, "max": 1, "value": 0.5 } }
}
```
"""

class StemAIEngine:
    """
    Conversational STEM Engine with two phases: Planning and Generation.
    """
    
    def __init__(self, model_name=None):
        # Standardized on gemini-2.5-flash series
        self.planning_model = "gemini-2.5-flash"
        self.generation_model = "gemini-2.5-flash"
    
    def chat_interact(self, message: str, context_logs=None) -> dict:
        """
        Phase 1: Chat with user to gather details.
        """
        engine = KusmusAIEngine(
            system_instruction=STEM_PLANNING_PROMPT,
            model_name=self.planning_model
        )
        
        response_text, thought_trace = engine.generate_response(message, context_logs=context_logs)
        
        # Parse state from response
        state = self._parse_state(response_text)
        
        # Clean response of the hidden state for the UI
        clean_response = re.sub(r'\[STATE:.*?\]', '', response_text).strip()
        
        return {
            "response": clean_response,
            "state": state,
            "thought_trace": thought_trace
        }

    def generate_simulation(self, design_doc: str) -> dict:
        """
        Phase 2: Generate high-fidelity code using Gemini 2.5 Flash.
        """
        engine = KusmusAIEngine(
            system_instruction=STEM_GENERATION_PROMPT,
            model_name=self.generation_model
        )
        
        response_text, thought_trace = engine.generate_response(
            f"Generate the full STEM simulation code for this design: {design_doc}"
        )
        
        result = self._parse_json(response_text)
        result["thought_trace"] = thought_trace
        result["model_used"] = self.generation_model
        return result

    def _parse_state(self, text: str) -> dict:
        match = re.search(r'\[STATE:\s*({.*?})\s*\]', text)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        return {"subject": "physics", "ready": False, "missing": []}

    def _parse_json(self, text: str) -> dict:
        try:
            json_pattern = r'```json\s*({.*?})\s*```'
            match = re.search(json_pattern, text, flags=re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
        except:
            return {"errors": ["A.I. failed to produce valid JSON structure"]}
