try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
    print("Warning: MetaTrader5 module not found. Trading functions will be disabled (Linux/Cloud Environment detected).")

import logging
import time
from datetime import datetime

# Configure logging for this module
logger = logging.getLogger(__name__)

class MT5Connection:
    """
    Manages the MetaTrader5 connection lifecycle.
    Uses a singleton-like pattern to ensure only one connection.
    """
    _instance = None
    _is_initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5Connection, cls).__new__(cls)
        return cls._instance

    def initialize(self, path=None, portable_path=None, timeout=10):
        """Initializes the MT5 connection."""
        if mt5 is None:
            logger.warning("MT5 module missing. Skipping initialization (Simulation Mode).")
            return False

        if self._is_initialized:
            logger.info("MT5 already initialized.")
            return True

        logger.info("Attempting to initialize MetaTrader5...")
        try:
            # Construct keyed arguments, omitting None values to avoid "Invalid argument" errors
            init_args = {}
            if path:
                init_args['path'] = path
            if portable_path:
                init_args['portable_path'] = portable_path
            if timeout:
                init_args['timeout'] = timeout
            
            if mt5.initialize(**init_args):
                self._is_initialized = True
                terminal_info = mt5.terminal_info()
                logger.info(f"MetaTrader5 initialized successfully. Terminal: {terminal_info.name}, Account: {mt5.account_info().login}")
                return True
            else:
                logger.error(f"Failed to initialize MetaTrader5. Error code: {mt5.last_error()}")
                return False
        except Exception as e:
            logger.error(f"Exception during MT5 initialization: {e}")
            return False

    def shutdown(self):
        """Shuts down the MT5 connection."""
        if mt5 is None: return

        if self._is_initialized:
            logger.info("Shutting down MetaTrader5 connection...")
            mt5.shutdown()
            self._is_initialized = False
            logger.info("MetaTrader5 connection shut down.")
        else:
            logger.info("MT5 not initialized, no need to shut down.")

    def is_connected(self):
        """Checks if MT5 is currently connected."""
        return self._is_initialized and mt5.login(mt5.account_info().login, password="", server="") # Check if logged in without re-logging

# Global instance of MT5Connection
mt5_connector = MT5Connection()

def get_symbol_info(symbol: str):
    """Retrieves symbol information from MT5."""
    if not mt5_connector.is_connected():
        logger.error(f"MT5 not connected. Cannot get symbol info for {symbol}.")
        return None
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"Failed to get symbol info for {symbol}. Error: {mt5.last_error()}")
            return None
        if not symbol_info.visible:
            logger.warning(f"Symbol {symbol} is not visible in Market Watch. Attempting to select it.")
            if mt5.symbol_select(symbol, True):
                symbol_info = mt5.symbol_info(symbol) # Try fetching again
                if symbol_info is None:
                    logger.error(f"Failed to select and get symbol info for {symbol} after retry.")
                    return None
            else:
                logger.error(f"Failed to select symbol {symbol}. Error: {mt5.last_error()}")
                return None
        return symbol_info
    except Exception as e:
        logger.error(f"Exception getting symbol info for {symbol}: {e}")
        return None

def get_current_price(symbol: str):
    """Fetches the current Bid and Ask prices for a symbol."""
    if not mt5_connector.is_connected():
        logger.error(f"MT5 not connected. Cannot get current price for {symbol}.")
        return None, None
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return tick.bid, tick.ask
        logger.warning(f"Failed to get tick info for {symbol}. Error: {mt5.last_error()}")
        return None, None
    except Exception as e:
        logger.error(f"Exception getting current price for {symbol}: {e}")
        return None, None

