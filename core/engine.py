# core/engine.py

import os
import json
from google import genai
from google.genai import types
from services.mcp_tools import MCP_TOOLKIT
from core.key_manager import key_manager

class KusmusAIEngine:
    def __init__(self, system_instruction, model_name="gemini-2.0-flash-exp", tools=None, enable_google_search=False):
        # Use the provided model name, defaulting to gemini-2.0-flash-exp
        self.model_id = model_name
        self.system_instruction = system_instruction
        # If tools are explicitly provided (even empty list), use them.
        # Otherwise, default to the standard MCP_TOOLKIT.
        if tools is not None:
            self.tools = list(tools) # Ensure it's a list copy
        else:
            self.tools = [t for t in MCP_TOOLKIT.values() if t is not None]
        
        # Add Google Search Tool if enabled
        if enable_google_search:
            try:
                # Add the Google Search tool configuration
                # Note: The exact syntax depends on the SDK version, assuming standard Tool object
                search_tool = types.Tool(google_search=types.GoogleSearch())
                self.tools.append(search_tool)
            except Exception as e:
                print(f"Warning: Failed to enable Google Search: {e}")

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
        # Handle context_logs being either list of strings or list of dicts
        def format_log(item):
            if isinstance(item, dict):
                return f"{item.get('role', 'user')}: {item.get('content', '')}"
            return str(item)
        
        live_telemetry = "\n".join(format_log(log) for log in (context_logs[-20:] if context_logs else []))
        forensic_block = "\n".join(forensic_context)
        full_instruction = f"{self.system_instruction}\n\nLIVE_TELEMETRY:\n{live_telemetry}\n\nFORENSIC_MEMORY:\n{forensic_block}"

        # 4. GEMINI 2.5 FLASH THINKING CONFIG (Minimum 1024 budget for speed)
        config = types.GenerateContentConfig(
            system_instruction=full_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024),
            tools=self.tools
        )

        # Retry logic with key rotation
        max_retries = len(key_manager.get_all_keys()) * 2  # Try each key twice
        if max_retries == 0: 
            max_retries = 1
        
        last_exc = None
        
        for attempt in range(max_retries):
            current_key = key_manager.get_current_key()
            key_index = key_manager.current_index
            
            try:
                client = genai.Client(api_key=current_key)
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=message,
                    config=config
                )
                
                # Check if response contains rate limit error text (sometimes returned in response)
                response_text = ""
                try:
                    response_text = response.text if hasattr(response, 'text') else ""
                except:
                    pass
                
                if response_text and any(x in response_text.lower() for x in ["429", "quota", "resource_exhausted"]):
                    # Response contains rate limit info - rotate and retry
                    import time
                    print(f"[Key {key_index}] Rate limit detected in response, rotating...")
                    time.sleep(3)
                    key_manager.rotate_key()
                    continue
                
                # 5. EXTRACT NATIVE THOUGHTS for Cognitive Trace HUD
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'thought') and part.thought:
                        if isinstance(part.thought, bool):
                            thought_trace.append(part.text)
                        else:
                            thought_trace.append(part.thought)
                    elif hasattr(part, 'text') and part.text:
                        final_text += part.text
                if not final_text:
                    final_text = response.text
                    
                # Success - return the response
                return final_text, thought_trace
                
            except Exception as e:
                last_exc = e
                error_str = str(e)
                
                # Stop on 400 Bad Request (Configuration/Validation Error)
                if "400" in error_str and not any(x in error_str for x in ["429", "quota", "403", "expired"]):
                    final_text = f"System Configuration Error: {error_str}"
                    thought_trace.append(f"Critical Error: {error_str}")
                    return final_text, thought_trace

                # Check for rate limit or auth errors
                if any(x in error_str.lower() for x in ["429", "quota", "resource_exhausted", "403", "leaked", "expired", "invalid"]):
                    import time
                    import re
                    
                    # Try to parse retry delay from error message
                    delay_match = re.search(r'retry\s*(?:in|after)?\s*(\d+(?:\.\d+)?)\s*s', error_str.lower())
                    wait_time = float(delay_match.group(1)) if delay_match else 3.0
                    wait_time = min(wait_time, 10.0)  # Cap at 10 seconds
                    
                    print(f"[Key {key_index}] Rate limit hit, waiting {wait_time:.1f}s before rotating...")
                    time.sleep(wait_time)
                    key_manager.rotate_key()
                    continue
                else:
                    # For other errors, rotate and retry
                    key_manager.rotate_key()
                    continue

        final_text = f"Sovereign System Error: {str(last_exc)}"
        thought_trace.append(f"Error connecting to Gemini. All {len(key_manager.get_all_keys())} keys exhausted. Last error: {str(last_exc)}")
        return final_text, thought_trace

    def generate_response_stream(self, message, history=[], context_logs=[]):
        """Generates a streaming response for real-time frontend updates."""
        print(f"DEBUG: Starting stream for model {self.model_id}")
        
        try:
            # 1. Prepare Context (same as generate_response)
            forensic_context = []
            try:
                with open("data/log.txt", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    forensic_context = lines[-20:] if len(lines) > 20 else lines
            except Exception:
                pass
            forensic_context = [l.strip() for l in forensic_context if l.strip()]
            
            live_telemetry = "\n".join(context_logs[-20:] if context_logs else [])
            forensic_block = "\n".join(forensic_context)
            
            full_instruction = f"{self.system_instruction}\n\nLIVE_TELEMETRY:\n{live_telemetry}\n\nFORENSIC_MEMORY:\n{forensic_block}"

            # 2. Config (using thinking_budget for Gemini 2.5)
            # Ensure tools is a list of Tool objects or None
            # The SDK expects 'tools' in config to be distinct from 'tools' functions if using function calling
            # But for Search, it's a Tool object.
            
            # Helper to determine if model supports thinking
            # We boldly attempt to enable it for 2.5-flash as requested
            is_thinking_candidate = "thinking" in self.model_id.lower() or "flash" in self.model_id.lower()
            
            gen_config_args = {
                "system_instruction": full_instruction,
                "tools": self.tools if self.tools else None
            }
            
            # Create two configs: one with thinking, one without
            config_thinking = None
            if is_thinking_candidate:
                args_copy = gen_config_args.copy()
                # Increased budget to allow for complete chain-of-thought before tool invocation
                args_copy["thinking_config"] = types.ThinkingConfig(include_thoughts=True, thinking_budget=4096)
                config_thinking = types.GenerateContentConfig(**args_copy)

            config_standard = types.GenerateContentConfig(**gen_config_args)

            current_key = key_manager.get_current_key()
            client = genai.Client(api_key=current_key)
        
            # enable streaming
            print("DEBUG: Calling generate_content_stream...")
            response_stream = None
            
            # Attempt 1: With Thinking (if eligible)
            if config_thinking:
                try:
                    print(f"DEBUG: Attempting with Thinking Config for {self.model_id}")
                    response_stream = client.models.generate_content_stream(
                        model=self.model_id,
                        contents=message,
                        config=config_thinking
                    )
                    # Iterate once to verify stream validity (optional, but finding error early is good)
                    # actually we can't iterate without consuming. Just assume it works if no error raised immediately.
                except Exception as e:
                    print(f"DEBUG: Thinking config failed ({e}). Fallback to standard.")
                    response_stream = None

            # Attempt 2: Standard (Fallback or default)
            if response_stream is None:
                try:
                    print(f"DEBUG: Attempting Standard Config for {self.model_id}")
                    response_stream = client.models.generate_content_stream(
                        model=self.model_id,
                        contents=message,
                        config=config_standard
                    )
                except Exception as e:
                     # Fallback mechanism for 404/Not Found models
                    error_str = str(e).lower()
                    print(f"DEBUG: Primary model failed with: {error_str}")
                    
                    if "404" in error_str or "not found" in error_str or "unsupported" in error_str:
                        print(f"DEBUG: Model {self.model_id} not found. Fallback to gemini-2.0-flash-lite.")
                        # Use a model we SAW in the list
                        response_stream = client.models.generate_content_stream(
                            model="gemini-2.0-flash-lite", 
                            contents=message,
                            config=config_standard # Use standard config for fallback
                        )
                    else:
                        raise e
            
            print("DEBUG: Entering stream loop...")
            
            print("DEBUG: Entering stream loop...")
            chunk_count = 0
            for chunk in response_stream:
                chunk_count += 1
                if chunk and hasattr(chunk, 'candidates') and chunk.candidates:
                    cand = chunk.candidates[0]
                    # Check for content presence
                    if hasattr(cand, 'content') and cand.content and hasattr(cand.content, 'parts'):
                        for part in cand.content.parts:
                            is_thought_part = False
                            
                            # 1. Handle "Thinking" content
                            if hasattr(part, 'thought') and part.thought:
                                is_thought_part = True
                                thought_text = part.text if (isinstance(part.thought, bool) and part.thought) else str(part.thought)
                                if thought_text:
                                    yield {"type": "thought", "content": thought_text}
                            
                            # 2. Handle Standard Text Content
                            if hasattr(part, 'text') and part.text:
                                # If it was marked as thought (boolean True implies text is thought), skip content yield.
                                # Otherwise, yield as content.
                                # Note: Some models return separate parts for thought vs text.
                                if not is_thought_part:
                                    yield {"type": "content", "content": part.text}

                            # 3. Handle Function Calls (Simulated Tool Execution)
                            if hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                f_name = fc.name
                                f_args = fc.args
                                
                                # Convert Struct/Map to dict if necessary (depending on SDK version)
                                # Usually SDK returns a dict-like object for args
                                args_dict = {}
                                if hasattr(f_args, 'items'):
                                    args_dict = {k: v for k, v in f_args.items()}
                                else:
                                    args_dict = f_args # Hope it's a dict or None
                                
                                yield {"type": "thought", "content": f"Invoking Tool: `{f_name}` with args: {str(args_dict)}"}

                                # Execute Tool from Registry
                                if f_name in MCP_TOOLKIT:
                                    try:
                                        tool_func = MCP_TOOLKIT[f_name]
                                        # Call the function with unpacked args
                                        result = tool_func(**args_dict)
                                        
                                        # Format result for display
                                        result_str = json.dumps(result, indent=2)
                                        output_md = f"\n\n**Tool Execution Result `{f_name}`:**\n```json\n{result_str}\n```\n"
                                        
                                        yield {"type": "content", "content": output_md}
                                    except Exception as tool_err:
                                        err_msg = f"\n\n**Tool Error:** {str(tool_err)}"
                                        yield {"type": "content", "content": err_msg}
                                else:
                                    yield {"type": "content", "content": f"\n\n**System Error:** Tool `{f_name}` attempted but not found in registry."}

            if chunk_count == 0:
                print("DEBUG: Stream yielded 0 chunks.")
                yield {"type": "content", "content": " [System: Neural engine yielded 0 content chunks. Connection reset.]"}
            
            print("DEBUG: Stream finished.")
                             
        except Exception as e:
            print(f"DEBUG: Steam Error {e}")
            yield {"type": "error", "content": f"Engine Error: {str(e)}"}