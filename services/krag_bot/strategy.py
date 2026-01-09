import pandas as pd
import logging
import yaml
import os
import json
import re
from datetime import datetime, timedelta

# Import necessary modules
import modules.indicators as indicators
import modules.trade_execution as trade_execution
import modules.database as database
import modules.notifications as notifications # For alerts related to strategy decisions
from modules.ai_analysis import AIAnalyzer
from modules.news_oracle import NewsOracle
from modules.compliance_agent import ComplianceAgent

# Configure logging for this module
logger = logging.getLogger(__name__)

class TradingStrategy:
    """
    Encapsulates the entire trading strategy logic.
    """
    def __init__(self, config_path="config/strategy_params.yaml", db_connection=None):
        self.config = self._load_config(config_path)
        self.db_conn = db_connection
        self.magic_number = self.config.get('mt5_magic_number', 0)
        self.deviation = self.config.get('mt5_deviation', 10)
        
        # Initialize AI ecosystem (Helix Agents)
        self.ai_enabled = self.config.get('ai_enabled', False)
        if self.ai_enabled:
            self.ai_analyzer = AIAnalyzer(model_name=self.config.get('ai_model_name', "gemini-2.5-flash-lite"))
            self.news_oracle = NewsOracle(self.config)
            self.compliance_agent = ComplianceAgent(self.config)
        else:
            self.ai_analyzer = None
            self.news_oracle = None
            self.compliance_agent = None

        logger.info("TradingStrategy initialized and Helix Agents loaded.")

    def _load_config(self, config_path):
        """Loads strategy parameters from a YAML file."""
        absolute_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_path)
        try:
            with open(absolute_config_path, 'r') as file:
                config = yaml.safe_load(file)
            logger.info(f"Loaded strategy configuration from {absolute_config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Strategy config file not found: {absolute_config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing strategy config file: {e}")
            raise

    def set_db_connection(self, conn):
        """Sets the database connection after initialization."""
        self.db_conn = conn
        logger.info("Database connection set for TradingStrategy.")

    def _get_risk_management_params(self):
        """Helper to get risk management parameters."""
        return {
            "risk_per_trade_percent": self.config.get('risk_per_trade_percent', 1.0),
            "max_daily_loss_percent": self.config.get('max_daily_loss_percent', 5.0),
            "fixed_sl_percentage": self.config.get('fixed_sl_percentage', 1.0),
            "risk_to_reward_ratio": self.config.get('risk_to_reward_ratio', 2.0),
            "max_trades_per_day": self.config.get('max_trades_per_day', 5),
            "max_open_positions": self.config.get('max_open_positions', 2)
        }

    def calculate_lot_size(self, symbol: str, entry_price: float, stop_loss_price: float) -> float:
        """
        Calculates the appropriate lot size based on account equity, risk per trade,
        and the distance to the stop loss.
        """
        account_info = trade_execution.get_account_info()
        if not account_info:
            logger.error("Could not get account info for lot size calculation.")
            return 0.0

        equity = account_info['equity']
        risk_params = self._get_risk_management_params()
        risk_per_trade_percent = risk_params['risk_per_trade_percent']

        if stop_loss_price == 0.0 or entry_price == stop_loss_price:
            logger.error(f"Invalid SL price ({stop_loss_price}) or same as entry price ({entry_price}) for lot size calculation.")
            return 0.0

        # Calculate risk amount based on equity
        risk_amount = (equity * risk_per_trade_percent) / 100

        # Calculate the potential loss per unit (e.g., per 1.0 lot)
        # This part is highly dependent on symbol's pip/point value and contract size.
        # For simplicity, let's assume 1 pip is 0.0001 for a 5-digit quote like EURUSD,
        # and a standard lot is 100,000 units.
        # For crypto, it's usually just (entry - SL) * volume
        
        # Determine pip/point value from symbol info
        symbol_info = trade_execution.get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Failed to get symbol info for {symbol} for lot size calculation.")
            return 0.0

        point_value = symbol_info.point # Value of one point
        contract_size = symbol_info.trade_contract_size # E.g., 100000 for 1 lot EURUSD

        # Calculate stop loss distance in terms of price difference
        sl_distance = abs(entry_price - stop_loss_price)

        if sl_distance == 0:
            logger.warning(f"SL distance is zero for {symbol}. Cannot calculate lot size.")
            return 0.0

        # Calculate lot size: Risk Amount / (SL Distance * Point Value * Contract Size per Lot)
        # Assuming lot size is directly proportional to volume for crypto/forex
        # For forex: (Risk Amount / (SL_pips * Pip_value_per_lot))
        # For crypto: Risk Amount / (SL_distance * price_per_unit)

        # Simplified for crypto:
        # A change of `sl_distance` means `sl_distance * volume` loss for `volume` units
        # Risk Amount = sl_distance * volume
        # volume = Risk Amount / sl_distance
        
        # For forex, often better to calculate based on pip value
        # e.g., if EURUSD, 1 lot = $10 per pip
        # sl_pips = sl_distance / point_value
        # If your broker defines 1 standard lot (1.0) as moving $10 per pip on a 5-digit quote:
        # loss_per_lot_at_sl = sl_pips * (10 / (10**symbol_info.digits)) * (10**symbol_info.digits) # This can be complex.
        # simpler: loss_per_lot_at_sl = sl_distance * contract_size
        
        # Using a general approach:
        # If you buy 1 unit of BTC at 60k and SL is 59k, you lose 1k per unit.
        # If your risk is $100, you can trade $100 / $1000 = 0.1 units.
        # So, volume = risk_amount / sl_distance
        
        # Ensure minimum volume is respected, get from symbol_info
        min_volume = symbol_info.volume_min
        volume_step = symbol_info.volume_step
        max_volume = symbol_info.volume_max

        calculated_volume = risk_amount / sl_distance # This is the "base" volume in units

        # Adjust for symbol's contract size and minimum volume, step
        # If 1 lot = 1 unit for crypto, or 1 lot = 100,000 for forex
        # The result of `calculated_volume` is in units. Convert to lots if needed.
        
        # Example for forex: if 1 standard lot (1.0) is 100,000 units (contract_size)
        # Then volume in lots = (calculated_volume_in_units / contract_size)
        
        # For simplicity, assume calculated_volume is directly in "lots" or units MT5 expects.
        # If MT5 expects 0.01 for mini-lots, or 0.1 for micro, this needs to be scaled.
        # A safer approach is to test this directly with your broker and symbol.

        # Snap to volume step
        lot_size = max(min_volume, round(calculated_volume / volume_step) * volume_step)
        lot_size = min(lot_size, max_volume) # Ensure not exceeding max volume

        logger.info(f"Calculated lot size for {symbol}: {lot_size:.2f} (Risk: ${risk_amount:.2f})")
        return lot_size

    def check_market_environment(self, df_htf: pd.DataFrame) -> dict:
        """
        Evaluates the overall market environment (trend, volatility) on a higher timeframe.
        Returns a dictionary with environment status.
        """
        env_status = {
            'is_uptrend': False,
            'is_downtrend': False,
            'is_trending': False, # For ADX
            'is_ranging': False
        }

        if df_htf.empty:
            logger.warning("Higher timeframe DataFrame is empty for market environment check.")
            return env_status

        last_idx = df_htf.index[-1]
        
        # 1. EMA Trend Definition (Extreme Uptrend/Downtrend)
        ema_short_col = f'ema_short'
        ema_medium_col = f'ema_medium'
        ema_long_col = f'ema_long'
        ema_very_long_col = f'ema_very_long'
        
        # Ensure EMAs are present and not NaN at the latest bar
        if not all(col in df_htf.columns and pd.notna(df_htf.loc[last_idx, col]) for col in [ema_short_col, ema_medium_col, ema_long_col, ema_very_long_col]):
            logger.warning("Not all required EMAs are available for HTF trend check.")
            return env_status

        # Check for clear stack for uptrend
        if (df_htf.loc[last_idx, ema_short_col] > df_htf.loc[last_idx, ema_medium_col] and
            df_htf.loc[last_idx, ema_medium_col] > df_htf.loc[last_idx, ema_long_col] and
            df_htf.loc[last_idx, ema_long_col] > df_htf.loc[last_idx, ema_very_long_col]):
            env_status['is_uptrend'] = True

        # Check for clear stack for downtrend
        if (df_htf.loc[last_idx, ema_short_col] < df_htf.loc[last_idx, ema_medium_col] and
            df_htf.loc[last_idx, ema_medium_col] < df_htf.loc[last_idx, ema_long_col] and
            df_htf.loc[last_idx, ema_long_col] < df_htf.loc[last_idx, ema_very_long_col]):
            env_status['is_downtrend'] = True

        # 2. ADX Filtering (Trending vs. Ranging)
        adx_period = self.config.get('adx_period', 14)
        adx_trending_threshold = self.config.get('adx_trending_threshold', 25)
        adx_col = f'ADX_{adx_period}'

        if adx_col in df_htf.columns and pd.notna(df_htf.loc[last_idx, adx_col]):
            if df_htf.loc[last_idx, adx_col] >= adx_trending_threshold:
                env_status['is_trending'] = True
                logger.info(f"Market is trending (ADX {adx_col}: {df_htf.loc[last_idx, adx_col]:.2f})")
            else:
                env_status['is_ranging'] = True
                logger.info(f"Market is ranging (ADX {adx_col}: {df_htf.loc[last_idx, adx_col]:.2f})")
        else:
            logger.warning(f"ADX column '{adx_col}' not available for HTF trending check.")

        logger.info(f"Market Environment: Uptrend={env_status['is_uptrend']}, Downtrend={env_status['is_downtrend']}, Trending={env_status['is_trending']}, Ranging={env_status['is_ranging']}")
        return env_status

    def evaluate_entry_signals(self, df_ltf: pd.DataFrame, market_env: dict, trade_type: str, is_recovery_trade: bool = False, symbol: str = None) -> dict:
        """
        Evaluates various signals for a potential entry.
        Returns a dictionary indicating signal strengths and reasons.
        `trade_type` can be 'BUY' or 'SELL'.
        """
        signal_strength = 0
        reasons = []
        entry_signals = {
            'is_signal': False,
            'strength': 0,
            'reasons': []
        }

        if df_ltf.empty:
            logger.warning("Low timeframe DataFrame is empty for entry signal evaluation.")
            return entry_signals

        last_idx = df_ltf.index[-1]
        prev_idx = df_ltf.index[-2] if len(df_ltf) >= 2 else None

        current_close = df_ltf.loc[last_idx, 'close']
        current_open = df_ltf.loc[last_idx, 'open']
        current_high = df_ltf.loc[last_idx, 'high']
        current_low = df_ltf.loc[last_idx, 'low']
        current_volume = df_ltf.loc[last_idx, 'volume']

        if prev_idx:
            prev_close = df_ltf.loc[prev_idx, 'close']
            prev_open = df_ltf.loc[prev_idx, 'open']

        # Get relevant strategy parameters
        params = self.config
        rsi_period = params.get('rsi_period', 14)
        rsi_buy_threshold = params.get('rsi_buy_threshold', 30)
        rsi_sell_threshold = params.get('rsi_sell_threshold', 70)

        crsi_rsi_price_period = params.get('crsi_rsi_price_period', 3)
        crsi_up_down_length_period = params.get('crsi_up_down_length_period', 2)
        crsi_percent_rank_period = params.get('crsi_percent_rank_period', 100)
        crsi_buy_threshold = params.get('crsi_buy_threshold', 25)
        crsi_sell_threshold = params.get('crsi_sell_threshold', 75)

        macd_fast = params.get('macd_fast_period', 12)
        macd_slow = params.get('macd_slow_period', 26)
        macd_signal = params.get('macd_signal_period', 9)
        
        atr_period = params.get('atr_period', 14)

        # Apply stricter conditions for recovery trades
        strictness_multiplier = params.get('recovery_trade_strictness_multiplier', 1.0) if is_recovery_trade else 1.0
        
        # --- Signal Checks ---

        # 1. Price Action Confirmation (Candlestick Pattern)
        # Simplified Engulfing pattern check
        if prev_idx:
            if trade_type == 'BUY':
                # Bullish Engulfing: Current candle body is bullish and engulfs previous bearish body
                if (current_close > current_open and prev_close < prev_open and
                    current_open < prev_close and current_close > prev_open and
                    (current_close - current_open) > (prev_open - prev_close) * params.get('bullish_engulfing_min_ratio', 1.2)):
                    signal_strength += 1
                    reasons.append("Price Action: Bullish Engulfing")
            elif trade_type == 'SELL':
                # Bearish Engulfing: Current candle body is bearish and engulfs previous bullish body
                if (current_close < current_open and prev_close > prev_open and
                    current_open > prev_close and current_close < prev_open and
                    (current_open - current_close) > (prev_close - prev_open) * params.get('bearish_engulfing_min_ratio', 1.2)): # Assume a bearish ratio if not defined
                    signal_strength += 1
                    reasons.append("Price Action: Bearish Engulfing")

        # 2. RSI Confirmation
        rsi_col = f'RSI_{rsi_period}'
        if rsi_col in df_ltf.columns and pd.notna(df_ltf.loc[last_idx, rsi_col]):
            current_rsi = df_ltf.loc[last_idx, rsi_col]
            if trade_type == 'BUY' and current_rsi <= (rsi_buy_threshold * strictness_multiplier):
                signal_strength += 1
                reasons.append(f"RSI: Oversold ({current_rsi:.2f} <= {rsi_buy_threshold * strictness_multiplier:.2f})")
            elif trade_type == 'SELL' and current_rsi >= (rsi_sell_threshold / strictness_multiplier):
                signal_strength += 1
                reasons.append(f"RSI: Overbought ({current_rsi:.2f} >= {rsi_sell_threshold / strictness_multiplier:.2f})")
        else:
            logger.warning(f"RSI column '{rsi_col}' not available for signal check.")

        # 3. CRSI Confirmation (Composite RSI)
        # Ensure CRSI is calculated in indicators.py
        crsi_col = 'CRSI' # From calculate_crsi function
        if crsi_col in df_ltf.columns and pd.notna(df_ltf.loc[last_idx, crsi_col]):
            current_crsi = df_ltf.loc[last_idx, crsi_col]
            if trade_type == 'BUY' and current_crsi <= (crsi_buy_threshold * strictness_multiplier):
                signal_strength += 1
                reasons.append(f"CRSI: Oversold ({current_crsi:.2f} <= {crsi_buy_threshold * strictness_multiplier:.2f})")
            elif trade_type == 'SELL' and current_crsi >= (crsi_sell_threshold / strictness_multiplier):
                signal_strength += 1
                reasons.append(f"CRSI: Overbought ({current_crsi:.2f} >= {crsi_sell_threshold / strictness_multiplier:.2f})")
        else:
            logger.warning(f"CRSI column '{crsi_col}' not available for signal check.")

        # 4. MACD Confirmation
        macd_col = f'MACD_{macd_fast}_{macd_slow}_{macd_signal}'
        macds_col = f'MACDS_{macd_fast}_{macd_slow}_{macd_signal}'
        if all(col in df_ltf.columns and pd.notna(df_ltf.loc[last_idx, col]) for col in [macd_col, macds_col]):
            current_macd = df_ltf.loc[last_idx, macd_col]
            current_macds = df_ltf.loc[last_idx, macds_col]
            if trade_type == 'BUY' and current_macd > current_macds and df_ltf.loc[prev_idx, macd_col] <= df_ltf.loc[prev_idx, macds_col]:
                # MACD cross above signal line (bullish cross)
                signal_strength += 1
                reasons.append("MACD: Bullish Crossover")
            elif trade_type == 'SELL' and current_macd < current_macds and df_ltf.loc[prev_idx, macd_col] >= df_ltf.loc[prev_idx, macds_col]:
                # MACD cross below signal line (bearish cross)
                signal_strength += 1
                reasons.append("MACD: Bearish Crossover")
        else:
            logger.warning(f"MACD columns '{macd_col}' or '{macds_col}' not available for signal check.")

        # 5. Volume Confirmation (e.g., above average volume on signal candle)
        # Need to calculate a rolling average volume first
        if 'volume' in df_ltf.columns and current_volume > 0:
            avg_volume_period = params.get('volume_avg_period', 20) # Define in config
            if len(df_ltf) >= avg_volume_period:
                avg_volume = df_ltf['volume'].iloc[-avg_volume_period:-1].mean() # Average of previous bars
                volume_confirm_ratio = params.get('volume_confirm_ratio', 1.5) # Define in config
                if current_volume > (avg_volume * volume_confirm_ratio):
                    signal_strength += 1
                    reasons.append(f"Volume: Above Average ({current_volume:.0f} > {avg_volume * volume_confirm_ratio:.0f})")
            else:
                logger.warning(f"Insufficient data for average volume calculation (need {avg_volume_period} bars).")
        else:
            logger.warning("Volume column not available or current volume is zero.")

        # 6. ATR (Average True Range) Confirmation (e.g., current candle size relative to ATR)
        atr_col = f'ATR_{atr_period}'
        if atr_col in df_ltf.columns and pd.notna(df_ltf.loc[last_idx, atr_col]):
            current_atr = df_ltf.loc[last_idx, atr_col]
            if current_atr > 0:
                candle_range = abs(current_high - current_low)
                atr_candle_ratio = params.get('atr_candle_ratio', 0.5) # E.g., candle range should be at least 50% of ATR
                if candle_range >= (current_atr * atr_candle_ratio):
                    signal_strength += 1
                    reasons.append(f"ATR: Significant Candle Range ({candle_range:.4f} >= {current_atr * atr_candle_ratio:.4f})")
        else:
            logger.warning(f"ATR column '{atr_col}' not available for signal check.")

        # Combine checks with market environment and recovery trade logic
        min_signals_required = params.get('min_signals_required', 3) # Define in config

        # If it's a recovery trade, make overall requirements stricter
        if is_recovery_trade:
            min_signals_required = int(min_signals_required * strictness_multiplier)
            logger.info(f"Recovery trade mode: Min signals required increased to {min_signals_required}.")

        # --- AI Integration ---
        if self.ai_enabled and self.ai_analyzer and signal_strength > 0 and symbol:
             try:
                logger.info(f"Requesting AI validation for {symbol} ({trade_type}) signal...")
                analysis = self.ai_analyzer.analyze_market(
                     symbol,
                     df_ltf,
                     reasons
                )
                
                ai_decision = analysis.get('decision', 'NEUTRAL')
                ai_confidence = analysis.get('confidence', 0)
                ai_reasoning = analysis.get('reasoning', '')
                
                # Add AI findings to signals
                entry_signals['ai_decision'] = ai_decision
                entry_signals['ai_confidence'] = ai_confidence
                entry_signals['ai_reasoning'] = ai_reasoning
                
                # Logic: If AI Agrees with high confidence, boost strength
                if ai_decision == trade_type and ai_confidence >= self.config.get('ai_confidence_threshold', 70):
                    signal_strength += 2 # Give it a big boost
                    reasons.append(f"AI: Confirmed {ai_decision} ({ai_confidence}%)")
                    logger.info(f"AI Confirmed {trade_type} for {symbol}. Confidence: {ai_confidence}%")
                elif ai_decision != 'HOLD' and ai_decision != trade_type:
                     # AI disagrees strongly
                     signal_strength -= 2
                     reasons.append(f"AI: Disagrees, suggests {ai_decision}")
                     logger.warning(f"AI Disagrees with {trade_type} for {symbol}. Suggests {ai_decision}")
             except Exception as e:
                logger.error(f"Error during AI analysis: {e}")

        if signal_strength >= min_signals_required:
            entry_signals['is_signal'] = True
            entry_signals['strength'] = signal_strength
            entry_signals['reasons'] = reasons
            logger.info(f"Entry Signal Detected ({trade_type}) with strength {signal_strength}: {', '.join(reasons)}")
        else:
            logger.info(f"No strong entry signal ({trade_type}). Strength: {signal_strength}/{min_signals_required}. Reasons: {', '.join(reasons) if reasons else 'None'}")

        return entry_signals

    def manage_positions(self, symbol: str, current_price: float):
        """
        Manages existing open positions for the given symbol (updates SL/TP, checks for exits).
        """
        if not self.db_conn:
            logger.error("Database connection not set for strategy. Cannot manage positions.")
            return

        open_positions = database.get_open_positions(self.db_conn)
        positions_for_symbol = [p for p in open_positions if p['symbol'] == symbol]

        for pos in positions_for_symbol:
            position_id = pos['position_id']
            entry_price = pos['entry_price']
            position_type = pos['position_type']
            current_sl = pos['stop_loss']
            current_tp = pos['take_profit']
            open_time = datetime.strptime(pos['open_time'], '%Y-%m-%d %H:%M:%S')
            volume = pos['volume']

            # Calculate current profit/loss (R-value)
            price_diff = (current_price - entry_price) if position_type == 'BUY' else (entry_price - current_price)
            sl_distance = abs(entry_price - current_sl) if current_sl else 0.0

            # Assuming 1R is the initial stop loss distance
            current_r = 0.0
            if sl_distance > 0:
                current_r = price_diff / sl_distance
            
            logger.debug(f"Position {position_id} ({symbol} {position_type}): Current R={current_r:.2f}")

            # 1. Time-Based Exit
            max_duration_minutes = self.config.get('time_based_exit_minutes', 240)
            if (datetime.now() - open_time).total_seconds() / 60 >= max_duration_minutes:
                logger.info(f"Position {position_id} ({symbol}) exceeding max duration ({max_duration_minutes} min). Initiating close.")
                self.execute_close_position(position_id, symbol, volume, position_type, current_price, 'TIME_BASED_EXIT')
                continue # Move to next position

            # 2. Breakeven Stop Loss
            breakeven_enabled = self.config.get('breakeven_enabled', True)
            breakeven_profit_r_multiplier = self.config.get('breakeven_profit_r_multiplier', 0.5)
            breakeven_buffer_percent = self.config.get('breakeven_buffer_percent', 0.05) # 0.05% buffer

            if breakeven_enabled and current_r >= breakeven_profit_r_multiplier:
                # Calculate breakeven price (entry price + small buffer in favorable direction)
                breakeven_price = entry_price + (entry_price * breakeven_buffer_percent / 100) * (1 if position_type == 'BUY' else -1)

                # Ensure new SL is better than current SL and actually moves to breakeven or better
                if position_type == 'BUY' and (current_sl is None or breakeven_price > current_sl):
                    logger.info(f"Moving SL to breakeven for position {position_id} ({symbol}). New SL: {breakeven_price:.5f}")
                    self.update_sl_tp(position_id, symbol, breakeven_price, current_tp)
                elif position_type == 'SELL' and (current_sl is None or breakeven_price < current_sl):
                    logger.info(f"Moving SL to breakeven for position {position_id} ({symbol}). New SL: {breakeven_price:.5f}")
                    self.update_sl_tp(position_id, symbol, breakeven_price, current_tp)
            
            # 3. Trailing Stop Loss
            trailing_stop_enabled = self.config.get('trailing_stop_enabled', True)
            if trailing_stop_enabled and current_r > breakeven_profit_r_multiplier: # Only trail after hitting breakeven or some profit
                atr_period = self.config.get('atr_period', 14)
                # Need to fetch latest OHLCV to calculate current ATR
                # This is a simplification; ideally, ATR should be passed from main loop.
                # For a true production system, you'd calculate ATR on every tick/candle
                # and pass it to this function. For now, we'll assume we have the latest ATR.
                # Placeholder: df_ltf should be passed to this function or fetched here
                # For simplicity, we'll assume current_atr is available (e.g., from main loop)
                # For now, let's just make it a fixed percentage trailing or assume ATR is passed
                
                # --- Assuming ATR is available or calculate it here for current data ---
                # To calculate ATR, you would need recent OHLCV data.
                # As `manage_positions` only receives `current_price`,
                # this would ideally be done in `main.py` and passed down.
                # For example, in `main.py`:
                # df_ltf = data_provider.fetch_ohlcv(...)
                # df_ltf = indicators.calculate_atr(df_ltf, config['atr_period'])
                # current_atr = df_ltf[f'ATR_{config["atr_period"]}'].iloc[-1]
                # Then pass `current_atr` to this function.

                # For this example, let's assume a simplified fixed percentage trailing logic
                trailing_stop_atr_multiplier = self.config.get('trailing_stop_atr_multiplier', 1.5) # This should be ATR based
                sl_update_min_diff = self.config.get('sl_update_min_diff', 0.0001) # Minimum price diff to update SL

                # Example fixed percentage trailing stop, for true ATR trailing, need ATR value
                # A common way is to trail by `N * ATR` from the highest high (for buy) or lowest low (for sell)
                # Since we don't have historical high/low here, this is a conceptual example.

                new_trailing_sl = current_sl # Initialize with current SL

                if position_type == 'BUY':
                    # Calculate potential new SL, e.g., current_price - (trailing_stop_percent * current_price / 100)
                    # For ATR based: current_price - (trailing_stop_atr_multiplier * current_atr)
                    # For simplicity without ATR:
                    if current_price > entry_price: # Only trail if in profit
                        potential_sl = entry_price + (current_price - entry_price) * 0.5 # Example: trail 50% of profit
                        new_trailing_sl = max(current_sl if current_sl else 0, potential_sl)
                        
                        # Ensure new_trailing_sl is not less than breakeven price if breakeven was set
                        breakeven_price = entry_price + (entry_price * breakeven_buffer_percent / 100)
                        if breakeven_enabled:
                            new_trailing_sl = max(new_trailing_sl, breakeven_price)

                elif position_type == 'SELL':
                    if current_price < entry_price: # Only trail if in profit
                        potential_sl = entry_price - (entry_price - current_price) * 0.5 # Example: trail 50% of profit
                        new_trailing_sl = min(current_sl if current_sl else float('inf'), potential_sl)

                        breakeven_price = entry_price - (entry_price * breakeven_buffer_percent / 100)
                        if breakeven_enabled:
                            new_trailing_sl = min(new_trailing_sl, breakeven_price)

                # Only update if the new SL is significantly better than current and valid
                if (position_type == 'BUY' and new_trailing_sl > current_sl + sl_update_min_diff) or \
                   (position_type == 'SELL' and new_trailing_sl < current_sl - sl_update_min_diff):
                    logger.info(f"Updating trailing SL for position {position_id} ({symbol}). Old SL: {current_sl:.5f}, New SL: {new_trailing_sl:.5f}")
                    self.update_sl_tp(position_id, symbol, new_trailing_sl, current_tp)

    def update_sl_tp(self, position_id: int, symbol: str, new_sl: float, new_tp: float):
        """Helper to call trade_execution.modify_position and update database."""
        if trade_execution.modify_position(position_id, symbol, new_sl, new_tp, self.magic_number):
            database.update_open_position(self.db_conn, position_id, stop_loss=new_sl, take_profit=new_tp)
            notifications.send_telegram_message(f"🚨 <b>Position Update:</b> {symbol} #{position_id} SL/TP updated to SL:{new_sl:.5f} TP:{new_tp:.5f}")
        else:
            logger.error(f"Failed to modify SL/TP for position {position_id}.")
            notifications.send_telegram_message(f"❌ <b>Error:</b> Failed to modify SL/TP for {symbol} #{position_id}.")

    def execute_close_position(self, position_id: int, symbol: str, volume: float, position_type: str, current_price: float, reason: str):
        """
        Executes closing of a position, updates database, and logs history.
        """
        close_result = trade_execution.close_position(position_id, symbol, volume, position_type, self.magic_number)
        if close_result:
            profit = 0.0 # Calculate actual profit based on entry/exit price and volume/contract size
            # Retrieve original entry details to calculate profit
            original_pos = database.get_open_position_by_id(self.db_conn, position_id)
            if original_pos:
                entry_price = original_pos['entry_price']
                if position_type == 'BUY':
                    profit = (close_result['exit_price'] - entry_price) * volume # Simplified profit calculation
                else: # SELL
                    profit = (entry_price - close_result['exit_price']) * volume # Simplified profit calculation
                
                trade_status = 'CLOSED_PROFIT' if profit > 0 else ('CLOSED_LOSS' if profit < 0 else 'CLOSED_BREAKEVEN')

                database.log_trade_history(self.db_conn, {
                    'position_id': position_id,
                    'symbol': symbol,
                    'position_type': position_type,
                    'entry_price': entry_price,
                    'exit_price': close_result['exit_price'],
                    'volume': volume,
                    'open_time': original_pos['open_time'],
                    'close_time': close_result['close_time'],
                    'profit': profit,
                    'status': trade_status,
                    'close_reason': reason
                })
                database.delete_open_position(self.db_conn, position_id)
                notifications.send_telegram_message(f"✅ <b>Position Closed:</b> {symbol} #{position_id} ({position_type}) closed at {close_result['exit_price']:.5f} for {profit:.2f} profit. Reason: {reason}")
                logger.info(f"Position {position_id} ({symbol}) closed. Profit: {profit:.2f}. Reason: {reason}")

                # Update daily P/L
                bot_state = database.get_bot_state(self.db_conn)
                if bot_state:
                    updated_daily_profit_loss = bot_state['daily_profit_loss'] + profit
                    database.update_bot_state(self.db_conn, daily_profit_loss=updated_daily_profit_loss)
            else:
                logger.error(f"Original position {position_id} not found in DB for profit calculation after close.")
        else:
            logger.error(f"Failed to close position {position_id} for {symbol}.")
            notifications.send_telegram_message(f"❌ <b>Error:</b> Failed to close position {symbol} #{position_id}.")


    def check_and_execute_trades(self, symbol: str, ltf_data: pd.DataFrame, htf_data: pd.DataFrame, is_recovery_trade: bool = False):
        """
        Main function to check for signals and execute trades.
        """
        if not self.db_conn:
            logger.error("Database connection not set for strategy. Cannot check/execute trades.")
            return

        # Check daily trade limits and max daily loss
        bot_state = database.get_bot_state(self.db_conn)
        current_day = datetime.now().strftime('%Y-%m-%d')
        risk_params = self._get_risk_management_params()

        if bot_state['last_trading_day'] != current_day:
            # Reset daily counters if a new day
            account_info = trade_execution.get_account_info()
            daily_equity_start = account_info['equity'] if account_info else 0.0
            database.update_bot_state(self.db_conn,
                                      last_trading_day=current_day,
                                      daily_trade_count=0,
                                      daily_equity_start=daily_equity_start,
                                      daily_profit_loss=0.0)
            bot_state = database.get_bot_state(self.db_conn) # Refresh state

        if bot_state['daily_trade_count'] >= risk_params['max_trades_per_day']:
            logger.warning(f"Max trades per day ({risk_params['max_trades_per_day']}) reached for {symbol}.")
            return

        if bot_state['daily_equity_start'] > 0 and \
           (bot_state['daily_equity_start'] - (bot_state['daily_equity_start'] + bot_state['daily_profit_loss'])) / bot_state['daily_equity_start'] * 100 >= risk_params['max_daily_loss_percent']:
            logger.warning(f"Max daily loss ({risk_params['max_daily_loss_percent']}%) reached for {symbol}. Stopping trading for the day.")
            notifications.send_telegram_message(f"⚠️ <b>Daily Loss Limit Reached:</b> Trading paused for {symbol} for the day.")
            return

        open_positions = database.get_open_positions(self.db_conn)
        if len(open_positions) >= risk_params['max_open_positions']:
            logger.info(f"Max open positions ({risk_params['max_open_positions']}) reached. Cannot open new trade for {symbol}.")
            return

        # 1. Market Environment Check (HTF)
        market_env = self.check_market_environment(htf_data)

        # 2. Check for BUY Signal
        buy_signal = self.evaluate_entry_signals(ltf_data, market_env, 'BUY', is_recovery_trade, symbol=symbol)
        if buy_signal['is_signal'] and market_env['is_uptrend'] and market_env['is_trending']:
            logger.info(f"Strong BUY signal for {symbol}. Evaluating trade...")
            self._initiate_trade(symbol, 'BUY', ltf_data.iloc[-1]['close'], buy_signal['reasons'], is_recovery_trade)
            return # Only one trade per check cycle for a symbol

        # 3. Check for SELL Signal
        sell_signal = self.evaluate_entry_signals(ltf_data, market_env, 'SELL', is_recovery_trade, symbol=symbol)
        if sell_signal['is_signal'] and market_env['is_downtrend'] and market_env['is_trending']:
            logger.info(f"Strong SELL signal for {symbol}. Evaluating trade...")
            self._initiate_trade(symbol, 'SELL', ltf_data.iloc[-1]['close'], sell_signal['reasons'], is_recovery_trade)
            return

        logger.info(f"No entry signal for {symbol} on this cycle.")

    def _initiate_trade(self, symbol: str, trade_type: str, entry_price: float, reasons: list, is_recovery_trade: bool):
        """
        Helper to initiate a trade if conditions are met after signal evaluation.
        Calculates SL/TP and lot size.
        """
        risk_params = self._get_risk_management_params()
        fixed_sl_percentage = risk_params['fixed_sl_percentage'] / 100 # Convert % to decimal
        risk_to_reward_ratio = risk_params['risk_to_reward_ratio']

        # Calculate initial SL and TP
        if trade_type == 'BUY':
            stop_loss = entry_price * (1 - fixed_sl_percentage)
            take_profit = entry_price + (entry_price - stop_loss) * risk_to_reward_ratio
        else: # SELL
            stop_loss = entry_price * (1 + fixed_sl_percentage)
            take_profit = entry_price - (stop_loss - entry_price) * risk_to_reward_ratio
        
        # Ensure SL/TP values are valid (e.g., non-zero, within min/max ranges if specific to broker)
        # For production, you might need to adjust SL/TP to align with broker's tick size/step.
        symbol_info = trade_execution.get_symbol_info(symbol)
        if symbol_info:
            digit_factor = 10**symbol_info.digits
            # Round SL/TP to instrument's tick precision
            stop_loss = round(stop_loss * digit_factor) / digit_factor
            take_profit = round(take_profit * digit_factor) / digit_factor
            
            # Additional checks: SL must be below current bid for buy, above current ask for sell.
            # TP must be above ask for buy, below bid for sell.
            # This logic needs to be robust for various instruments.

        lot_size = self.calculate_lot_size(symbol, entry_price, stop_loss)
        
        # Apply volume reduction for recovery trades
        if is_recovery_trade:
            initial_volume_reduction = self.config.get('recovery_trade_initial_volume_reduction', 0.5)
            lot_size = max(symbol_info.volume_min, lot_size * initial_volume_reduction)
            logger.info(f"Recovery trade: Adjusted lot size for {symbol} to {lot_size} (initial reduction).")

        if lot_size > 0:
            # --- Helix Guardian Check ---
            if self.compliance_agent:
                # Construct a trade proposal
                reasons_str = json.dumps(reasons)
                
                # Fetch Sentiment now if not already available
                sentiment_data = self.news_oracle.get_sentiment_analysis(symbol) if self.news_oracle else {}
                sentiment_score = sentiment_data.get('sentiment_score', 0)
                
                trade_proposal = {
                    'symbol': symbol,
                    'action': trade_type,
                    'volume': lot_size,
                    'sl': stop_loss,
                    'tp': take_profit,
                    'reason': reasons,
                    'ai_decision': 'CONFIRM' if str(reasons).find("AI: Confirmed") != -1 else None,
                    # Extract confidence if available, using a safer regex
                    'ai_confidence': int(re.search(r"\((\d+)%\)", str(reasons)).group(1)) if str(reasons).find("AI: Confirmed") != -1 and re.search(r"\((\d+)%\)", str(reasons)) else 0,
                    'market_sentiment_score': sentiment_score
                }
                
                # Get Account Info for Daily Loss Check
                account_info = trade_execution.get_account_info()
                # Assuming database tracks daily equity start
                bot_state = database.get_bot_state(self.db_conn)
                acc_snapshot = {
                    'equity': account_info['equity'],
                    'equity_start': bot_state['daily_equity_start'],
                    'daily_loss': abs(min(0, bot_state['daily_profit_loss'])) # Only count loss
                }

                review = self.compliance_agent.review_trade(trade_proposal, acc_snapshot)
                
                if not review['approved']:
                    notifications.send_telegram_message(f"🛡️ <b>Guardian Blocked Trade:</b> {review['rejection_reason']}")
                    logger.warning(f"Guardian blocked trade for {symbol}: {review['rejection_reason']}")
                    return # ABORT TRADE

            order_result = trade_execution.send_order(
                symbol=symbol,
                order_type=trade_type,
                volume=lot_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                magic_number=self.magic_number,
                deviation=self.deviation,
                comment="BotTrade"
            )
            if order_result:
                # Update daily trade count
                bot_state = database.get_bot_state(self.db_conn)
                if bot_state:
                    database.update_bot_state(self.db_conn, daily_trade_count=bot_state['daily_trade_count'] + 1)

                # Save open position to database
                position_data = {
                    'position_id': order_result['position_id'],
                    'symbol': symbol,
                    'position_type': trade_type,
                    'entry_price': order_result['entry_price'],
                    'volume': order_result['volume'],
                    'open_time': order_result['open_time'],
                    'stop_loss': order_result['stop_loss'],
                    'take_profit': order_result['take_profit'],
                    'magic_number': self.magic_number,
                    'comment': order_result['comment']
                }
                database.save_open_position(self.db_conn, position_data)
                notifications.send_telegram_message(
                    f"🚀 <b>New Trade:</b> {trade_type} {lot_size:.2f} {symbol} @ {entry_price:.5f}. SL:{stop_loss:.5f} TP:{take_profit:.5f}. Reasons: {', '.join(reasons)}"
                )
                logger.info(f"Trade executed for {symbol}. Position ID: {order_result['position_id']}")
            else:
                logger.error(f"Failed to execute trade for {symbol}.")
                notifications.send_telegram_message(f"❌ <b>Trade Execution Failed:</b> Could not open {trade_type} {symbol}.")
        else:
            logger.warning(f"Calculated lot size is zero for {symbol}. Trade not initiated.")
            notifications.send_telegram_message(f"⚠️ <b>Trade Warning:</b> Lot size for {symbol} calculated as zero. Trade not initiated.")