def send_order(
    symbol: str,
    order_type: str, # "BUY" or "SELL"
    volume: float,
    price: float = None, # For MARKET_BUY/SELL, can be None (will use current market price)
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    deviation: int = 10, # Max price deviation in points
    magic_number: int = 0,
    comment: str = "MyAlgoBot"
):
    """
    Sends a market order (BUY or SELL) to MetaTrader 5.
    Returns the order result (dict) on success, None on failure.
    """
    if not mt5_connector.is_connected():
        logger.error("MT5 not connected. Cannot send order.")
        return None

    symbol_info = get_symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Cannot send order for {symbol}: Symbol info not available.")
        return None

    # Get current price if not provided (for market orders)
    current_bid, current_ask = get_current_price(symbol)
    if current_bid is None or current_ask is None:
        logger.error(f"Could not get current price for {symbol}. Cannot send order.")
        return None

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "deviation": deviation,
        "magic": magic_number,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC, # Good Till Cancelled
        "type_filling": mt5.ORDER_FILLING_FOC, # Fill Or Kill (or IOC/RETURN if partial fills are allowed)
    }

    if order_type.upper() == "BUY":
        request["type"] = mt5.ORDER_TYPE_BUY
        request["price"] = current_ask # Buy at Ask price
        request["sl"] = stop_loss
        request["tp"] = take_profit
    elif order_type.upper() == "SELL":
        request["type"] = mt5.ORDER_TYPE_SELL
        request["price"] = current_bid # Sell at Bid price
        request["sl"] = stop_loss
        request["tp"] = take_profit
    else:
        logger.error(f"Invalid order type: {order_type}. Must be 'BUY' or 'SELL'.")
        return None

    logger.info(f"Sending MT5 order: {order_type} {volume} {symbol} @ {request['price']} SL:{stop_loss} TP:{take_profit}")
    try:
        result = mt5.order_send(request)
        if result is None:
            logger.error(f"Order send failed, no result object. Last MT5 error: {mt5.last_error()}")
            return None

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            position_id = result.order # Use order as position ID for market orders
            logger.info(f"Order sent successfully! Position ID: {position_id}, Volume: {result.volume}, Price: {result.price}, Comment: {result.comment}")
            return {
                "position_id": position_id,
                "symbol": symbol,
                "type": order_type,
                "volume": result.volume,
                "entry_price": result.price,
                "open_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "magic_number": magic_number,
                "comment": comment,
                "retcode": result.retcode,
                "deal_id": result.deal # The actual deal ticket
            }
        else:
            logger.error(f"Order failed! Return code: {result.retcode} ({mt5.last_error()}). Request: {request}. Result: {result}")
            # Log full result and request for debugging
            logger.debug(f"Full Order Result: {result}")
            logger.debug(f"Full Order Request: {request}")
            return None
    except Exception as e:
        logger.error(f"Exception during MT5 order send for {symbol}: {e}")
        return None

def modify_position(position_id: int, symbol: str, new_sl: float = 0.0, new_tp: float = 0.0, magic_number: int = 0):
    """
    Modifies an existing open position's Stop Loss (SL) and Take Profit (TP).
    """
    if not mt5_connector.is_connected():
        logger.error("MT5 not connected. Cannot modify position.")
        return None

    symbol_info = get_symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Cannot modify position {position_id}: Symbol info not available for {symbol}.")
        return None

    # Get current position details from MT5 (important to get current price/type)
    positions = mt5.positions_get(symbol=symbol)
    current_position = next((p for p in positions if p.ticket == position_id), None)

    if not current_position:
        logger.warning(f"Position {position_id} not found on MT5 terminal. Cannot modify.")
        return None

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": position_id,
        "symbol": symbol,
        "sl": new_sl,
        "tp": new_tp,
        "deviation": 10, # Deviation for modification (optional, but good practice)
        "magic": magic_number,
        "comment": "SL/TP Update"
    }

    logger.info(f"Modifying position {position_id} for {symbol}: New SL={new_sl}, New TP={new_tp}")
    try:
        result = mt5.order_send(request)
        if result is None:
            logger.error(f"Position modification failed, no result object. Last MT5 error: {mt5.last_error()}")
            return False

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Position {position_id} SL/TP modified successfully.")
            return True
        else:
            logger.error(f"Position modification failed! Return code: {result.retcode} ({mt5.last_error()}). Request: {request}. Result: {result}")
            logger.debug(f"Full Modify Result: {result}")
            logger.debug(f"Full Modify Request: {request}")
            return False
    except Exception as e:
        logger.error(f"Exception during MT5 position modification for {position_id}: {e}")
        return False

def close_position(position_id: int, symbol: str, volume: float, position_type: str, magic_number: int = 0):
    """
    Closes an open position on MetaTrader 5.
    `position_type` is needed to determine if it's a BUY (close with SELL) or SELL (close with BUY).
    """
    if not mt5_connector.is_connected():
        logger.error("MT5 not connected. Cannot close position.")
        return None

    symbol_info = get_symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Cannot close position {position_id}: Symbol info not available for {symbol}.")
        return None

    # Determine close type based on position type
    close_type = mt5.ORDER_TYPE_SELL if position_type.upper() == "BUY" else mt5.ORDER_TYPE_BUY
    current_bid, current_ask = get_current_price(symbol)
    if current_bid is None or current_ask is None:
        logger.error(f"Could not get current price for {symbol}. Cannot close position {position_id}.")
        return None

    close_price = current_bid if position_type.upper() == "BUY" else current_ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": close_type,
        "position": position_id, # Crucial: specify the position to close
        "price": close_price,
        "deviation": 10,
        "magic": magic_number,
        "comment": "CloseByBot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOC,
    }

    logger.info(f"Attempting to close position {position_id} for {symbol} ({position_type} {volume}) @ {close_price}")
    try:
        result = mt5.order_send(request)
        if result is None:
            logger.error(f"Close position failed, no result object. Last MT5 error: {mt5.last_error()}")
            return None

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Position {position_id} closed successfully! Deal ID: {result.deal}, Price: {result.price}.")
            return {
                "position_id": position_id,
                "exit_price": result.price,
                "close_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "retcode": result.retcode,
                "deal_id": result.deal
            }
        else:
            logger.error(f"Failed to close position {position_id}! Return code: {result.retcode} ({mt5.last_error()}). Result: {result}")
            logger.debug(f"Full Close Result: {result}")
            logger.debug(f"Full Close Request: {request}")
            return None
    except Exception as e:
        logger.error(f"Exception during MT5 position close for {position_id}: {e}")
        return None

