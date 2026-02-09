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
You are a STEM Research Assistant. Your goal is to help the user design a high-fidelity 3D physics simulation.

YOUR MISSION:
1.  **Analyze & Plan**: When a user describes an experiment, draft a concise technical plan (objects, constraints, physics laws).
2.  **Any Level**: 
    - For **Simple** requests ("drop a ball"): Fill in reasonable defaults immediately and set `ready: true`.
    - For **Complex** requests ("double pendulum"): Outline the constraints and math you will use.
3.  **Proactive Design**: Do NOT ask endless questions. If parameters are missing, PROPOSE standard values (e.g., "I will use a 1kg mass and 1m length") and ask for confirmation OR just proceed if the request implies urgency.
4.  **Identify Subject**: Determine if the request is valid Physics.

RESPONSE FORMAT:
"I have designed the simulation for [concept]. It will include [features]. Ready to build?"

INTERNAL STATE:
Always include a hidden state at the end of your response:
[STATE: { "subject": "physics", "ready": true, "design": "Full technical description of the scene..." }]

- Set `ready: true` if you have enough to generate a working demo.
- Set `ready: false` ONLY if the request is gibberish or critically ambiguous.
"""

# The system prompt for the "Generation" phase (Gemini 2.5 Flash)
STEM_GENERATION_PROMPT = """
You are a STEM Simulation Architect powered by Gemini 2.5 Flash.
Convert the following research design into 100% executable Three.js + Cannon-es code.

CODE GUIDELINES:
1.  **Premium Aesthetics**: Use lights, shadows, and refined materials (MeshStandardMaterial).
2.  **Cannon-es Math**: Use Cannon.js for all physical calculations (mass, gravity, constraints).
3.  **Environment Awareness**: 
    - **Distance**: 1 unit = 1 meter. Use the grid (1m squares) for positioning.
    - **Time**: A built-in timer HUD is available. Ensure simulations reflect real-world time.
4.  **Complex Physics capabilities**:
    - **Constraints**: Use `CANNON.PointToPointConstraint`, `LockConstraint`, or `HingeConstraint` for joints/pendulums.
    - **Springs**: Use `CANNON.Spring` for elastic connections.
    - **Multi-body**: Handle arrays of objects and their interactions.
    - **Visuals**: Sync Three.js meshes to Cannon.js bodies in the render loop.
    - The code MUST return an object `physicsControls` with `reset()` to restart the sim.

OUTPUT FORMAT:
1.  **Code**: Provide the full "raw" JavaScript code in a ```javascript``` block. Do NOT escape quotes or newlines here.
2.  **Metadata**: Provide the title and description in a ```json``` block.

Example:
```javascript
const scene = new THREE.Scene();
// ...
return { controls: ... };
```

```json
{
    "title": "Double Pendulum",
    "description": "A chaotic system..."
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

    def generate_simulation(self, design_doc: str, retries: int = 2) -> dict:
        """
        Phase 2: Generate high-fidelity code using Gemini 2.5 Flash.
        Includes a retry mechanism for robust JSON parsing.
        """
        engine = KusmusAIEngine(
            system_instruction=STEM_GENERATION_PROMPT,
            model_name=self.generation_model
        )
        
        last_error = None
        for attempt in range(retries + 1):
            try:
                response_text, thought_trace = engine.generate_response(
                    f"Generate the full STEM simulation code for this design: {design_doc}"
                )
                
                result = self._parse_json(response_text)
                if "errors" not in result:
                    result["thought_trace"] = thought_trace
                    result["model_used"] = self.generation_model
                    return result
                
                last_error = result["errors"][0]
                print(f"[StemAIEngine] Attempt {attempt + 1} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                print(f"[StemAIEngine] Attempt {attempt + 1} exception: {last_error}")
        
        return {"errors": [f"Deep Generation Failed after {retries + 1} attempts. Last error: {last_error}"]}

    def generate_simulation_stream(self, design_doc: str):
        """
        Stream the high-fidelity code generation for real-time visualization.
        """
        engine = KusmusAIEngine(
            system_instruction=STEM_GENERATION_PROMPT,
            model_name=self.generation_model
        )
        
        # Use the engine's streaming capability
        # We wrap the design doc in the prompt locally
        prompt = f"Generate the full STEM simulation code for this design: {design_doc}"
        
        # Yield chunks from the engine
        for chunk in engine.generate_response_stream(prompt):
            yield chunk

    def _parse_state(self, text: str) -> dict:
        match = re.search(r'\[STATE:\s*({.*?})\s*\]', text)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        return {"subject": "physics", "ready": False, "missing": []}

    def _parse_json(self, text: str) -> dict:
        """
        Robust JSON parser that handles common AI formatting anomalies.
        """
        result = {}
        
        # 1. Extract Code Block
        code_match = re.search(r'```(?:javascript|js)\s*(.*?)\s*```', text, flags=re.DOTALL)
        if code_match:
            result["threejs_code"] = code_match.group(1)
        
        # 2. Extract JSON Block
        json_match = re.search(r'```json\s*({.*?})\s*```', text, flags=re.DOTALL)
        if json_match:
            try:
                metadata = json.loads(json_match.group(1))
                result.update(metadata)
            except:
                pass
        
        # Fallback: If no code block but JSON has threejs_code
        if "threejs_code" not in result and "threejs_code" in text:
             # Try legacy pure JSON parse
            try:
                legacy = json.loads(text, strict=False)
                return legacy
            except:
                pass

        if "threejs_code" in result:
             return result

        return {"errors": ["Could not parse code or metadata from response"]}
