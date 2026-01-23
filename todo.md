# Project TODO

## Accomplished:

*   **Initial Codebase Understanding:** Performed a comprehensive analysis of the repository's architecture, identifying key components, their interactions, and core functionalities (Flask web application, AI Sandbox, Secure Tax Agent, Automated Trading Bot).
*   **Market Sentinel Tool Refactoring:**
    *   Created `services/market_sentinel_tools.py` to encapsulate market-related tool functions (`fetch_market_news_tool`, `get_insider_trades_tool`, `prepare_trade_order_tool`).
    *   Updated the `market_sentinel` persona in `services/personas.py` to use `tools_allowed` and reference the new tool function names.
    *   Integrated the new market sentinel tool functions into the `MCP_TOOLKIT` in `services/mcp_tools.py`, making them discoverable and executable by the `KusmusAIEngine`.

## To Accomplish (Next Steps / Potential Enhancements for Market Sentinel):

*   **Enhance `prepare_trade_order_tool`:** Currently, `prepare_trade_order_tool` is a simulated function. Future work could involve integrating it with a real trading API or the `krag_bot`'s trade execution logic for live (or more realistic simulated) order placement.
*   **Add Unit Tests for Market Sentinel Tools:** Develop unit tests for `fetch_market_news_tool`, `get_insider_trades_tool`, and `prepare_trade_order_tool` to ensure their correctness and robustness.
*   **Expand Market Sentinel Functionality:** Explore additional features for the `market_sentinel` tool, such as:
    *   Technical analysis tools (e.g., moving averages, MACD, Bollinger Bands).
    *   Fundamental analysis data retrieval (e.g., P/E ratios, earnings reports).
    *   Real-time stock price fetching.
    *   Integration with risk management parameters.
*   **Refine AI Persona Instructions:** Continuously refine the `market_sentinel` persona's instructions in `services/personas.py` to guide the AI more effectively in using its tools and synthesizing information.