def get_account_info():
    """Retrieves current account information from MT5."""
    if not mt5_connector.is_connected():
        logger.error("MT5 not connected. Cannot get account info.")
        return None
    try:
        account_info = mt5.account_info()
        if account_info:
            return {
                "login": account_info.login,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "profit": account_info.profit,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "currency": account_info.currency,
                "leverage": account_info.leverage
            }
        logger.warning(f"Failed to get account info. Error: {mt5.last_error()}")
        return None
    except Exception as e:
        logger.error(f"Exception getting account info: {e}")
        return None

# You can add a test block here if you wish to test this module in isolation.
# For example:
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG) # Set root logger to DEBUG for more output

    # --- Important for local testing ---
    # 1. Ensure MetaTrader5 terminal is open and logged into an account.
    # 2. If MT5 is not in default path, specify `path` parameter in `mt5_connector.initialize()`
    #    e.g., path="C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    # 3. Ensure the symbol you want to test (e.g., "EURUSD") is visible in your MT5 Market Watch.

    test_symbol = "EURUSD" # Use a common symbol for testing
    test_magic_number = 123456

    print(f"\n--- Testing MT5 Connection and Trading Operations for {test_symbol} ---")

    if mt5_connector.initialize(): # Initialize MT5 connection
        account_info = get_account_info()
        if account_info:
            print(f"Account Info: Balance={account_info['balance']}, Equity={account_info['equity']}")
        else:
            print("Failed to get account info.")

        bid, ask = get_current_price(test_symbol)
        if bid and ask:
            print(f"Current price for {test_symbol}: Bid={bid}, Ask={ask}")
        else:
            print(f"Failed to get current price for {test_symbol}.")

        # --- Test Buy Order (on a demo account!) ---
        # print("\nAttempting to send BUY order...")
        # # Set SL/TP very wide for testing, or to 0 if not desired
        # sl_buy = bid - 0.0050 # Example: 50 pips below
        # tp_buy = ask + 0.0100 # Example: 100 pips above
        # buy_result = send_order(test_symbol, "BUY", 0.01, stop_loss=sl_buy, take_profit=tp_buy, magic_number=test_magic_number)
        # if buy_result:
        #     print(f"BUY Order successful! Position ID: {buy_result['position_id']}")
        #     # Simulate some time passing
        #     # time.sleep(5)
        #     # print(f"Attempting to modify SL/TP for position {buy_result['position_id']}...")
        #     # modify_position(buy_result['position_id'], test_symbol, new_sl=buy_result['entry_price'] - 0.0020, new_tp=buy_result['entry_price'] + 0.0040, magic_number=test_magic_number)
        #     # time.sleep(5)
        #     # print(f"Attempting to close position {buy_result['position_id']}...")
        #     # close_result = close_position(buy_result['position_id'], test_symbol, 0.01, "BUY", magic_number=test_magic_number)
        #     # if close_result:
        #     #     print(f"Position {buy_result['position_id']} closed successfully.")
        #     # else:
        #     #     print(f"Failed to close position {buy_result['position_id']}.")
        # else:
        #     print("BUY Order failed.")


        # --- Test Sell Order (on a demo account!) ---
        # print("\nAttempting to send SELL order...")
        # sl_sell = ask + 0.0050 # Example: 50 pips above
        # tp_sell = bid - 0.0100 # Example: 100 pips below
        # sell_result = send_order(test_symbol, "SELL", 0.01, stop_loss=sl_sell, take_profit=tp_sell, magic_number=test_magic_number)
        # if sell_result:
        #     print(f"SELL Order successful! Position ID: {sell_result['position_id']}")
        # else:
        #     print("SELL Order failed.")

    else:
        print("Failed to initialize MT5 connection.")

    mt5_connector.shutdown() # Ensure MT5 is shut down at the end of testing
    print("\n--- MT5 Testing Complete ---")