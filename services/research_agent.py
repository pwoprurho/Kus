import os
import json
import re
import time
import uuid
from google import genai
from google.genai import types
from core.key_manager import key_manager

# Initialize client with rotation support
def get_client():
    api_key = key_manager.get_current_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def parse_tasks(text):
    """Parses numbered tasks from the plan text."""
    return [{"num": m.group(1), "text": m.group(2).strip().replace('\n', ' ')} 
            for m in re.finditer(r'^(\d+)[\.\)\-]\s*(.+?)(?=\n\d+[\.\)\-]|\n\n|\Z)', text, re.MULTILINE | re.DOTALL)]

class ResearchAgentService:
    @staticmethod
    def _call_with_fallback(prompt, config, model_override=None, sovereign_config=None):
        """Helper to call Gemini or Sovereign backend with fallback."""
        if sovereign_config and sovereign_config.get('base_url'):
            from openai import OpenAI
            try:
                client = OpenAI(
                    api_key=sovereign_config.get('api_key'),
                    base_url=sovereign_config.get('base_url')
                )
                response = client.chat.completions.create(
                    model=model_override or "sovereign",
                    messages=[
                        {"role": "system", "content": config.system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    timeout=120
                )
                # Mock a Gemini-like response object for compatibility
                class MockResponse:
                    def __init__(self, text): self.text = text
                return MockResponse(response.choices[0].message.content)
            except Exception as e:
                print(f"   [Research] Sovereign Node Failed: {e}. Falling back to Gemini...")
        
        models_to_try = [model_override] if model_override else ["gemini-2.5-flash", "gemini-2.0-flash"]
        
        last_error = None
        for model in models_to_try:
            for _ in range(2): # Try twice per model (with rotation)
                client = get_client()
                if not client: return {"error": "No API Key"}
                
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                    return response
                except Exception as e:
                    last_error = str(e)
                    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                        print(f"   [Research] Quota hit for {model}. Rotating key...")
                        key_manager.rotate_key()
                        continue
                    return {"error": last_error}
        
        return {"error": f"Quota exhausted on all models/keys. Last error: {last_error}"}

    @staticmethod
    def create_plan(goal: str, sovereign_config=None):
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())] if not sovereign_config else None,
                system_instruction="You are a research architect. Create a detailed research plan with 5-8 numbered tasks."
            )
            
            response = ResearchAgentService._call_with_fallback(
                f"Create a numbered research plan for: {goal}\n\nFormat: 1. [Task] - [Details]",
                config,
                sovereign_config=sovereign_config
            )
            
            if isinstance(response, dict) and "error" in response:
                return response

            plan_text = response.text
            tasks = parse_tasks(plan_text)
            
            return {
                "plan_id": str(uuid.uuid4()),
                "plan_text": plan_text,
                "tasks": tasks
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def execute_research_task(plan_id: str, task_text: str, previous_context: str = "", sovereign_config=None):
        """Executes a single research task with context of previous findings."""
        try:
            prompt = f"""
            TASK: {task_text}
            
            CONTEXT FROM PREVIOUS VECTORS:
            {previous_context or "No previous context."}
            
            INSTRUCTIONS:
            1. Research the task thoroughly using available tools.
            2. Provide a detailed, technical breakdown of findings.
            3. CRITICAL: Identify 2-3 'Emergent Sub-Vectors' (highly specific follow-up areas) based on your findings.
            
            FORMAT:
            --- FINDINGS ---
            [Detailed findings here]
            
            --- EMERGENT SUB-VECTORS ---
            1. [Sub-Vector Title] - [Reasoning]
            2. [Sub-Vector Title] - [Reasoning]
            """
            
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())] if not sovereign_config else None,
                system_instruction="You are a deep research intelligence agent. Focus on granular technical details and identifying high-value follow-up vectors."
            )
            
            response = ResearchAgentService._call_with_fallback(prompt, config, sovereign_config=sovereign_config)
            
            if isinstance(response, dict) and "error" in response:
                return response

            findings_text = response.text
            
            # Parse sub-vectors for dynamic expansion
            sub_vectors = []
            sv_match = re.search(r'--- EMERGENT SUB-VECTORS ---\n(.*?)(?=\Z|---)', findings_text, re.DOTALL)
            if sv_match:
                sub_vectors = parse_tasks(sv_match.group(1))

            # Store incremental findings
            task_id = str(uuid.uuid4())[:8]
            result_dir = f"data/research/{plan_id}"
            os.makedirs(result_dir, exist_ok=True)
            with open(f"{result_dir}/{task_id}.txt", "w", encoding="utf-8") as f:
                f.write(findings_text)
            
            return {
                "task_id": task_id,
                "findings": findings_text,
                "sub_vectors": sub_vectors
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def execute_research(plan_id: str, selected_tasks: list, sovereign_config=None):
        # Legacy entry point - redirected to task-by-task if possible or kept for bulk
        # For now, keeping as a bulk fallback but recommending the task-specific route
        try:
            task_list_str = "\n\n".join(selected_tasks)
            prompt = f"Research these tasks thoroughly and provide detailed findings with sources:\n\n{task_list_str}"
            
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval())] if not sovereign_config else None,
                system_instruction="You are a deep research intelligence agent. Provide exhaustive details for each task."
            )
            
            response = ResearchAgentService._call_with_fallback(prompt, config, sovereign_config=sovereign_config)
            
            if isinstance(response, dict) and "error" in response:
                return response

            research_id = str(uuid.uuid4())
            os.makedirs("data/research", exist_ok=True)
            with open(f"data/research/{research_id}.txt", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            return {
                "research_id": research_id,
                "status": "completed" 
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_status(interaction_id: str):
        if os.path.exists(f"data/research/{interaction_id}.txt"):
            return {"id": interaction_id, "status": "completed"}
        return {"id": interaction_id, "status": "unknown"}

    @staticmethod
    def generate_report(research_id: str, plan_id: str = None, sovereign_config=None):
        try:
            research_text = ""
            if plan_id:
                # Synthesize from incremental task files
                result_dir = f"data/research/{plan_id}"
                if os.path.exists(result_dir):
                    files = sorted(os.listdir(result_dir))
                    for filename in files:
                        if filename.endswith(".txt"):
                            with open(f"{result_dir}/{filename}", "r", encoding="utf-8") as f:
                                research_text += f"\n\n--- TASK FINDINGS ---\n{f.read()}"
            
            if not research_text:
                # Fallback to single file
                try:
                    with open(f"data/research/{research_id}.txt", "r", encoding="utf-8") as f:
                        research_text = f.read()
                except FileNotFoundError:
                    return {"error": "Research findings not found"}

            config = types.GenerateContentConfig(
                system_instruction="You are a senior analyst. Write a concise, high-impact executive report in Markdown. Synthesize the findings into a cohesive narrative."
            )
            
            response = ResearchAgentService._call_with_fallback(
                f"Based on the following research findings, create a professional executive report. Include a Summary, Strategic Implications (how this affects institutional autonomy), Detailed Analysis, and Risks.\n\nResearch Findings:\n{research_text}",
                config,
                sovereign_config=sovereign_config
            )
            
            if isinstance(response, dict) and "error" in response:
                return response
            
            return {
                "report_id": str(uuid.uuid4()),
                "report_text": response.text,
                "infographic": None
            }
        except Exception as e:
            return {"error": str(e)}
