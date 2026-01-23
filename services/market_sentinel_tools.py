import json

def fetch_market_news_tool(ticker: str) -> str:
    """
    Fetches the latest market news for a given stock ticker.
    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL").
    Returns:
        str: A JSON string of the latest news articles.
    """
    from services.mcp_tools import get_ticker_news
    news = get_ticker_news(ticker)
    return json.dumps(news)

def get_insider_trades_tool(ticker: str) -> str:
    """
    Retrieves the latest insider trading activity for a given stock ticker.
    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL").
    Returns:
        str: A JSON string of insider trades.
    """
    from services.mcp_tools import get_ticker_insider_trades
    trades = get_ticker_insider_trades(ticker)
    return json.dumps(trades)

def prepare_trade_order_tool(ticker: str, action: str, quantity: int) -> str:
    """
    Prepares a simulated trade order based on the given parameters.
    This is a placeholder for actual trade execution.
    Args:
        ticker (str): The stock ticker symbol.
        action (str): "BUY" or "SELL".
        quantity (int): The number of shares/units.
    Returns:
        str: A JSON string confirming the simulated order.
    """
    # In a real system, this would interact with a trading API
    # For now, it's a simulated response.
    simulated_order = {
        "status": "simulated_success",
        "ticker": ticker,
        "action": action,
        "quantity": quantity,
        "timestamp": "now" # In a real system, use datetime.utcnow().isoformat()
    }
    return json.dumps(simulated_order)
