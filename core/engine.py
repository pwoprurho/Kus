# core/engine.py
import os
from google import genai
from google.genai import types
from services.mcp_tools import MCP_TOOLKIT

class KusmusAIEngine:
    def __init__(self, system_instruction, model_name="gemini-2.0-flash-thinking-exp"):
        # USAGE: pip install google-genai
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = model_name
        self.system_instruction = system_instruction
        self.forensic_memory = [] 

    def generate_response(self, message, history=[], context_logs=[], tools=None):
        thought_trace = []
        final_text = ""
        
        # --- 1. GLOBAL OVERRIDE CHECK ---
        override_cmds = ["stop", "abort", "revert", "cancel", "hold"]
        if any(cmd in message.lower() for cmd in override_cmds):
            return "Protocol Halted. System standing down. Control returned to human operator.", "CRITICAL: Manual Override Triggered by User. Halting all autonomous functions."

        # --- 2. FORENSIC CONTEXT INGESTION ---
        # We inject the last 20 lines of logs so the AI can "see" the attack
        live_telemetry = "\n".join(context_logs[-20:]) if context_logs else "No active logs."
        
        full_instruction = f"""{self.system_instruction}
        
        === LIVE TELEMETRY CONTEXT ===
        {live_telemetry}
        """
        
        # --- 3. THINKING & TOOL CONFIGURATION ---
        # Convert tool dictionary to list of callables for the SDK
        tool_list = [t for t in MCP_TOOLKIT.values()] if MCP_TOOLKIT else []
        
        config = types.GenerateContentConfig(
            system_instruction=full_instruction,
            # 16k token budget for deep reasoning
            thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=16000),
            tools=tool_list 
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=message,
                config=config
            )

            # --- 4. EXTRACT THOUGHTS VS RESPONSE ---
            # The model returns parts; some are text, some are thoughts.
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'thought') and part.thought:
                    thought_trace.append(part.thought)
                elif hasattr(part, 'text') and part.text:
                    final_text += part.text
            
            # Fallback if thoughts aren't separated in this specific model version
            if not thought_trace and not final_text:
                final_text = response.text

        except Exception as e:
            final_text = f"[SYSTEM_ERROR]: Cognitive Engine offline. {str(e)}"
            thought_trace.append("Error connecting to Gemini 2.0 Flash Thinking model.")

        return final_text, "\n\n".join(thought_trace)