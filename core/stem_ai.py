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
You are a STEM Simulation Architect. Generate 100% executable Three.js + Cannon.js code.
The available globals are: `THREE` (r128), `CANNON` (0.6.2), and `lil.GUI`. Do NOT use import/export.

=== EXPERIMENT CATEGORIES ===

**CATEGORY A: RIGID-BODY MECHANICS** (Pendulums, Collisions, Projectiles)
- Use `CANNON.World`, `CANNON.Body`, `CANNON.Sphere`, `CANNON.Box`, `CANNON.Plane`.
- You MUST call `world.gravity.set(0, -9.82, 0)` and `world.step(1/60)` every frame.
- **CANNON.js 0.6.2 API WARNING**: Do NOT use `setFromEulerAngles`. For rotations use `quaternion.setFromAxisAngle(new CANNON.Vec3(axis), angle)`.
- **CONSTRAINT VISUALIZATION**: Do **NOT** manually draw lines for constraints (springs, distance constraints). The system will **automatically visualize** all `world.constraints` and `world.springs`. JUST create the physics constraint and add it to the world.

**CATEGORY B: QUANTUM EXPERIMENTS** (Quantum coin toss, Schrödinger wave, Tunneling)
- Do NOT use Cannon.js. Implement the physics in pure JavaScript.
- For wave functions: Use a grid/array and solve the Schrödinger equation numerically (e.g., split-step FFT or finite-difference).
- Visualize using `THREE.Points` or `THREE.Mesh` with custom shaders or vertex colors.

**CATEGORY C: LIGHT & OPTICS** (Prism refraction, Lenses, Interference)
- Do NOT use Cannon.js. Implement ray tracing / wave optics in pure JavaScript.
- Implement Snell's law ($n_1 \sin \theta_1 = n_2 \sin \theta_2$) for refraction.
- Visualize rays using `THREE.Line`.

**CATEGORY D: ELECTROMAGNETISM** (Lorentz force, Field lines, Cyclotron)
- Use `CANNON.World` for integration, even if no collisions. Apply custom forces in the update loop.
- Lorentz Force: $\mathbf{F} = q(\mathbf{E} + \mathbf{v} \times \mathbf{B})$. Apply via `body.applyForce(force, body.position)`.
- Visualize field lines using `THREE.Line` (streamlines).
- Visualize charged particles as colored spheres (Red +, Blue -).

**CATEGORY E: THERMODYNAMICS & SOFT BODIES** (Ideal Gas, Cloth, Springs)
- **Thermo**: Simulate N particles in a box. elastic collisions. Color by velocity (Hot=Red, Cold=Blue).
- **Soft Bodies**: Use `CANNON.Spring` or `CANNON.DistanceConstraint` between a grid of spheres.
- **Cloth**: Grid of particles connected by distance constraints.

**CATEGORY F: FLUID DYNAMICS** (SPH, Flow)
- Use a particle-based approach (Smoothed Particle Hydrodynamics - SPH) in pure JS or Cannon.js particles with custom repulsive forces.
- Visualize as a collection of blue spheres or a metaball mesh if possible.

=== VISUALIZATION STANDARDS ===
- Materials: `THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.3 })`.
- Shadows: `castShadow = true` and `receiveShadow = true`.
- Lighting: Ambient + Directional (5, 10, 5).
- Controls: Use `lil.GUI` for parameters (Gravity, B-field strength, Temperature).

=== OUTPUT FORMAT ===
1. Full JavaScript in a ```javascript``` block.
2. Metadata in a ```json``` block.
3. **CRITICAL**: The JS **MUST** return an object containing `{ scene, camera, rendererParameters, render, world }`.
   - `world`: The `CANNON.World` instance (if used). This triggers the auto-visualization of constraints.

=== COMPLETE WORKING EXAMPLE (Free Fall) ===
```javascript
// --- Scene ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111122);
const camera = new THREE.PerspectiveCamera(60, 16/9, 0.1, 1000);
camera.position.set(0, 6, 12);
camera.lookAt(0, 3, 0);

// --- Lighting ---
const ambient = new THREE.AmbientLight(0xffffff, 0.5);
scene.add(ambient);
const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
dirLight.position.set(5, 10, 5);
dirLight.castShadow = true;
scene.add(dirLight);

// --- Ground + Grid ---
const groundGeo = new THREE.PlaneGeometry(20, 20);
const groundMat = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.8 });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
scene.add(new THREE.GridHelper(20, 20, 0x444444, 0x222222));

// --- Physics World ---
const world = new CANNON.World();
world.gravity.set(0, -9.82, 0);

// Ground physics
const groundBody = new CANNON.Body({ mass: 0, shape: new CANNON.Plane() });
groundBody.quaternion.setFromAxisAngle(new CANNON.Vec3(1, 0, 0), -Math.PI / 2);
world.addBody(groundBody);

// --- Ball (dynamic) ---
const radius = 0.5;
const ballGeo = new THREE.SphereGeometry(radius, 32, 32);
const ballMat = new THREE.MeshStandardMaterial({ color: 0xff4444, roughness: 0.4, metalness: 0.3 });
const ballMesh = new THREE.Mesh(ballGeo, ballMat);
ballMesh.castShadow = true;
scene.add(ballMesh);

const ballBody = new CANNON.Body({ mass: 1, shape: new CANNON.Sphere(radius) });
ballBody.position.set(0, 10, 0);
world.addBody(ballBody);

// --- GUI ---
const gui = new GUI({ title: 'Controls' });
gui.add({ reset: () => { ballBody.position.set(0, 10, 0); ballBody.velocity.set(0, 0, 0); } }, 'reset').name('Reset Ball');

// --- Update Loop ---
function update() {
    world.step(1 / 60);
    ballMesh.position.copy(ballBody.position);
    ballMesh.quaternion.copy(ballBody.quaternion);
}

// CRITICAL: Return 'world' for visual helper!
return {
    rendererParameters: { antialias: true, alpha: true },
    scene: scene,
    camera: camera,
    world: world, // <--- MUST INCLUDE THIS
    render: update
};
```

```json
{
    "title": "Free Fall",
    "description": "A ball dropped from 10m under gravity (g = 9.82 m/s²)"
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
