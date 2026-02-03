# core/physics_ai.py
"""
Physics AI Engine
Converts natural language experiment descriptions to Three.js + Cannon-es code.
Uses Gemini 3.0 Flash (with 2.5 Flash fallback).
"""

import json
import re
from core.engine import KusmusAIEngine
from core.key_manager import key_manager


# System prompt for physics experiments
PHYSICS_SYSTEM_PROMPT = """
You are a Physics Lab Assistant powered by Gemini 3.0 Flash (or Gemini 2.5 Flash as fallback) that converts natural language experiment descriptions into Three.js + Cannon-es visualization code.

Your mission is to create INTERACTIVE, EDUCATIONAL, and BEAUTIFUL physics simulations similar to PhET.

Core Guidelines:
1. Parse descriptions into physical objects (spheres, boxes, planes, springs, pendulums, etc.).
2. Extract or infer parameters: mass, velocity, gravity, friction, restitution, spring constants, electric field strength, etc.
3. INCLUDE SLIDERS: Every experimental object should have at least 2-3 adjustable parameters defined in the "adjustable" field. These should be rendered in the UI as sliders.
4. INCLUDE VISUAL FEEDBACK: Draw force vectors (arrows), paths (trails/dots), or heatmaps where applicable to aid understanding.
5. COMPLETE CODE: Generate 100% valid, self-contained Three.js + Cannon-es code. No placeholders.

Output Format (JSON):
{
    "title": "Descriptive title (e.g., 'Harmonic Oscillation Lab')",
    "description": "Educational summary of the experiment's goal",
    "concept": "The primary physics principle (e.g., 'Hooke's Law')",
    "threejs_code": "Complete, executable JavaScript code in an IIFE",
    "physics_config": {
        "gravity": [0, -9.81, 0],
        "timeScale": 1.0
    },
    "objects": [
        {
            "id": "obj_1",
            "name": "Moving Charge",
            "type": "sphere",
            "position": [0, 5, 0],
            "physics": {
                "mass": 1,
                "velocity": [10, 0, 0],
                "charge": 5e-6
            },
            "adjustable": {
                "mass": {"min": 0.1, "max": 10, "step": 0.1, "value": 1, "label": "Mass (kg)"},
                "velocity_x": {"min": -20, "max": 20, "step": 1, "value": 10, "label": "Initial Velocity X"}
            }
        }
    ],
    "parameters": {
        "gravity": {"min": 0, "max": 20, "value": 9.81, "label": "Gravity (m/s²)"},
        "timeScale": {"min": 0.1, "max": 3, "value": 1.0, "label": "Simulation Speed"}
    },
    "estimated_runtime": 5000,
    "errors": []
}

Detailed Code Constraints:
- Use Cannon.js for the physical simulation.
- Use THREE.MeshStandardMaterial with light sources for a premium look.
- Use Cannon.PointToPointConstraint for pendulums.
- Use Cannon.Spring for elastic components.
- ADD MEASURABLE DATA: If the user asks for a graph or values, include code that logs these values or displays them on-screen using THREE.TextGeometry or simple DOM overlays.

Generate a COMPLETE response including the JSON structure.
"""


class PhysicsAIEngine:
    """
    Physics-specific AI engine using Gemini 2.5 Flash Lite.
    """
    
    def __init__(self, model_name=None):
        self.model_name = model_name or "gemini-2.5-flash-lite"
        self.system_instruction = PHYSICS_SYSTEM_PROMPT
    
    def generate_experiment_code(self, description: str) -> dict:
        """
        Converts natural language to Three.js + physics code.
        
        Args:
            description: Natural language experiment description
            
        Returns:
            dict with keys: title, description, concept, threejs_code, 
                          physics_config, objects, parameters, errors
        """
        try:
            # Create AI engine instance
            engine = KusmusAIEngine(
                system_instruction=self.system_instruction,
                model_name=self.model_name
            )
            
            # Generate response
            response_text, thought_trace = engine.generate_response(
                f"Generate a physics experiment for: {description}"
            )
            
            # Parse JSON from response
            result = self._parse_response(response_text)
            
            if not result.get('threejs_code'):
                result['errors'] = result.get('errors', []) + ["Failed to generate code"]
            
            return result
            
        except Exception as e:
            return {
                "title": "Error",
                "description": description,
                "concept": "Physics",
                "threejs_code": "",
                "physics_config": {},
                "objects": [],
                "parameters": {},
                "errors": [f"AI generation failed: {str(e)}"]
            }
    
    def _parse_response(self, response_text: str) -> dict:
        """
        Parse the AI response and extract JSON.
        """
        try:
            # Look for JSON block in response
            json_pattern = r'```json\s*(\{.*?\})\s*```'
            match = re.search(json_pattern, response_text, flags=re.DOTALL)
            
            if match:
                json_str = match.group(1)
                result = json.loads(json_str)
                
                # Also extract code if in separate block
                code_pattern = r'```javascript\s*(.*?)\s*```'
                code_match = re.search(code_pattern, response_text, flags=re.DOTALL)
                if code_match:
                    result['threejs_code'] = code_match.group(1).strip()
                
                return result
            
            # Try to parse entire response as JSON
            return json.loads(response_text)
            
        except json.JSONDecodeError:
            # If no JSON found, create a basic response
            return {
                "title": "Physics Experiment",
                "description": response_text[:100],
                "concept": "Physics",
                "threejs_code": self._generate_fallback_code(response_text),
                "physics_config": {"gravity": [0, -9.81, 0], "timeScale": 1.0},
                "objects": [],
                "parameters": {},
                "errors": ["Could not parse AI response, using fallback"]
            }
    
    def _generate_fallback_code(self, description: str) -> str:
        """
        Generate a simple fallback visualization.
        """
        return f"""
// Fallback visualization for: {description}
// Please try a more specific description

(function() {{
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 5, 10);
    camera.lookAt(0, 0, 0);
    
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);
    
    // Basic lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 10, 5);
    scene.add(directionalLight);
    
    // Ground
    const planeGeometry = new THREE.PlaneGeometry(20, 20);
    const planeMaterial = new THREE.MeshStandardMaterial({{ color: 0x444444 }});
    const plane = new THREE.Mesh(planeGeometry, planeMaterial);
    plane.rotation.x = -Math.PI / 2;
    scene.add(plane);
    
    function animate() {{
        requestAnimationFrame(animate);
        renderer.render(scene, camera);
    }}
    animate();
}})();
"""
    
    def generate_with_fallback(self, description: str) -> dict:
        """
        Generate experiment with fallback to 2.5 Flash if 3.0 fails.
        """
        result = self.generate_experiment_code(description)
        
        if result.get('errors') and 'model' in str(result.get('errors', [''])).lower():
            # Try with 2.5 Flash fallback
            self.model_name = "gemini-2.5-flash-lite"
            result = self.generate_experiment_code(description)
            self.model_name = "gemini-3.0-flash-lite"  # Reset
        
        return result
