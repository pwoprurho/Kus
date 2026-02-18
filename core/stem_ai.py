# core/stem_ai.py
"""
STEM AI Engine (Conversational Gateway)
Handles routing to subject-specific agents and unified code generation.
"""

import json
import re
from core.engine import KusmusAIEngine
from core.physics_ai import PhysicsSubject
from core.maths_ai import MathsSubject
from core.biology_ai import BiologySubject
from core.chemistry_ai import ChemistrySubject

# Shared base for generation
BASE_GENERATION_PROMPT = """
You are a STEM Simulation Architect. Generate 100% executable Three.js + Cannon.js code.
The available globals are: `THREE` (r128), `CANNON` (0.6.2), and `lil.GUI`. Do NOT use import/export.

=== UNIVERSAL STANDARDS ===
- Materials: `THREE.MeshStandardMaterial({ roughness: 0.4, metalness: 0.3 })`.
- Shadows: `castShadow = true` and `receiveShadow = true`.
- Lighting: Ambient + Directional (5, 10, 5).
- Controls: Use `lil.GUI` for parameters.

=== OUTPUT FORMAT ===
1. Full JavaScript in a ```javascript``` block.
2. Metadata in a ```json``` block.
3. **CRITICAL**: The JS **MUST** end with a top-level return statement: `return { scene, camera, rendererParameters, render, world };`. Do not wrap in a function.
"""

class StemAIEngine:
    def __init__(self):
        self.subjects = {
            "physics": PhysicsSubject,
            "maths": MathsSubject,
            "biology": BiologySubject,
            "chemistry": ChemistrySubject
        }
        self.planning_model = "gemini-2.5-flash"
        self.generation_model = "gemini-2.5-flash"

    def get_subject_logic(self, subject_name: str):
        return self.subjects.get(subject_name, PhysicsSubject)

    def chat_interact(self, message: str, subject_name: str = "physics", context_logs=None) -> dict:
        """
        Phase 1: Chat with user to gather details for a specific subject.
        """
        subject = self.get_subject_logic(subject_name)
        
        engine = KusmusAIEngine(
            system_instruction=subject.PLANNING_PROMPT,
            model_name=self.planning_model
        )
        
        response_text, thought_trace = engine.generate_response(message, context_logs=context_logs)
        
        state = self._parse_state(response_text, subject_name)
        clean_response = re.sub(r'\[STATE:.*?\]', '', response_text).strip()
        
        return {
            "response": clean_response,
            "state": state,
            "thought_trace": thought_trace
        }

    def generate_simulation(self, design_doc: str, subject_name: str = "physics", retries: int = 2) -> dict:
        """
        Phase 2: Generate high-fidelity code based on the subject's specialization.
        """
        subject = self.get_subject_logic(subject_name)
        full_system_prompt = BASE_GENERATION_PROMPT + "\n" + subject.GENERATION_PROMPT_ADDITION
        
        engine = KusmusAIEngine(
            system_instruction=full_system_prompt,
            model_name=self.generation_model
        )
        
        last_error = None
        for attempt in range(retries + 1):
            try:
                response_text, thought_trace = engine.generate_response(
                    f"Generate the full {subject_name.upper()} simulation code for this design: {design_doc}"
                )
                
                result = self._parse_json(response_text)
                if "errors" not in result:
                    result["thought_trace"] = thought_trace
                    result["model_used"] = self.generation_model
                    return result
                
                last_error = result["errors"][0]
            except Exception as e:
                last_error = str(e)
        
        return {"errors": [f"Deep Generation Failed. Last error: {last_error}"]}

    def generate_simulation_stream(self, design_doc: str, subject_name: str = "physics"):
        """
        Stream the high-fidelity code generation for real-time visualization.
        """
        subject = self.get_subject_logic(subject_name)
        full_system_prompt = BASE_GENERATION_PROMPT + "\n" + subject.GENERATION_PROMPT_ADDITION
        
        engine = KusmusAIEngine(
            system_instruction=full_system_prompt,
            model_name=self.generation_model,
            tools=[]
        )
        
        prompt = f"Generate the full {subject_name.upper()} simulation code for this design: {design_doc}"
        
        for chunk in engine.generate_response_stream(prompt):
            yield chunk

    def _parse_state(self, text: str, default_subject: str) -> dict:
        match = re.search(r'\[STATE:\s*({.*?})\s*\]', text)
        if match:
            try:
                state = json.loads(match.group(1))
                if 'subject' not in state: state['subject'] = default_subject
                return state
            except:
                pass
        return {"subject": default_subject, "ready": False}

    def _parse_json(self, text: str) -> dict:
        result = {}
        code_match = re.search(r'```(?:javascript|js)\s*(.*?)\s*```', text, flags=re.DOTALL)
        if code_match:
            result["threejs_code"] = code_match.group(1)
        
        json_match = re.search(r'```json\s*({.*?})\s*```', text, flags=re.DOTALL)
        if json_match:
            try:
                metadata = json.loads(json_match.group(1))
                result.update(metadata)
            except:
                pass
        
        if "threejs_code" in result:
             return result

        return {"errors": ["Could not parse code or metadata from response"]}
