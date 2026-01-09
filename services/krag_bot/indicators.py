import pandas as pd
import pandas_ta as ta # Import pandas_ta for efficient indicator calculations
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

def calculate_emas(df: pd.DataFrame, periods: dict) -> pd.DataFrame:
    """
    Calculates multiple Exponential Moving Averages (EMAs) and adds them to the DataFrame.
    Periods should be a dictionary like {'ema_short': 9, 'ema_medium': 21, ...}.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or 'close' not in df.columns:
        logger.error("Invalid DataFrame or missing 'close' column for EMA calculation.")
        return df

    for name, period in periods.items():
        if period > len(df):
            logger.warning(f"EMA period {period} is greater than data length ({len(df)}). Skipping {name}.")
            df[name] = pd.NA
            continue
        try:
            # pandas_ta calculates EMA as 'EMA_period'
            df[name] = ta.ema(df['close'], length=period)
            logger.debug(f"Calculated {name} (EMA {period}).")
        except Exception as e:
            logger.error(f"Error calculating EMA for period {period} ({name}): {e}")
            df[name] = pd.NA # Assign NA on error
    return df

def calculate_adx(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Calculates ADX, +DI, and -DI and adds them to the DataFrame.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
        logger.error("Invalid DataFrame or missing HLC columns for ADX calculation.")
        return df

    if period > len(df):
        logger.warning(f"ADX period {period} is greater than data length ({len(df)}). Skipping ADX calculation.")
        df['ADX'] = pd.NA
        df['DMP'] = pd.NA
        df['DMN'] = pd.NA
        return df

    try:
        # pandas_ta returns a DataFrame with ADX, +DI, -DI columns (e.g., ADX_14, DMX_14, DMN_14)
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=period)
        if adx_df is not None and not adx_df.empty:
            # Rename columns to a consistent format
            df[f'ADX_{period}'] = adx_df[f'ADX_{period}']
            df[f'DMP_{period}'] = adx_df[f'DMP_{period}']
            df[f'DMN_{period}'] = adx_df[f'DMN_{period}']
            logger.debug(f"Calculated ADX, +DI, -DI for period {period}.")
        else:
            logger.warning(f"ADX calculation returned empty for period {period}.")
            df[f'ADX_{period}'] = pd.NA
            df[f'DMP_{period}'] = pd.NA
            df[f'DMN_{period}'] = pd.NA
    except Exception as e:
        logger.error(f"Error calculating ADX for period {period}: {e}")
        df[f'ADX_{period}'] = pd.NA
        df[f'DMP_{period}'] = pd.NA
        df[f'DMN_{period}'] = pd.NA
    return df

def calculate_rsi(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Calculates Relative Strength Index (RSI) and adds it to the DataFrame.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or 'close' not in df.columns:
        logger.error("Invalid DataFrame or missing 'close' column for RSI calculation.")
        return df

    if period > len(df):
        logger.warning(f"RSI period {period} is greater than data length ({len(df)}). Skipping RSI calculation.")
        df[f'RSI_{period}'] = pd.NA
        return df

    try:
        # pandas_ta calculates RSI as 'RSI_period'
        df[f'RSI_{period}'] = ta.rsi(df['close'], length=period)
        logger.debug(f"Calculated RSI for period {period}.")
    except Exception as e:
        logger.error(f"Error calculating RSI for period {period}: {e}")
        df[f'RSI_{period}'] = pd.NA
    return df

def calculate_macd(df: pd.DataFrame, fast_period: int, slow_period: int, signal_period: int) -> pd.DataFrame:
    """
    Calculates MACD, MACD Signal, and MACD Histogram and adds them to the DataFrame.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or 'close' not in df.columns:
        logger.error("Invalid DataFrame or missing 'close' column for MACD calculation.")
        return df

    max_period = max(fast_period, slow_period, signal_period)
    if max_period > len(df):
        logger.warning(f"MACD periods ({fast_period},{slow_period},{signal_period}) are greater than data length ({len(df)}). Skipping MACD calculation.")
        df['MACD'] = pd.NA
        df['MACD_SIGNAL'] = pd.NA
        df['MACD_HIST'] = pd.NA
        return df

    try:
        # pandas_ta calculates MACD as a DataFrame with MACD, MACD_H, MACD_S columns
        macd_df = ta.macd(df['close'], fast=fast_period, slow=slow_period, signal=signal_period)
        if macd_df is not None and not macd_df.empty:
            df[f'MACD_{fast_period}_{slow_period}_{signal_period}'] = macd_df[f'MACD_{fast_period}_{slow_period}_{signal_period}']
            df[f'MACDH_{fast_period}_{slow_period}_{signal_period}'] = macd_df[f'MACDH_{fast_period}_{slow_period}_{signal_period}']
            df[f'MACDS_{fast_period}_{slow_period}_{signal_period}'] = macd_df[f'MACDS_{fast_period}_{slow_period}_{signal_period}']
            logger.debug(f"Calculated MACD ({fast_period},{slow_period},{signal_period}).")
        else:
            logger.warning(f"MACD calculation returned empty for periods {fast_period},{slow_period},{signal_period}.")
            df[f'MACD_{fast_period}_{slow_period}_{signal_period}'] = pd.NA
            df[f'MACDH_{fast_period}_{slow_period}_{signal_period}'] = pd.NA
            df[f'MACDS_{fast_period}_{slow_period}_{signal_period}'] = pd.NA
    except Exception as e:
        logger.error(f"Error calculating MACD for periods {fast_period},{slow_period},{signal_period}: {e}")
        df[f'MACD_{fast_period}_{slow_period}_{signal_period}'] = pd.NA
        df[f'MACDH_{fast_period}_{slow_period}_{signal_period}'] = pd.NA
        df[f'MACDS_{fast_period}_{slow_period}_{signal_period}'] = pd.NA
    return df

