import requests
import os
import time
import logging
import json # For better JSON handling/pretty printing
import pandas as pd
from datetime import datetime, timedelta

# Configure logging for this module
logger = logging.getLogger(__name__)

def load_ohlcv_from_csv(file_path, interval):
    """
    Loads OHLCV (Open, High, Low, Close, Volume) data from a CSV file.
    Assumes the CSV has 'time', 'datetime', or 'timestamp' as its time column,
    along with 'open', 'high', 'low', 'close', 'volume' columns.
    The time column should be parseable as datetime.
    
    Args:
        file_path (str): The full path to the CSV file.
        interval (str): The interval of the data (e.g., '1min', '5min', '1h').
                        Used primarily for logging and context, not for resampling here.

    Returns:
        pd.DataFrame: A DataFrame with OHLCV data, indexed by datetime,
                      or an empty DataFrame if the file is not found or parsing fails.
    """
    if not os.path.exists(file_path):
        logger.error(f"CSV file not found: {file_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(file_path)
        
        # Standardize column names to lowercase
        df.columns = [col.lower() for col in df.columns]

        # Identify the time column and rename it to 'time' for consistency
        time_col_found = None
        if 'time' in df.columns:
            time_col_found = 'time'
        elif 'datetime' in df.columns: # Prioritize 'datetime' over 'timestamp'
            time_col_found = 'datetime'
            df.rename(columns={'datetime': 'time'}, inplace=True)
        elif 'timestamp' in df.columns:
            time_col_found = 'timestamp'
            df.rename(columns={'timestamp': 'time'}, inplace=True)
        
        if time_col_found is None:
            logger.error("No suitable time column found in CSV. Expected 'time', 'datetime', or 'timestamp'.")
            return pd.DataFrame()

        # Ensure required OHLCV columns exist after standardization and time column handling
        required_ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_ohlcv_columns):
            logger.error(f"Missing required OHLCV columns in CSV: {required_ohlcv_columns}. Found: {df.columns.tolist()}")
            return pd.DataFrame()

        # Convert 'time' column to datetime and set as index
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')
        
        # Sort by index (time) to ensure chronological order
        df = df.sort_index()

        logger.info(f"Successfully loaded {len(df)} {interval} bars from {file_path}")
        return df[required_ohlcv_columns] # Return only the OHLCV columns
    except Exception as e:
        logger.error(f"Error loading OHLCV data from CSV {file_path}: {e}", exc_info=True)
        return pd.DataFrame()


# Load API keys from environment variables
TOKENMETRICS_API_KEY = os.getenv('TOKENMETRICS_API_KEY')
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# Base URLs for APIs
TOKENMETRICS_BASE_URL = "https://api.tokenmetrics.com/v1"
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query?"

# --- Helper for API Rate Limiting ---
# This is a simple example. For production, consider a more sophisticated
# rate limiting library or a per-API-key token bucket algorithm.
last_tokenmetrics_request_time = 0
last_alphavantage_request_time = 0
TOKENMETRICS_RATE_LIMIT_SECONDS = 2 # Example: 1 request every 2 seconds
ALPHA_VANTAGE_RATE_LIMIT_SECONDS = 15 # Example: 1 request every 15 seconds (free tier is 5 calls/min)

def _wait_for_rate_limit(api_name):
    """Waits to respect API rate limits."""
    global last_tokenmetrics_request_time, last_alphavantage_request_time
    current_time = time.time()

    if api_name == "tokenmetrics":
        elapsed = current_time - last_tokenmetrics_request_time
        if elapsed < TOKENMETRICS_RATE_LIMIT_SECONDS:
            wait_time = TOKENMETRICS_RATE_LIMIT_SECONDS - elapsed
            logger.warning(f"Token Metrics rate limit approaching. Waiting for {wait_time:.2f} seconds.")
            time.sleep(wait_time)
        last_tokenmetrics_request_time = time.time()
    elif api_name == "alphavantage":
        elapsed = current_time - last_alphavantage_request_time
        if elapsed < ALPHA_VANTAGE_RATE_LIMIT_SECONDS:
            wait_time = ALPHA_VANTAGE_RATE_LIMIT_SECONDS - elapsed
            logger.warning(f"Alpha Vantage rate limit approaching. Waiting for {wait_time:.2f} seconds.")
            time.sleep(wait_time)
        last_alphavantage_request_time = time.time()

# --- Token Metrics API Integration ---
def fetch_token_metrics_ohlcv(symbol, interval="1h", lookback_hours=240):
    """
    Fetches OHLCV data for a given symbol and interval from Token Metrics.
    Uses the `/ohlc` or similar endpoint.
    Token Metrics API documentation for OHLCV: [refer to Token Metrics API docs for exact endpoint and parameters]
    """
    if not TOKENMETRICS_API_KEY:
        logger.error("TOKENMETRICS_API_KEY not set. Cannot fetch Token Metrics OHLCV.")
        return None

    _wait_for_rate_limit("tokenmetrics")

    # This is a conceptual endpoint. You MUST verify the exact endpoint and parameters
    # from the official Token Metrics API documentation.
    # Example for OHLCV might be like: /api/v1/ohlc
    # Parameters might include symbol, interval, start_time, end_time, limit.
    endpoint = f"{TOKENMETRICS_BASE_URL}/ohlc" # Example endpoint
    params = {
        "symbol": symbol,
        "interval": interval, # e.g., "1m", "5m", "1h", "1d"
        "limit": lookback_hours # Number of bars (adjust based on interval for desired lookback duration)
        # You might need 'from' and 'to' timestamps for precise lookback
    }
    headers = {
        "Authorization": f"Bearer {TOKENMETRICS_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(endpoint, headers=headers, params=params, timeout=10) # Set a timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if not data or not isinstance(data, list): # Check if data is empty or not a list of candles
            logger.warning(f"No OHLCV data or unexpected format for {symbol} from Token Metrics: {data}")
            return None

        # Convert to Pandas DataFrame for easier processing
        # Assuming data is a list of dicts with keys like 'timestamp', 'open', 'high', 'low', 'close', 'volume'
        df = pd.DataFrame(data)
        # Assuming 'timestamp' is in milliseconds or seconds and needs conversion
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') # Adjust unit if needed (e.g., 's')
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True) # Ensure chronological order

        logger.info(f"Successfully fetched {len(df)} OHLCV bars for {symbol} from Token Metrics.")
        return df
    except requests.exceptions.Timeout:
        logger.error(f"Request to Token Metrics timed out for {symbol}.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching OHLCV from Token Metrics for {symbol}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from Token Metrics for {symbol}: {e}. Response: {response.text[:200]}...")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Token Metrics OHLCV for {symbol}: {e}")
        return None

