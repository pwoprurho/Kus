"""Simulated MCP tools used by the sandbox and agent demos.

This module intentionally contains lightweight, deterministic-ish
simulators for demo and testing. Keep implementations idempotent and
free of side-effects beyond returning structured dicts.
"""
import datetime
import random
import time
from typing import Any, Dict
from typing import Union

try:
    import yfinance as yf
    import pandas as pd
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    # import calendar helper if present
    from services.calendar_tool import create_calendar_event
    CALENDAR_AVAILABLE = True
except Exception:
    CALENDAR_AVAILABLE = False

# Import the new market sentinel tools
from services.market_sentinel_tools import fetch_market_news_tool, get_insider_trades_tool, prepare_trade_order_tool


def get_server_health(server_id: str) -> Dict[str, Any]:
    """Return a mock health snapshot for a server."""
    statuses = ["HEALTHY", "DEGRADED", "CRITICAL", "MAINTENANCE"]
    return {
        "server_id": server_id,
        "status": random.choice(statuses),
        "cpu_load": f"{random.randint(5, 98)}%",
        "last_ping": datetime.datetime.utcnow().isoformat()
    }


def get_oran_metrics(node_id: str) -> Dict[str, Any]:
    """Return mock O-RAN telemetry for a node."""
    latency = random.randint(10, 150)
    return {
        "node_id": node_id,
        "status": "OPTIMAL" if latency < 100 else "DEGRADED",
        "telemetry": {"latency_ms": latency}
    }


def run_napalm_audit(node_id: str) -> Dict[str, Any]:
    """Simulated network audit run for remediation scenarios."""
    time.sleep(0.2)
    return {
        "tool": "NAPALM_DRIVER_V2",
        "target": node_id,
        "status": "COMPROMISED",
        "diagnostics": {
            "interface_opt0": "DOWN (Signal Loss)",
            "action": "Traffic Rerouted to Backup Gateway",
            "result": "Connectivity Restored (Latency: 142ms)"
        }
    }


def trigger_incident_protocol(severity: str, target_id: str, notes: str) -> Dict[str, Any]:
    """Simulate creating an incident ticket and applying a blocking rule."""
    return {
        "status": "SUCCESS",
        "ticket_id": f"INC-{random.randint(10000, 99999)}",
        "action": f"SIEM Rule Created. Target {target_id} blocked at firewall.",
        "severity": severity,
        "notes": notes,
    }


def scan_siem_logs(query_filter: str) -> Dict[str, Any]:
    """Return a shallow response indicating a search was executed."""
    return {"status": "Complete", "matches": f"Simulated results for: {query_filter}"}


def get_attacker_metadata(ip_address: str) -> Dict[str, Any]:
    """Return enriched metadata for a suspicious IP (mock)."""
    # Deep-trace forensic enrichment
    mock_data = {
        "192.168.45.2": {
            "origin": "Eastern Europe",
            "type": "Known Botnet Node",
            "threat_level": "High",
            "first_seen": "2025-12-01T14:22:00Z",
            "last_activity": "2026-01-03T23:59:00Z",
            "attack_methods": ["Brute Force", "SQL Injection"],
            "related_cases": ["INC-10023", "INC-10456"]
        },
        "10.0.0.15": {
            "origin": "Internal VPN",
            "type": "Unauthorized Lateral Movement",
            "threat_level": "Critical",
            "first_seen": "2025-12-28T09:00:00Z",
            "last_activity": "2026-01-04T01:00:00Z",
            "attack_methods": ["Credential Stuffing"],
            "related_cases": ["INC-10999"]
        }
    }
    result = mock_data.get(ip_address, {
        "origin": "Unknown Proxy",
        "type": "Suspicious Probe",
        "threat_level": "Medium",
        "first_seen": None,
        "last_activity": None,
        "attack_methods": [],
        "related_cases": []
    })
    # Tamper-proof log stub (to be encrypted in security.py)
    try:
        from core.security import tamper_proof_log
        tamper_proof_log({"event": "attacker_metadata_lookup", "ip": ip_address, "result": result})
    except Exception:
        pass
    return {
        "ip": ip_address,
        "metadata": result,
        "action_recommendation": "Initiate Quarantine" if result["threat_level"] in ["Critical", "High"] else "Monitor"
    }