def calculate_atr(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Calculates Average True Range (ATR) and adds it to the DataFrame.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
        logger.error("Invalid DataFrame or missing HLC columns for ATR calculation.")
        return df

    if period > len(df):
        logger.warning(f"ATR period {period} is greater than data length ({len(df)}). Skipping ATR calculation.")
        df[f'ATR_{period}'] = pd.NA
        return df

    try:
        # pandas_ta calculates ATR as 'ATR_period'
        df[f'ATR_{period}'] = ta.atr(df['high'], df['low'], df['close'], length=period)
        logger.debug(f"Calculated ATR for period {period}.")
    except Exception as e:
        logger.error(f"Error calculating ATR for period {period}: {e}")
        df[f'ATR_{period}'] = pd.NA
    return df

def calculate_crsi(df: pd.DataFrame, rsi_price_period: int, up_down_length_period: int, percent_rank_period: int) -> pd.DataFrame:
    """
    Calculates Composite RSI (CRSI) based on the specified components.
    CRSI = (RSI_Price + RSI_UpDownLength + PercentRank_ROC) / 3
    This is a custom implementation based on the definition usually found for Connors RSI.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or 'close' not in df.columns:
        logger.error("Invalid DataFrame or missing 'close' column for CRSI calculation.")
        return df

    # 1. RSI of Price (using specified period)
    df = calculate_rsi(df, rsi_price_period)
    rsi_price_col = f'RSI_{rsi_price_period}'

    # 2. RSI of Up/Down Length
    # Calculate Up/Down based on consecutive changes
    df['change'] = df['close'].diff()
    df['up_down_length'] = 0
    current_length = 0
    last_direction = 0 # 1 for up, -1 for down

    for i in range(1, len(df)):
        if df['change'].iloc[i] > 0: # Price went up
            if last_direction == 1:
                current_length += 1
            else:
                current_length = 1
            last_direction = 1
        elif df['change'].iloc[i] < 0: # Price went down
            if last_direction == -1:
                current_length += 1
            else:
                current_length = 1
            last_direction = -1
        else: # No change
            current_length = 0
            last_direction = 0
        df['up_down_length'].iloc[i] = current_length * last_direction # Store length and direction

    # Calculate RSI of Up/Down Length (absolute value of length)
    # Note: pandas_ta's rsi function expects positive values for traditional RSI.
    # We apply RSI logic to the absolute value of the run lengths.
    df[f'RSI_U_D_LEN_{up_down_length_period}'] = ta.rsi(df['up_down_length'].abs(), length=up_down_length_period)

    # 3. Percent Rank of Rate of Change (ROC)
    # Calculate ROC
    df[f'ROC_{percent_rank_period}'] = ta.roc(df['close'], length=1) # ROC(1) for daily change
    # Calculate Percent Rank (usually over a longer lookback, here using pandas_ta percentile_rank)
    # Note: pandas_ta does not have a direct PercentRank function.
    # We will implement a rolling percentile rank for simplicity.
    # This requires a longer history than just 'percent_rank_period' for accurate percentile.
    # The 'lookback' for percentile_rank should be sufficiently large.
    # For now, we'll use a rolling apply if a direct function isn't available.
    # A more robust solution might pre-calculate ROC over a larger window and then get its percentile.

    # Simplified Percent Rank of ROC(1) over a window. This might be different from Connors RSI's exact definition.
    # Connors RSI's PercentRank is typically over the last X bars of ROC(1).
    # We'll use a rolling rank with normalization.
    if percent_rank_period > len(df):
        logger.warning(f"Percent Rank period {percent_rank_period} is greater than data length ({len(df)}). Skipping Percent Rank calculation.")
        df[f'PR_ROC_{percent_rank_period}'] = pd.NA
    else:
        # Calculate a simple percentile rank of the ROC(1) over the 'percent_rank_period'
        # This will give a value between 0 and 1 (or 0 and 100 if multiplied by 100)
        df[f'PR_ROC_{percent_rank_period}'] = df[f'ROC_{percent_rank_period}'].rolling(window=percent_rank_period).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False
        )
        logger.debug(f"Calculated Percent Rank of ROC({percent_rank_period}).")

    # Combine components for CRSI
    # Ensure all components are not NaN before summing
    df['CRSI'] = (
        df[rsi_price_col].fillna(0) +
        df[f'RSI_U_D_LEN_{up_down_length_period}'].fillna(0) +
        df[f'PR_ROC_{percent_rank_period}'].fillna(0)
    ) / 3

    # Handle cases where components are still NA (e.g., at the beginning of the DataFrame)
    df['CRSI'] = df['CRSI'].replace(0, pd.NA) # Replace 0s that came from fillna if all components were NA.

    logger.info(f"Calculated CRSI with periods: Price RSI {rsi_price_period}, Up/Down Length {up_down_length_period}, Percent Rank {percent_rank_period}.")
    return df

def calculate_all_indicators(df, config):
    """
    Calculates all necessary technical indicators on the given DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data (columns: 'open', 'high', 'low', 'close', 'volume').
        config (dict): The loaded configuration from strategy_params.yaml.
    
    Returns:
        pd.DataFrame: The original DataFrame with indicator columns added.
    """
    if df.empty:
        logger.warning("Attempted to calculate indicators on an empty DataFrame.")
        return df

    # Ensure the DataFrame is a copy to avoid SettingWithCopyWarning
    df_copy = df.copy()

    # --- EMA (Exponential Moving Average) ---
    ema_periods = config.get('ema_periods', {})
    for label, period in ema_periods.items():
        if period is not None:
            col_name = f'EMA_{label}'
            df_copy[col_name] = ta.ema(df_copy['close'], length=period)
            logger.debug(f"Calculated {col_name}")

    # --- RSI (Relative Strength Index) ---
    rsi_period = config.get('rsi_period')
    if rsi_period is not None:
        df_copy['RSI'] = ta.rsi(df_copy['close'], length=rsi_period)
        logger.debug(f"Calculated RSI with period {rsi_period}")

    # --- ADX (Average Directional Index) ---
    adx_period = config.get('adx_period')
    if adx_period is not None:
        adx_data = ta.adx(df_copy['high'], df_copy['low'], df_copy['close'], length=adx_period)
        if adx_data is not None and not adx_data.empty:
            df_copy['ADX'] = adx_data[f'ADX_{adx_period}']
            df_copy['DMP'] = adx_data[f'DMP_{adx_period}']
            df_copy['DMN'] = adx_data[f'DMN_{adx_period}']
            logger.debug(f"Calculated ADX, DMP, DMN with period {adx_period}")
        else:
            logger.warning(f"ADX calculation returned empty or None for period {adx_period}. Check data or period.")

   # --- MACD (Moving Average Convergence Divergence) ---
    macd_fast_period = config.get('macd_fast_period')
    macd_slow_period = config.get('macd_slow_period')
    macd_signal_period = config.get('macd_signal_period')
    if all(p is not None for p in [macd_fast_period, macd_slow_period, macd_signal_period]):
        macd_data = ta.macd(df_copy['close'], fast=macd_fast_period, slow=macd_slow_period, signal=macd_signal_period)
        
        # You can remove or comment out this debugging print statement now:
        # print(f"MACD Data Columns: {macd_data.columns}") 

        if macd_data is not None and not macd_data.empty:
            df_copy['MACD'] = macd_data[f'MACD_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}']
            # CHANGE THIS LINE: 'MACDH_' to 'MACDh_' (lowercase 'h')
            df_copy['MACD_HIST'] = macd_data[f'MACDh_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] 
            df_copy['MACD_SIGNAL'] = macd_data[f'MACDs_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}']
            logger.debug(f"Calculated MACD, MACD_HIST, MACD_SIGNAL with periods {macd_fast_period}, {macd_slow_period}, {macd_signal_period}")
        else:
            logger.warning("MACD calculation returned empty or None. Check data or periods.")

    # --- ATR (Average True Range) ---
    atr_period = config.get('atr_period')
    if atr_period is not None:
        df_copy['ATR'] = ta.atr(df_copy['high'], df_copy['low'], df_copy['close'], length=atr_period)
        logger.debug(f"Calculated ATR with period {atr_period}")

    # --- Volume Average ---
    volume_avg_period = config.get('volume_avg_period')
    if volume_avg_period is not None:
        df_copy['VOLUME_AVG'] = ta.sma(df_copy['volume'], length=volume_avg_period) # Using SMA for volume average
        logger.debug(f"Calculated VOLUME_AVG with period {volume_avg_period}")

    # --- CRSI (Composite RSI) ---
    # This is a custom indicator that might not be directly in pandas_ta.
    # Assuming you have a custom implementation for CRSI or will add it.
    # For now, let's add placeholder if the config is present.
    # If CRSI is complex and uses multiple indicators, its calculation would go here.
    crsi_rsi_price_period = config.get('crsi_rsi_price_period')
    crsi_up_down_length_period = config.get('crsi_up_down_length_period')
    crsi_percent_rank_period = config.get('crsi_percent_rank_period')

    if all(p is not None for p in [crsi_rsi_price_period, crsi_up_down_length_period, crsi_percent_rank_period]):
        try:
            # Placeholder for CRSI calculation. You will need to implement CRSI logic here
            # or ensure it's available through another function or library.
            # Example (this is NOT a real CRSI, just a placeholder):
            # df_copy['CRSI_RSI_PRICE'] = ta.rsi(df_copy['close'], length=crsi_rsi_price_period)
            # df_copy['CRSI_UP_DOWN_LENGTH'] = ta.rsi(df_copy['close'], length=crsi_up_down_length_period)
            # df_copy['CRSI_PERCENT_RANK'] = ta.percent_rank(df_copy['close'], length=crsi_percent_rank_period)
            # If your CRSI is a single value, ensure it's calculated and assigned to df_copy['CRSI']
            logger.debug(f"Placeholder for CRSI calculation added. Ensure actual CRSI logic is implemented.")
        except Exception as e:
            logger.warning(f"Failed to calculate CRSI: {e}")

    logger.debug(f"Finished calculating all indicators for slice up to {df_copy.index[-1]}")
    return df_copy