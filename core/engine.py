import os
import google.generativeai as genai
from google.generativeai.types import Tool
from services.mcp_tools import MCP_TOOLKIT, get_server_health, trigger_incident_protocol

class KusmusAIEngine:
    def __init__(self, system_instruction, model_name="gemini-2.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        self.tools_obj = Tool(function_declarations=[
            get_server_health,
            trigger_incident_protocol
        ])

        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=[self.tools_obj]
        )

    def generate_response(self, message, history=[]):
        """
        Returns a tuple: (response_text, thought_trace)
        """
        formatted_history = [{"role": h["role"], "parts": h["parts"]} for h in history]
        chat = self.model.start_chat(history=formatted_history)
        
        # Initial thought trace for the UI
        thought_trace = [
            "Neural weights loaded.",
            f"Contextualizing directive: {message[:30]}...",
            "Searching MCP tool registry..."
        ]

        response = chat.send_message(message)
        
        try:
            part = response.parts[0]
            if part.function_call:
                fc = part.function_call
                thought_trace.append(f"EXEC-PROTOCOL: Triggering {fc.name}...")
                
                if fc.name in MCP_TOOLKIT:
                    tool_result = MCP_TOOLKIT[fc.name](**fc.args)
                    thought_trace.append(f"PROTOCOL-RETURN: Success. Data integrated.")
                    
                    final_response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fc.name,
                                    response={'result': tool_result}
                                )
                            )]
                        )
                    )
                    return final_response.text, thought_trace
        except Exception as e:
            thought_trace.append(f"TRACE-ERROR: {str(e)}")

        thought_trace.append("Inference cycle complete.")
        return response.text, thought_trace