def quarantine_compute_node(node_id: str) -> Dict[str, Any]:
    """Simulate isolating a compute node from the network fabric."""
    time.sleep(0.3)
    # Tamper-proof log stub (to be encrypted in security.py)
    try:
        from core.security import tamper_proof_log
        tamper_proof_log({"event": "quarantine_node", "node_id": node_id, "ts": datetime.datetime.utcnow().isoformat()})
    except Exception:
        pass
    return {
        "status": "SUCCESS",
        "action": f"Node {node_id} isolated from O-RAN Fabric.",
        "firewall_rule": "DENY ALL INBOUND/OUTBOUND",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


def get_robot_vision_feed(camera_id: str) -> Dict[str, Any]:
    """Return a simulated visual-analysis result for a camera feed."""
    time.sleep(0.25)
    scenarios = [
        {
            "status": "SECURE",
            "objects": ["Server Rack", "Cooling Unit"],
            "anomaly_score": 0.05,
            "frame_hash": "a1b2c3d4"
        },
        {
            "status": "CRITICAL",
            "objects": ["Open Chassis", "Unverified USB Device", "Human Hand"],
            "anomaly_score": 0.98,
            "frame_hash": "e5f6g7h8"
        }
    ]
    result = random.choice(scenarios)
    # Tamper-proof log stub (to be encrypted in security.py)
    try:
        from core.security import tamper_proof_log
        tamper_proof_log({"event": "robot_vision_feed", "camera_id": camera_id, "result": result})
    except Exception:
        pass
    return {
        "camera_id": camera_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "visual_analysis": result,
        "action_required": "Physical Intervention" if result["anomaly_score"] > 0.8 else "None"
    }


def execute_arc_payment(amount_usdc: float, recipient: str) -> Dict[str, Any]:
    """
    Simulate a USDC payment on Arc L1 using Circle's x402 standard.
    Returns a transaction dict with status, x402 header, tx hash, and timestamp.
    """
    import hashlib
    import datetime
    # Simulate transaction hash
    tx_input = f"{amount_usdc}:{recipient}:{random.random()}:{datetime.datetime.utcnow().isoformat()}"
    tx_hash = hashlib.sha256(tx_input.encode()).hexdigest()
    # Simulate status
    status = random.choice(["PENDING", "CONFIRMED", "FAILED"])
    x402_header = f"Circle-USDC amount={amount_usdc}; address={recipient}; x402=arc-l1"
    return {
        "status": status,
        "x402_header": x402_header,
        "tx_hash": tx_hash,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "message": (
            "Transaction confirmed and audit report released."
            if status == "CONFIRMED" else
            "Transaction pending. Awaiting confirmation."
            if status == "PENDING" else
            "Transaction failed. Please retry."
        )
    }


def perform_self_heal(target_system: str) -> Dict[str, Any]:
    """Execute a short, deterministic self-heal simulation and return actions."""
    actions = []
    # Step 1: Restart critical services
    actions.append({
        "action": "restart_services",
        "detail": f"Restarted {target_system}-core services",
        "status": "SUCCESS"
    })
    time.sleep(0.15)

    # Step 2: Reconcile firewall and routing rules
    actions.append({
        "action": "reconcile_firewall",
        "detail": "Applied hardened firewall rules; removed suspicious entries",
        "status": "SUCCESS"
    })
    time.sleep(0.12)

    # Step 3: Post-heal verification
    verification = random.choice(["PASS", "PASS", "WARN"])
    actions.append({
        "action": "post_heal_verification",
        "detail": f"Verification result: {verification}",
        "status": "PASS" if verification == "PASS" else "WARN"
    })

    return {
        "status": "COMPLETED" if verification == "PASS" else "COMPLETED_WITH_WARNINGS",
        "actions": actions,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }



def get_ticker_insider_trades(ticker: str) -> Dict[str, Any]:
    """
    Simulates fetching recent SEC Form 4 (Insider Trade) and 13D (Beneficial Ownership) filings.
    Tries LIVE data from yfinance first.
    """
    ticker = ticker.upper()
    
    # --- LIVE DATA PATH ---
    if YFINANCE_AVAILABLE:
        try:
            t = yf.Ticker(ticker)
            # Try getting insider transactions
            insider = t.insider_transactions
            if insider is not None and not insider.empty:
                recent_trades = []
                # Take top 8 recent
                for i in range(min(8, len(insider))):
                    row = insider.iloc[i]
                    # Helper to get value safely
                    def get_val(r, keys, default):
                        for k in keys:
                            if k in r and pd.notna(r[k]): return r[k]
                        return default
                    
                    person = get_val(row, ['Reporter', 'Name', 'Insider'], 'Unknown')
                    date_val = get_val(row, ['Start Date', 'Date'], 'Unknown')
                    
                    # Format date cleanly (YYYY-MM-DD)
                    date_str = str(date_val)
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime('%Y-%m-%d')
                    elif ' ' in date_str:
                        date_str = date_str.split(' ')[0]

                    shares = get_val(row, ['Shares', 'Quantity'], 0)
                    value = get_val(row, ['Value'], 0)
                    text = get_val(row, ['Text', 'Transaction'], '') # e.g. "Sale at price..."
                    
                    recent_trades.append({
                        "filing_type": "SEC Form 4 (Live)",
                        "reporting_person": str(person),
                        "transaction_date": date_str,
                        "description": str(text),
                        "shares": int(shares) if isinstance(shares, (int, float)) else 0,
                        "value": float(value) if isinstance(value, (int, float)) else 0.0,
                    })

                return {
                    "ticker": ticker,
                    "source": "LIVE (yfinance/SEC)",
                    "signal": "ANALYSIS_REQUIRED",
                    "recent_filings": recent_trades,
                    "analysis": f"Retrieved {len(recent_trades)} live insider records."
                }
        except Exception as e:
            print(f"Warning: Live insider fetch failed for {ticker}: {e}")

    # --- NO MOCK FALLBACK --- 
    # User requested no simulation. If live data fails, return empty.
    print(f"No live insider data found for {ticker}")
    return {
        "ticker": ticker,
        "source": "LIVE_ONLY",
        "signal": "NO_DATA",
        "recent_filings": [],
        "analysis": "No live insider filings available."
    }


def fetch_market_news(ticker: str) -> Dict[str, Any]:
    """
    Retrieves live market news via yfinance (if available), else simulates.
    """
    ticker = ticker.upper()

    # --- LIVE DATA PATH ---
    if YFINANCE_AVAILABLE:
        try:
            t = yf.Ticker(ticker)
            raw_news = t.news
            if raw_news:
                articles = []
                for item in raw_news[:5]:
                    # yfinance news fields: 'title', 'publisher', 'link', 'providerPublishTime'
                    ts = item.get('providerPublishTime', int(time.time()))
                    pub_date = datetime.datetime.utcfromtimestamp(ts).isoformat()
                    
                    articles.append({
                        "source": item.get('publisher', 'Unknown'),
                        "tier": 1, 
                        "text": item.get('title', ''),
                        "link": item.get('link', ''),
                        "sentiment": 0.0, # Agent will infer sentiment
                        "published_at": pub_date
                    })

                return {
                    "ticker": ticker,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "articles": articles,
                    "unusual_volume": False,
                    "data_source": "LIVE (yfinance)"
                }
        except Exception as e:
            print(f"Warning: Live news fetch failed for {ticker}: {e}")

    # --- MOCK FALLBACK ---
    random.seed(ticker + "news")
    
    headlines = [
        {"source": "Bloomberg Terminal", "tier": 1, "text": f"{ticker} in advanced talks for strategic acquisition, sources say.", "sentiment": 0.8},
        {"source": "Reuters", "tier": 1, "text": f"Regulatory approval likely for {ticker}'s new product line.", "sentiment": 0.6},
        {"source": "Seeking Alpha", "tier": 2, "text": f"Why {ticker} might be overvalued at these levels.", "sentiment": -0.4},
        {"source": "Twitter/X", "tier": 3, "text": f"${ticker} to the moon! 🚀 #stocks", "sentiment": 0.9},
        {"source": "Industry Dive", "tier": 2, "text": f"Supply chain constraints could hit {ticker} Q4 margins.", "sentiment": -0.5}
    ]
    
    # Pick a random subset
    selected_news = random.sample(headlines, 3)
    
    return {
        "ticker": ticker,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "articles": selected_news,
        "unusual_volume": random.choice([True, False]),
        "data_source": "SIMULATED (Backup)"
    }


def get_global_market_trend() -> Dict[str, Any]:
    """
    Determines if the overall market (S&P 500) is Bullish (Up) or Bearish (Down) today.
    Returns a score from -100 (Deep Bear) to +100 (Strong Bull).
    """
    # Default State
    trend_score = 10 
    sp500_change = 0.0

    if YFINANCE_AVAILABLE:
        try:
            # Check S&P 500 (SPY) and Nasdaq (QQQ)
            tickers = yf.Tickers("SPY QQQ")
            spy_hist = tickers.tickers["SPY"].history(period="2d")
            
            if len(spy_hist) >= 1:
                # Calculate daily change percent
                close_price = spy_hist['Close'].iloc[-1]
                open_price = spy_hist['Open'].iloc[-1]
                # Or comparison with previous close if available
                if len(spy_hist) >= 2:
                    prev_close = spy_hist['Close'].iloc[-2]
                    change_pct = ((close_price - prev_close) / prev_close) * 100
                    sp500_change = change_pct
                else:
                    change_pct = ((close_price - open_price) / open_price) * 100
                    sp500_change = change_pct

                # Scale -2% to +2% range to -100 to 100 score
                trend_score = int(max(min(change_pct * 50, 100), -100))
        except Exception as e:
            print(f"Market Trend Error: {e}")
            pass
            
    return {
        "score": trend_score,
        "sp500_change": round(sp500_change, 2),
        "status": "BULLISH" if trend_score > 0 else "BEARISH",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

def get_ticker_news(ticker: str) -> list[Dict[str, Any]]:
    """Fetch the latest news for a ticker using yfinance."""
    if not YFINANCE_AVAILABLE:
        return []
    try:
        t = yf.Ticker(ticker)
        news = t.news
        results = []
        if news:
            for n in news:
                results.append({
                    "title": n.get("title", "No Title"),
                    "publisher": n.get("publisher", "Unknown"),
                    "link": n.get("link", "#"),
                    "providerPublishTime": n.get("providerPublishTime", 0),
                    "type": n.get("type", "STORY")
                })
        return results
    except Exception as e:
        print(f"News fetch error for {ticker}: {e}")
        return []

def get_ticker_history(ticker: str, period: str = "3mo", interval: str = "1d") -> Dict[str, Any]:
    """Fetch historical OHLC data for a ticker using yfinance."""
    if not YFINANCE_AVAILABLE:
        # Mock Data Generator for when offline
        mock_candles = []
        base_price = 150.0
        for i in range(30):
            change = random.uniform(-5, 5)
            open_p = base_price + change
            close_p = open_p + random.uniform(-2, 2)
            high_p = max(open_p, close_p) + random.uniform(0, 2)
            low_p = min(open_p, close_p) - random.uniform(0, 2)
            base_price = close_p
            mock_candles.append({
                "date": (datetime.datetime.now() - datetime.timedelta(days=30-i)).strftime("%Y-%m-%d"),
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": int(random.uniform(1000000, 5000000))
            })
        return {"ticker": ticker, "candles": mock_candles}

    try:
        t = yf.Ticker(ticker)
        # Fetch history
        hist = t.history(period=period, interval=interval)
        
        if hist.empty:
            raise ValueError(f"No data found for {ticker}")

        # Reset index to get Date as column
        hist.reset_index(inplace=True)
        
        # Handle 'Date' (Daily) vs 'Datetime' (Intraday) column naming
        date_col = 'Date'
        if 'Datetime' in hist.columns:
            date_col = 'Datetime'
        elif 'Date' not in hist.columns:
            # Fallback if neither found (unlikely with yfinance)
            date_col = hist.columns[0] 

        candles = []
        for _, row in hist.iterrows():
            # Format date which might be Timestamp
            dt_obj = row[date_col]
            # Use ISO-like format for intraday to preserve time
            if date_col == 'Datetime':
                date_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = dt_obj.strftime("%Y-%m-%d")
                
            candles.append({
                "date": date_str,
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })
            
        return {"ticker": ticker, "candles": candles}
        
    except Exception as e:
        print(f"Error fetching history for {ticker}: {e}")
        # Retrying once with a shorter period if the first attempt failed (sometimes futures fail on long lookbacks)
        if period == "6mo":
            try:
                print(f"Retrying {ticker} with period='1mo'...")
                hist = t.history(period="1mo", interval=interval)
                if not hist.empty:
                    hist.reset_index(inplace=True)
                    candles = []
                    for _, row in hist.iterrows():
                        date_str = row['Date'].strftime("%Y-%m-%d")
                        candles.append({
                            "date": date_str,
                            "open": round(row['Open'], 2),
                            "high": round(row['High'], 2),
                            "low": round(row['Low'], 2),
                            "close": round(row['Close'], 2),
                            "volume": int(row['Volume'])
                        })
                    return {"ticker": ticker, "candles": candles}
            except:
                pass
                
        return {"error": str(e), "message": "Live data unavailable. Check ticker symbol."}


def prepare_trade_order(ticker: str, action: str, quantity: int, conviction_score: int) -> Dict[str, Any]:
    """
    Staging function for Human-in-the-Loop execution. Does not execute, but locks the price.
    """
    if conviction_score < 70:
        return {
            "status": "REJECTED",
            "reason": f"Conviction Score ({conviction_score}) is below the Sovereign threshold (70). Execution denied."
        }
        
    estimated_price = round(random.uniform(100, 200), 2)
    return {
        "status": "STAGED",
        "ticket_id": f"ORD-{random.randint(1000,9999)}-{ticker}",
        "action": action.upper(),
        "ticker": ticker.upper(),
        "quantity": quantity,
        "limit_price": estimated_price,
        "total_value": round(estimated_price * quantity, 2),
        "conviction": conviction_score,
        "expiry": "5 minutes",
        "message": "Order staged in Execution Vault. Waiting for Chairman's signature."
    }


# Public registry of tools available for controlled invocation in the sandbox
MCP_TOOLKIT = {
    "get_insider_trades": get_ticker_insider_trades,
    "fetch_market_news": fetch_market_news,
    "prepare_trade_order": prepare_trade_order,
    "get_server_health": get_server_health,
    "get_oran_metrics": get_oran_metrics,
    "run_napalm_audit": run_napalm_audit,
    "scan_siem_logs": scan_siem_logs,
    "trigger_incident_protocol": trigger_incident_protocol,
    "get_attacker_metadata": get_attacker_metadata,
    "quarantine_compute_node": quarantine_compute_node,
    "get_robot_vision_feed": get_robot_vision_feed,
    "execute_arc_payment": execute_arc_payment,
    "perform_self_heal": perform_self_heal,
    "create_calendar_event": (create_calendar_event if CALENDAR_AVAILABLE else None),
}
