import os
import time
import logging
import yaml
import pandas as pd # Still needed for data processing
from dotenv import load_dotenv
import signal
import sys
from datetime import datetime, timedelta

# Import modules for LIVE trading
import modules.trade_execution as trade_execution # Use real MT5 for live trading
import modules.notifications as notifications
import modules.database as database
import modules.data_provider as data_provider
import modules.indicators as indicators
import modules.strategy as strategy

# --- Global Variables for Graceful Shutdown ---
shutdown_requested = False

# --- Signal Handler for Graceful Shutdown ---
def signal_handler(signum, frame):
    global shutdown_requested
    logging.info(f"Received signal {signum}. Initiating graceful shutdown...")
    notifications.send_telegram_message("🔴 Bot received shutdown signal. Initiating graceful shutdown.")
    shutdown_requested = True

# --- Main Bot Orchestrator for LIVE Trading ---
def main():
    # 1. Load Environment Variables from .env file
    load_dotenv()

    # 2. Load Configuration from strategy_params.yaml
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'strategy_params.yaml')
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        logging.critical(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.critical(f"Error parsing config file: {e}")
        sys.exit(1)

    # 3. Configure Logging
    log_level_str = config.get('log_level', 'INFO').upper()
    numeric_log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=numeric_log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'bot.log')), # Log to file
                            logging.StreamHandler(sys.stdout) # Log to console
                        ])
    logger = logging.getLogger(__name__) # Get logger instance
    logger.info(f"{config['bot_name']} is starting in LIVE mode...")
    notifications.send_telegram_message(f"🟢 <b>{config['bot_name']}</b> has started in LIVE mode!")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # Kill command

    # 4. Initialize Database Connection
    db_conn = None
    try:
        db_conn = database.connect_db(db_file=os.path.join(os.path.dirname(__file__), 'data', 'bot_state.db'))
        database.create_tables(db_conn)
        # Initialize bot state if it doesn't exist
        if not database.get_bot_state(db_conn):
            initial_equity = trade_execution.get_account_info()['equity'] if trade_execution.get_account_info() else 0.0
            database.update_bot_state(db_conn, last_trading_day=datetime.now().strftime('%Y-%m-%d'), daily_trade_count=0, daily_equity_start=initial_equity, daily_profit_loss=0.0, last_heartbeat_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        logger.info("Live database initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize live database: {e}", exc_info=True)
        notifications.send_telegram_message(f"❌ <b>CRITICAL ERROR:</b> Database initialization failed! {e}")
        sys.exit(1)

    # 5. Initialize MT5 Connection
    mt5_path = config.get('mt5_path')
    if not trade_execution.mt5_connector.initialize(path=mt5_path):
        logger.critical("Failed to initialize MetaTrader5 connection. Exiting.")
        notifications.send_telegram_message("❌ <b>CRITICAL ERROR:</b> MT5 connection failed! Exiting bot.")
        sys.exit(1)
    logger.info("MT5 connection initialized.")
    
    # 6. Instantiate Strategy
    trading_strategy = strategy.TradingStrategy(db_connection=db_conn)
    
    # 7. Live Trading Loop
    logger.info("Starting LIVE TRADING loop...")
    last_heartbeat_time = time.time()
    heartbeat_interval_hours = config.get('heartbeat_interval_hours', 6)

    while not shutdown_requested:
        for symbol in config['trade_symbols']:
            logger.info(f"Processing symbol: {symbol} in LIVE mode.")
            try:
                # Fetch live data (latest bars)
                htf_interval = config['high_timeframe_interval']
                ltf_interval = config['low_timeframe_interval']
                htf_lookback = config['ohlcv_lookback_bars_htf']
                ltf_lookback = config['ohlcv_lookback_bars_ltf']

                htf_data = data_provider.fetch_ohlcv_mt5(symbol, htf_interval, htf_lookback)
                ltf_data = data_provider.fetch_ohlcv_mt5(symbol, ltf_interval, ltf_lookback)
                
                if htf_data.empty or ltf_data.empty:
                    logger.warning(f"Insufficient live data for {symbol}. HTF empty: {htf_data.empty}, LTF empty: {ltf_data.empty}. Skipping cycle for this symbol.")
                    notifications.send_telegram_message(f"⚠️ <b>Data Warning:</b> Insufficient live OHLCV data for {symbol}. Skipping cycle.")
                    continue

                # Calculate Indicators
                htf_data = indicators.calculate_all_indicators(htf_data, config)
                ltf_data = indicators.calculate_all_indicators(ltf_data, config)

                # Ensure indicators are not NaN for the last few bars
                if htf_data.iloc[-1].isnull().any() or ltf_data.iloc[-1].isnull().any():
                    logger.warning(f"NaN values found in latest indicators for {symbol}. May indicate insufficient lookback data or calculation error. Skipping decision for this symbol.")
                    continue

                # Manage Existing Positions
                current_bid, current_ask = trade_execution.get_current_price(symbol)
                if current_bid is None or current_ask is None:
                    logger.warning(f"Could not get current live price for {symbol} for position management. Skipping.")
                else:
                    current_price = (current_bid + current_ask) / 2 # Use mid-price
                    trading_strategy.manage_positions(symbol, current_price)
                
                # Check and Execute New Trades
                is_recovery_trade_attempt = False # This logic would be more complex and depend on your strategy's state
                trading_strategy.check_and_execute_trades(symbol, ltf_data, htf_data, is_recovery_trade_attempt)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}", exc_info=True)
                notifications.send_telegram_message(f"❌ <b>Error processing {symbol}:</b> {e}")

        # Check for heartbeat in live mode
        if time.time() - last_heartbeat_time >= heartbeat_interval_hours * 3600:
            account_info = trade_execution.get_account_info()
            equity_info = f"Equity: {account_info['equity']:.2f} {account_info['currency']}" if account_info else "N/A"
            notifications.send_telegram_message(f"❤️ {config['bot_name']} is alive! {equity_info}")
            last_heartbeat_time = time.time()

        # Sleep for the configured interval
        if not shutdown_requested:
            logger.info(f"Live cycle complete. Sleeping for {config['loop_interval_seconds']} seconds...")
            time.sleep(config['loop_interval_seconds'])

    # --- Graceful Shutdown Sequence ---
    logger.info("Bot received shutdown signal. Initiating graceful shutdown.")
    notifications.send_telegram_message("🔴 Bot shutting down gracefully. Closing MT5 connection and database.")

    # Shutdown MT5 connection
    trade_execution.mt5_connector.shutdown()
    logger.info("MetaTrader5 connection shut down.")

    # Ensure DB is updated and closed
    if db_conn:
        database.close_db(db_conn)
        logger.info("Database connection closed.")
    
    notifications.send_telegram_message(f"⚫ {config['bot_name']} has shut down.")
    logger.info("Bot shutdown complete.")
    sys.exit(0)

if __name__ == "__main__":
    main()