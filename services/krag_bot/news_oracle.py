import feedparser
import logging
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from .ai_analysis import AIAnalyzer

logger = logging.getLogger(__name__)

class NewsOracle:
    """
    The Oracle: Fetches real-world news and uses AI to determine market sentiment.
    """
    def __init__(self, config):
        self.config = config
        self.ai_analyzer = AIAnalyzer(model_name=config.get('ai_model_name', 'gemini-2.5-flash'))
        
        # Real-world crypto/finance RSS feeds
        self.rss_feeds = config.get('news_rss_feeds', [
            "https://cointelegraph.com/rss",
            "https://feeds.feedburner.com/CoinDesk",
            "https://www.investing.com/rss/news.rss" 
        ])
        
        self.last_analysis_time = None
        self.cached_sentiment = 0
        self.cached_impact_summary = ""

    def fetch_latest_news(self, limit=5):
        """Fetches and parses real news from RSS feeds."""
        news_items = []
        for url in self.rss_feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]: # Top 3 from each
                    # Clean HTML from summary
                    summary_text = BeautifulSoup(entry.summary, "html.parser").get_text()
                    news_items.append({
                        'title': entry.title,
                        'summary': summary_text,
                        'source': feed.feed.title,
                        'published': entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    })
            except Exception as e:
                logger.error(f"Error fetching RSS {url}: {e}")
        
        # Sort by latest (heuristic) and return top 'limit'
        return news_items[:limit]

    def get_sentiment_analysis(self, symbol):
        """
        Fetches news and asks Generative AI for a sentiment score (-10 to +10).
        Returns a dict with score, summary, and 'insider' flags.
        """
        # Cache to prevent spamming AI every second
        if self.last_analysis_time and (datetime.now() - self.last_analysis_time).total_seconds() < 900: # 15 min cache
            logger.info("Using cached news sentiment.")
            return {
                "score": self.cached_sentiment,
                "summary": self.cached_impact_summary
            }

        news = self.fetch_latest_news()
        if not news:
            return {"score": 0, "summary": "No news found."}

        # Prompt for the AI
        prompt = f"""
        You are 'The Oracle', a financial news analyzer for a hedge fund.
        Analyze the following real-time news headlines regarding {symbol} and the general market:
        
        {news}
        
        Tasks:
        1. Determine the Sentiment Score from -10 (Market Crash/Panic) to +10 (Euphoria/Bull Run).
        2. Identify any "High Impact" events (Regulation, Hacks, Mergers, Earnings).
        3. Provide a short summary reasoning.
        
        Output JSON:
        {{
            "sentiment_score": <float>,
            "high_impact_event": <bool>,
            "reasoning": "<string>"
        }}
        """

        try:
            if not self.ai_analyzer.model:
                 logger.warning("AI model not initialized for News Oracle.")
                 return {"score": 0, "summary": "AI unavailable"}

            response = self.ai_analyzer.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            import json
            result = json.loads(response.text)
            
            self.cached_sentiment = result.get('sentiment_score', 0)
            self.cached_impact_summary = result.get('reasoning', 'No reasoning provided')
            self.last_analysis_time = datetime.now()
            
            logger.info(f"Oracle Analysis Complete: Score {self.cached_sentiment}. {self.cached_impact_summary}")
            return result
            
        except Exception as e:
            logger.error(f"Oracle Analysis Failed: {e}")
            return {"score": 0, "summary": "Analysis Error"}
