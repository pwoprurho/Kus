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

BASE_GENERATION_PROMPT = """
You are a STEM Simulation Architect building structured JSON blueprints. 
You will not write Javascript code. Instead, you will define the environment, entities, and physics rules in a strictly formatted JSON object. 

=== ARCHITECTURAL LAYERS ===
1. **Config**: Define gravity, camera position, and renderer settings.
2. **Entities**: Define objects (spheres, boxes, planes). Every entity has an id, type, mass (0 for static), dimensions, position, and color.
3. **Constraints**: Define mechanical links (e.g., pointToPoint) between entities.

=== UNIVERSAL STANDARDS ===
- Physics Engine: Cannon.js concepts apply (restitution, friction, mass).
- Graphics: Three.js concepts apply.
- Use metric units (meters, kg).

=== STRICT OUTPUT FORMAT ===
Your response MUST be valid, parseable JSON wrapped in a ```json``` block. Do not include any Javascript.

{
  "title": "Simulation Title",
  "concept": "Core scientific concept",
  "description": "Detailed explanation",
  "config": {
    "gravity": [0, -9.82, 0],
    "cameraPos": [0, 5, 15],
    "lookAt": [0, 0, 0]
  },
  "entities": [
    { "id": "ground", "type": "plane", "mass": 0, "size": [100, 100], "position": [0, 0, 0], "rotation": [-1.5708, 0, 0], "color": "0x808080" },
    { "id": "bob", "type": "sphere", "mass": 1.0, "radius": 0.5, "position": [0, 3, 0], "color": "0xff0000", "restitution": 0.7 }
  ],
  "constraints": [
    { "id": "hinge", "type": "pointToPoint", "bodyA": "bob", "bodyB": "pivot", "pivotA": [0, 0, 0], "pivotB": [0, 0, 0] }
  ]
}
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

    def fix_simulation(self, failed_code: str, error_msg: str, subject_name: str = "physics") -> dict:
        """
        Self-healing loop: Analyze error and re-generate code.
        """
        subject = self.get_subject_logic(subject_name)
        prompt = f"""
        ERROR DETECTED IN SIMULATION CODE:
        {error_msg}

        FAILING CODE:
        {failed_code}

        STRICT INSTRUCTION:
        1. Identify what caused the error (e.g., missing entity ID, invalid number, bad constraint type).
        2. Re-write the JSON blueprint to FIX the error while maintaining the original simulation intent.
        3. Ensure the output is strictly valid JSON format mapping to the STEM Engine JSON schema.
        """
        
        engine = KusmusAIEngine(
            system_instruction=BASE_GENERATION_PROMPT + "\n" + subject.GENERATION_PROMPT_ADDITION,
            model_name=self.generation_model
        )
        
        response_text, thought_trace = engine.generate_response(prompt)
        result = self._parse_json(response_text)
        if "errors" not in result:
            result["thought_trace"] = thought_trace
            result["model_used"] = self.generation_model
        return result

    def _parse_state(self, text: str, default_subject: str) -> dict:
        # Improved parsing for complex design docs
        match = re.search(r'\[STATE:\s*({.*?})\s*\]', text, re.DOTALL)
        if match:
            try:
                state_str = match.group(1).replace('\n', ' ')
                state = json.loads(state_str)
                if 'subject' not in state: state['subject'] = default_subject
                return state
            except:
                pass
        return {"subject": default_subject, "ready": False}

    def _parse_json(self, text: str) -> dict:
        result = {}
        code_match = re.search(r'```(?:javascript|js)\s*(.*?)\s*```', text, flags=re.DOTALL)
        if code_match:
            result["threejs_code"] = code_match.group(1).strip()
        
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
