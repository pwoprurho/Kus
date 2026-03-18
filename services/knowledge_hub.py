import time
import json
import hashlib
from typing import List, Dict, Any

class KnowledgeHub:
    """
    Server-side aggregator for the Knowledge Vault.
    Handles news scouting, vectorization, and cache freshness.
    """
    
    def __init__(self):
        self.volatile_data = [] # Stores news chunks with TTL
        self.last_scout_time = 0

    def scout_news(self) -> List[Dict[str, Any]]:
        """
        Simulates a deep scout of global market news.
        In production, this calls specialized News Scout agents.
        """
        print("[KnowledgeHub] Scouting global news feeds...")
        
        # Simulated signals
        signals = [
            {"id": "s1", "text": "NVDA announces new B200 chips, expect high demand.", "category": "Tech", "priority": 1},
            {"id": "s2", "text": "Federal Reserve signals potential rate cut in June.", "category": "Macro", "priority": 2},
            {"id": "s3", "text": "Ethereum spot ETF approval odds jump to 75%.", "category": "Crypto", "priority": 1}
        ]
        
        processed = []
        for s in signals:
            processed.append({
                **s,
                "timestamp": int(time.time()),
                "vector": self.simulate_vectorization(s["text"]),
                "ttl": 7200 # 2 hours
            })
            
        self.volatile_data = processed
        self.last_scout_time = time.time()
        return processed

    def simulate_vectorization(self, text: str) -> List[float]:
        """
        Mock embedding generation using hashing.
        """
        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in h[:16]] # 16-dim mock vector

    def get_sync_payload(self, since_timestamp: int) -> List[Dict[str, Any]]:
        """
        Returns only the data added since the last client sync.
        """
        return [d for d in self.volatile_data if d["timestamp"] > since_timestamp]

knowledge_hub = KnowledgeHub()

if __name__ == "__main__":
    hub = KnowledgeHub()
    news = hub.scout_news()
    print(f"Scouted {len(news)} signals. Sample vector: {news[0]['vector']}")
