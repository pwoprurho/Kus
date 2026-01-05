# core/engine.py

import os
import json
from google import genai
from google.genai import types
from services.mcp_tools import MCP_TOOLKIT
from core.key_manager import key_manager

class KusmusAIEngine:
    def __init__(self, system_instruction, model_name="gemini-2.5-flash", tools=None):
        # Use the provided model name, defaulting to gemini-2.5-flash
        self.model_id = model_name
        self.system_instruction = system_instruction
        # If tools are explicitly provided (even empty list), use them.
        # Otherwise, default to the standard MCP_TOOLKIT.
        if tools is not None:
            self.tools = tools
        else:
            self.tools = [t for t in MCP_TOOLKIT.values() if t is not None]

    def generate_response(self, message, history=[], context_logs=[]):
        thought_trace = []
        final_text = ""

        # 1. GLOBAL HUMAN OVERRIDE (robust)
        # Only trigger on exact commands to prevent false positives in conversation
        override_cmds = {"stop", "abort", "revert", "cancel", "hold", "terminate"}
        clean_msg = (message or "").strip().lower()
        if clean_msg in override_cmds or clean_msg.startswith("system override"):
            return "Protocol Halted. System standing down. Control returned to human operator.", ["CRITICAL: Manual Override Triggered."]

        # 2. FORENSIC MEMORY LAYER: Ingest last 15-20 lines of data/log.txt
        forensic_context = []
        try:
            with open("data/log.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                forensic_context = lines[-20:] if len(lines) > 20 else lines
        except Exception:
            forensic_context = []
        forensic_context = [l.strip() for l in forensic_context if l.strip()]

        # 3. CONTEXT INJECTION: Combine context_logs and forensic_context
        live_telemetry = "\n".join(context_logs[-20:] if context_logs else [])
        forensic_block = "\n".join(forensic_context)
        full_instruction = f"{self.system_instruction}\n\nLIVE_TELEMETRY:\n{live_telemetry}\n\nFORENSIC_MEMORY:\n{forensic_block}"

        # 4. GEMINI 2.5 FLASH THINKING CONFIG (Minimum 1024 budget for speed)
        config = types.GenerateContentConfig(
            system_instruction=full_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024),
            tools=self.tools
        )

        # Retry logic with key rotation
        max_retries = len(key_manager.get_all_keys()) * 2 # Try each key twice effectively
        if max_retries == 0: max_retries = 1
        
        last_exc = None
        
        for attempt in range(max_retries):
            current_key = key_manager.get_current_key()
            try:
                client = genai.Client(api_key=current_key)
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=message,
                    config=config
                )
                # 5. EXTRACT NATIVE THOUGHTS for Cognitive Trace HUD
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'thought') and part.thought:
                        thought_trace.append(part.thought)
                    elif hasattr(part, 'text') and part.text:
                        final_text += part.text
                if not final_text:
                    final_text = response.text
                return final_text, thought_trace
            except Exception as e:
                last_exc = e
                error_str = str(e)
                
                # Stop on 400 Bad Request (Configuration/Validation Error) to avoid wasting retries
                if "400" in error_str and not any(x in error_str for x in ["429", "quota", "403", "expired"]):
                     final_text = f"System Configuration Error: {error_str}"
                     thought_trace.append(f"Critical Error: {error_str}")
                     return final_text, thought_trace

                # Check for rate limit or auth errors
                if any(x in error_str.lower() for x in ["429", "quota", "403", "leaked", "expired", "invalid"]):
                    # print(f"   [Engine Error] {e}. Rotating key...")
                    key_manager.rotate_key()
                    continue
                else:
                    # For other errors, maybe don't rotate immediately, but we will for robustness
                    key_manager.rotate_key()
                    continue

        final_text = f"Sovereign System Error: {str(last_exc)}"
        thought_trace.append(f"Error connecting to Gemini 2.5 Flash. Last error: {str(last_exc)}")
        return final_text, thought_trace