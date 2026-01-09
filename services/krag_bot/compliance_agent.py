import logging
import json

logger = logging.getLogger(__name__)

class ComplianceAgent:
    """
    The Guardian: Enforces risk policies and prevents 'hallucinated' or reckless trades.
    Functions as a final firewall before execution.
    """
    def __init__(self, config):
        self.config = config
        self.max_daily_loss_percent = config.get('max_daily_loss_percent', 5.0)
        self.max_risk_per_trade_percent = config.get('risk_per_trade_percent', 1.0)
        self.blacklisted_symbols = config.get('blacklisted_symbols', [])
        self.trading_hours = config.get('allowed_trading_hours', "00:00-23:59") 

    def review_trade(self, trade_proposal: dict, account_info: dict) -> dict:
        """
        Reviews a proposed trade against hard rules.
        
        Args:
            trade_proposal: {symbol, action, volume, sl, tp, reason, ai_confidence}
            account_info: {equity, balance, daily_loss}
            
        Returns:
            { "approved": bool, "rejection_reason": str }
        """
        symbol = trade_proposal.get('symbol')
        action = trade_proposal.get('action')
        volume = trade_proposal.get('volume')
        
        # 1. Blacklist Check
        if symbol in self.blacklisted_symbols:
            return self._reject(f"Symbol {symbol} is blacklisted.")

        # 2. Daily Loss Limit (Hard Stop)
        daily_loss_percent = (account_info.get('daily_loss', 0) / account_info.get('equity_start', 1)) * 100
        if daily_loss_percent >= self.max_daily_loss_percent:
            return self._reject(f"Daily loss limit reached ({daily_loss_percent:.2f}% >= {self.max_daily_loss_percent}%).")

        # 3. AI Confidence Check (Hallucination Prevention)
        # If the trade claims to be AI-backed, it must meet the threshold
        if trade_proposal.get('ai_decision'):
             confidence = trade_proposal.get('ai_confidence', 0)
             required_conf = self.config.get('ai_confidence_threshold', 70)
             if confidence < required_conf:
                 return self._reject(f"AI Confidence {confidence}% is too low (Req: {required_conf}%). Guardian blocks uncertain trades.")

        # 4. Impact/News Safety (Integration with Oracle)
        # If Oracle said "Sentiment -10", we should not buy.
        # (This logic might be passed in trade_proposal or checked here if we link agents)
        sentiment_score = trade_proposal.get('market_sentiment_score', 0)
        if action == 'BUY' and sentiment_score < -5:
            return self._reject(f"Guardian blocks BUY due to extremely negative market sentiment ({sentiment_score}).")
        if action == 'SELL' and sentiment_score > 5:
            return self._reject(f"Guardian blocks SELL due to extremely positive market sentiment ({sentiment_score}).")

        return {"approved": True, "rejection_reason": None}

    def _reject(self, reason):
        logger.warning(f"🛡️ GUARDIAN BLOCKED TRADE: {reason}")
        return {"approved": False, "rejection_reason": reason}
