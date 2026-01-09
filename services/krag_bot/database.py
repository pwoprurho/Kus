import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def connect_db(db_file):
    """Establishes a connection to the SQLite database. Creates the file if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row # Allows accessing columns by name
        logger.info(f"Connected to database: {db_file}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error for {db_file}: {e}")
        raise # Re-raise the exception to be handled by the caller

def create_tables(conn):
    """Creates necessary tables if they don't exist."""
    try:
        cursor = conn.cursor()
        
        # Table for bot state (single row to store daily progress, last heartbeat, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_state (
                id INTEGER PRIMARY KEY,
                last_trading_day TEXT NOT NULL,
                daily_trade_count INTEGER NOT NULL,
                daily_equity_start REAL NOT NULL,
                daily_profit_loss REAL NOT NULL,
                last_heartbeat_time TEXT NOT NULL
            )
        ''')
        
        # Table for open positions (what the bot currently holds)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS open_positions (
                position_id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                position_type TEXT NOT NULL, -- 'BUY' or 'SELL'
                entry_price REAL NOT NULL,
                volume REAL NOT NULL,
                open_time TEXT NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                magic_number INTEGER
            )
        ''')
        
        # Table for closed trades history (all completed trades for PnL analysis)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                position_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                volume REAL NOT NULL,
                open_time TEXT NOT NULL,
                close_time TEXT NOT NULL,
                profit REAL NOT NULL,
                status TEXT NOT NULL, -- e.g., 'CLOSED_PROFIT', 'CLOSED_LOSS', 'CLOSED_BREAKEVEN'
                close_reason TEXT -- e.g., 'TP', 'SL', 'Manual', 'Strategy Exit'
            )
        ''')
        
        conn.commit()
        logger.info("Database tables checked/created.")
    except sqlite3.Error as e:
        logger.error(f"Error creating tables: {e}")
        raise # Re-raise the exception

def get_bot_state(conn):
    """Retrieves the current bot state."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bot_state LIMIT 1")
    state = cursor.fetchone()
    return dict(state) if state else None

def update_bot_state(conn, **kwargs):
    """Updates or inserts the bot's state."""
    cursor = conn.cursor()
    current_state = get_bot_state(conn)

    if current_state:
        # Update existing row
        set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
        query = f"UPDATE bot_state SET {set_clause} WHERE id = ?"
        values = list(kwargs.values()) + [current_state['id']]
        cursor.execute(query, values)
    else:
        # Insert new row
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        query = f"INSERT INTO bot_state ({columns}) VALUES ({placeholders})"
        values = list(kwargs.values())
        cursor.execute(query, values)
    conn.commit()

def add_open_position(conn, position_id, symbol, position_type, entry_price, volume, open_time, stop_loss=0.0, take_profit=0.0, magic_number=0):
    """Adds a new open position to the database."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO open_positions (position_id, symbol, position_type, entry_price, volume, open_time, stop_loss, take_profit, magic_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (position_id, symbol, position_type, entry_price, volume, open_time, stop_loss, take_profit, magic_number)
    )
    conn.commit()
    logger.info(f"Added open position {position_id} for {symbol} to DB.")

def delete_open_position(conn, position_id):
    """Deletes an open position from the database."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM open_positions WHERE position_id = ?", (position_id,))
    conn.commit()
    logger.info(f"Deleted open position {position_id} from DB.")

def get_open_positions(conn, symbol=None):
    """Retrieves all or specific open positions."""
    cursor = conn.cursor()
    if symbol:
        cursor.execute("SELECT * FROM open_positions WHERE symbol = ?", (symbol,))
    else:
        cursor.execute("SELECT * FROM open_positions")
    return [dict(row) for row in cursor.fetchall()]

def add_trade_history(conn, position_id, symbol, position_type, entry_price, exit_price, volume, open_time, close_time, profit, status, close_reason):
    """Adds a closed trade to the history table."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trades_history (position_id, symbol, position_type, entry_price, exit_price, volume, open_time, close_time, profit, status, close_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (position_id, symbol, position_type, entry_price, exit_price, volume, open_time, close_time, profit, status, close_reason)
    )
    conn.commit()
    logger.info(f"Added trade {position_id} for {symbol} to history. Profit: {profit:.2f}")

def reset_bot_state_and_trades(conn):
    """Resets bot state and clears all trade history for a new backtest."""
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_state")
        cursor.execute("DELETE FROM open_positions")
        cursor.execute("DELETE FROM trades_history")
        conn.commit()
        logger.info("Bot state and trade history reset.")
    except sqlite3.Error as e:
        logger.error(f"Error resetting bot state and trades: {e}")
        raise # Re-raise the exception

def close_db(conn):
    """Closes the database connection."""
    if conn:
        conn.close()
        logger.info("Database connection closed.")