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
1.  **Deep Reasoning**: Before answering, think through the physics principles required (e.g., refraction indices for prisms, probability distributions for quantum experiments). 
2.  **Conversational Loop**: 
    - If a request is broad ("A light experiment using a glass prism"), don't build it yet. Ask for specifics: "What wavelength of light?", "What shape of prism (triangular, rectangular)?", "Enable dispersive effects?"
    - For "Schrodingers experiment using coin toss", discuss how to represent superposition (e.g., a translucent coin or a box that only reveals state upon clicking).
3.  **Proactive Design**: Propose standard values (e.g., "I will use a 1kg mass and 1m length") to speed up the process.
4.  **Identify Subject**: Ensure the request is valid Physics/STEM.

RESPONSE FORMAT:
"I've analyzed your experiment. [Concise reasoning/plan]. [Clarifying questions or confirmation]."

INTERNAL STATE:
Always include a hidden state at the end of your response:
[STATE: { "subject": "physics", "ready": true, "design": "Full technical description of the scene..." }]

- Set `ready: true` ONLY when you have enough information to build a high-quality, scientifically accurate simulation.
- Set `ready: false` if you need more details from the user.
"""

# The system prompt for the "Generation" phase (Gemini 2.5 Flash)
STEM_GENERATION_PROMPT = """
You are a STEM Simulation Architect powered by Gemini 2.5 Flash.
Convert the following research design into 100% executable Three.js + Cannon-es code.

CODE GUIDELINES:
1.  **Premium Aesthetics**: Use lights, shadows, and refined materials (MeshStandardMaterial). **IMPORTANT**: You MUST add lighting (AmbientLight + PointLight/DirectionalLight) or the scene will be pitch black.
2.  **Environment Setup**: Always include a ground plane (e.g., a grid or a solid plane) so objects have a spatial context.
3.  **Cannon-es Math**: Use Cannon.js for all physical calculations (mass, gravity, constraints).
4.  **Environment Awareness**: 
    - **Distance**: 1 unit = 1 meter. Use the grid (1m squares) for positioning.
    - **Time**: A built-in timer HUD is available. Ensure simulations reflect real-world time.
5.  **Complex Physics capabilities**:
    - **Constraints**: Use `CANNON.PointToPointConstraint`, `LockConstraint`, or `HingeConstraint` for joints/pendulums.
    - **Springs**: Use `CANNON.Spring` for elastic connections.
    - **Multi-body**: Handle arrays of objects and their interactions.
    - **Visuals**: Sync Three.js meshes to Cannon.js bodies in the render loop.
6.  **Standardized Environment**: Do NOT use `import` or `export` statements. Use the global variables provided in the scope: `THREE`, `CANNON`, and `lil.GUI`.
7.  The code MUST return an object with the structure shown in the example.

OUTPUT FORMAT:
1.  **Code**: Provide the full "raw" JavaScript code in a ```javascript``` block.
2.  **Metadata**: Provide the title and description in a ```json``` block.

Example:
```javascript
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(...);
// ... setup lighting, ground, objects, physics ...
function update() {
    // ... update physics, sync meshes ...
}
return { 
    rendererParameters: { antialias: true, alpha: true }, 
    scene: scene,
    camera: camera, 
    controls: { reset: () => { /* reset logic */ } }, 
    render: update 
};
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