def fetch_token_metrics_grades_signals(symbol):
    """
    Fetches grades and signals for a given symbol from Token Metrics.
    Uses the `/grades` or `/signals` endpoints.
    Token Metrics API documentation for Grades/Signals: [refer to Token Metrics API docs for exact endpoints]
    """
    if not TOKENMETRICS_API_KEY:
        logger.error("TOKENMETRICS_API_KEY not set. Cannot fetch Token Metrics grades/signals.")
        return None

    _wait_for_rate_limit("tokenmetrics")

    # Example endpoint. You MUST verify the exact endpoint and parameters.
    endpoint_grades = f"{TOKENMETRICS_BASE_URL}/grades"
    endpoint_signals = f"{TOKENMETRICS_BASE_URL}/signals"

    params = {"symbol": symbol}
    headers = {
        "Authorization": f"Bearer {TOKENMETRICS_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # Fetch Grades
        grades_response = requests.get(endpoint_grades, headers=headers, params=params, timeout=10)
        grades_response.raise_for_status()
        grades_data = grades_response.json()

        # Fetch Signals
        signals_response = requests.get(endpoint_signals, headers=headers, params=params, timeout=10)
        signals_response.raise_for_status()
        signals_data = signals_response.json()

        logger.info(f"Successfully fetched Token Metrics grades and signals for {symbol}.")
        return {"grades": grades_data, "signals": signals_data}
    except requests.exceptions.Timeout:
        logger.error(f"Request to Token Metrics timed out for grades/signals for {symbol}.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching grades/signals from Token Metrics for {symbol}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from Token Metrics for {symbol} (grades/signals): {e}.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Token Metrics grades/signals for {symbol}: {e}")
        return None

# --- Alpha Vantage API Integration ---
def fetch_alpha_vantage_news_sentiment(symbol, limit=50):
    """
    Fetches news and sentiment data for a given stock symbol from Alpha Vantage.
    This typically uses the NEWS_SENTIMENT function.
    Refer to Alpha Vantage documentation: https://www.alphavantage.co/documentation/#news-sentiment
    """
    if not ALPHA_VANTAGE_API_KEY:
        logger.error("ALPHA_VANTAGE_API_KEY not set. Cannot fetch Alpha Vantage news.")
        return None

    _wait_for_rate_limit("alphavantage")

    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "limit": limit # Number of news articles to retrieve
    }

    try:
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or 'feed' not in data:
            logger.warning(f"No news feed or unexpected format for {symbol} from Alpha Vantage: {data}")
            return None

        news_df = pd.DataFrame(data['feed'])
        # Convert time_published to datetime and set as index
        if 'time_published' in news_df.columns:
            news_df['time_published'] = pd.to_datetime(news_df['time_published'])
            news_df.set_index('time_published', inplace=True)
            news_df.sort_index(inplace=True, ascending=False) # Sort by most recent first

        logger.info(f"Successfully fetched {len(news_df)} news articles for {symbol} from Alpha Vantage.")
        return news_df
    except requests.exceptions.Timeout:
        logger.error(f"Request to Alpha Vantage timed out for {symbol}.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news from Alpha Vantage for {symbol}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from Alpha Vantage for {symbol}: {e}. Response: {response.text[:200]}...")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Alpha Vantage news for {symbol}: {e}")
        return None


# --- Live Price (Tick Data) - Consider MT5 as primary for live ticks if trading on it ---
# While Token Metrics provides OHLCV, for real-time tick-level price data relevant to MT5 execution,
# it's often more reliable to get it directly from the MT5 terminal via its API.
# This function is a placeholder for that, which would be implemented in trade_execution.py or here.
def fetch_live_price_from_mt5(symbol):
    """
    Conceptual function to fetch live tick price directly from MT5.
    This would typically use the MetaTrader5 library (imported in trade_execution.py).
    """
    # This function would be implemented using MetaTrader5.symbol_info_tick() or similar.
    # For now, it's a placeholder to highlight the source of live price.
    logger.debug(f"Fetching live price for {symbol} from MT5 (conceptual).")
    # Example:
    # import MetaTrader5 as mt5
    # if not mt5.initialize():
    #     logger.error("Failed to initialize MT5 in data_provider for live price.")
    #     return None
    # tick_info = mt5.symbol_info_tick(symbol)
    # if tick_info:
    #     return {'bid': tick_info.bid, 'ask': tick_info.ask, 'last': tick_info.last}
    # return None
    pass

