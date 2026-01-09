import google.generativeai as genai
import os
import logging
import pandas as pd
import json

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, api_key=None, model_name="gemini-2.5-flash-lite"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. AI analysis will be disabled.")
            self.model = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"AI Analyzer initialized with model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize AI Analyzer: {e}")
                self.model = None

    def analyze_market(self, symbol, df_ltf, current_signals):
        """
        Sends market data and technical signals to Gemini for analysis.
        
        Args:
            symbol (str): The trading symbol.
            df_ltf (pd.DataFrame): The recent price data (tail).
            current_signals (dict): The technical signals identified by the strategy.
            
        Returns:
            dict: AI analysis result including 'decision', 'confidence', and 'reasoning'.
        """
        if not self.model:
            return {"decision": "NEUTRAL", "confidence": 0, "reasoning": "AI disabled"}

        # Prepare context for the AI
        # We take the last 5 candles for context
        recent_data = df_ltf.tail(5).to_dict(orient='records')
        
        # Construct the prompt
        prompt = f"""
        You are an expert financial market analyst. Analyze the following data for {symbol} and provide a trading decision.
        
        Recent Market Data (last 5 intervals):
        {json.dumps(recent_data, default=str)}
        
        Technical Signals Detected:
        {json.dumps(current_signals, default=str)}
        
        Task:
        1. Analyze the price action and technical indicators.
        2. Validate the detected technical signals.
        3. Provide a decision: BUY, SELL, or HOLD.
        4. Provide a confidence score (0-100).
        5. Briefly explain your reasoning.
        
        Response Format (JSON):
        {{
            "decision": "BUY" | "SELL" | "HOLD",
            "confidence": <int>,
            "reasoning": "<string>"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            result = json.loads(response.text)
            logger.info(f"AI Analysis for {symbol}: {result}")
            return result
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return {"decision": "NEUTRAL", "confidence": 0, "reasoning": f"Error: {e}"}
