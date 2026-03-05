"""Technical analysis engine using ta library."""
import pandas as pd
import numpy as np
import ta
import logging

logger = logging.getLogger("investnews.technical")


def analyze_stock(df, params=None):
    """Run full technical analysis on a stock's OHLCV DataFrame."""
    if df is None or df.empty or len(df) < 30:
        return None
    from backend.config import TA_PARAMS
    p = params or TA_PARAMS
    result = {}
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # --- Moving Averages ---
    for period in p["sma_periods"]:
        col = f"sma_{period}"
        result[col] = ta.trend.sma_indicator(close, window=period).iloc[-1] if len(df) >= period else None
    for period in p["ema_periods"]:
        col = f"ema_{period}"
        result[col] = ta.trend.ema_indicator(close, window=period).iloc[-1] if len(df) >= period else None

    # --- MACD ---
    macd_ind = ta.trend.MACD(close, window_slow=p["macd_slow"], window_fast=p["macd_fast"],
                             window_sign=p["macd_signal"])
    result["macd"] = macd_ind.macd().iloc[-1]
    result["macd_signal"] = macd_ind.macd_signal().iloc[-1]
    result["macd_hist"] = macd_ind.macd_diff().iloc[-1]
    macd_hist = macd_ind.macd_diff()
    result["macd_cross_bullish"] = bool(len(macd_hist) >= 2 and macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] <= 0)
    result["macd_cross_bearish"] = bool(len(macd_hist) >= 2 and macd_hist.iloc[-1] < 0 and macd_hist.iloc[-2] >= 0)

    # --- RSI ---
    rsi = ta.momentum.RSIIndicator(close, window=p["rsi_period"]).rsi()
    result["rsi"] = rsi.iloc[-1]
    result["rsi_overbought"] = bool(rsi.iloc[-1] > p["rsi_overbought"])
    result["rsi_oversold"] = bool(rsi.iloc[-1] < p["rsi_oversold"])

    # --- ADX ---
    adx_ind = ta.trend.ADXIndicator(high, low, close, window=p["adx_period"])
    result["adx"] = adx_ind.adx().iloc[-1]
    result["plus_di"] = adx_ind.adx_pos().iloc[-1]
    result["minus_di"] = adx_ind.adx_neg().iloc[-1]
    result["strong_trend"] = bool(result["adx"] and result["adx"] > p["adx_strong_trend"])

    # --- Stochastic ---
    stoch = ta.momentum.StochasticOscillator(high, low, close,
                                              window=p["stoch_k_period"], smooth_window=p["stoch_d_period"])
    result["stoch_k"] = stoch.stoch().iloc[-1]
    result["stoch_d"] = stoch.stoch_signal().iloc[-1]
    stoch_k_series = stoch.stoch()
    stoch_d_series = stoch.stoch_signal()
    result["stoch_bullish"] = bool(len(stoch_k_series) >= 2 and
                                   stoch_k_series.iloc[-1] > stoch_d_series.iloc[-1] and
                                   stoch_k_series.iloc[-2] <= stoch_d_series.iloc[-2])

    # --- CCI ---
    result["cci"] = ta.trend.CCIIndicator(high, low, close, window=p["cci_period"]).cci().iloc[-1]

    # --- Williams %R ---
    result["williams_r"] = ta.momentum.WilliamsRIndicator(high, low, close,
                                                           lbp=p["williams_period"]).williams_r().iloc[-1]

    # --- Ichimoku ---
    ichimoku = ta.trend.IchimokuIndicator(high, low, window1=p["ichimoku_tenkan"],
                                           window2=p["ichimoku_kijun"], window3=p["ichimoku_senkou"])
    result["ichimoku_tenkan"] = ichimoku.ichimoku_conversion_line().iloc[-1]
    result["ichimoku_kijun"] = ichimoku.ichimoku_base_line().iloc[-1]
    result["ichimoku_a"] = ichimoku.ichimoku_a().iloc[-1]
    result["ichimoku_b"] = ichimoku.ichimoku_b().iloc[-1]
    result["above_cloud"] = bool(close.iloc[-1] > max(result["ichimoku_a"] or 0, result["ichimoku_b"] or 0))

    # --- ATR ---
    atr = ta.volatility.AverageTrueRange(high, low, close, window=p["atr_period"])
    result["atr"] = atr.average_true_range().iloc[-1]
    result["atr_pct"] = (result["atr"] / close.iloc[-1] * 100) if close.iloc[-1] else None

    # --- Parabolic SAR ---
    try:
        psar = ta.trend.PSARIndicator(high, low, close, step=p["psar_step"], max_step=p["psar_max_step"])
        result["psar"] = psar.psar().iloc[-1]
        result["psar_bullish"] = bool(close.iloc[-1] > result["psar"])
    except Exception:
        result["psar"] = None
        result["psar_bullish"] = None

    # --- OBV ---
    obv_series = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    result["obv"] = obv_series.iloc[-1]
    result["obv_trend"] = "up" if len(obv_series) >= 5 and obv_series.iloc[-1] > obv_series.iloc[-5] else "down"

    # --- Volume Analysis ---
    vol_avg = volume.rolling(window=p["volume_avg_period"]).mean().iloc[-1]
    result["volume_current"] = float(volume.iloc[-1])
    result["volume_avg"] = float(vol_avg) if not pd.isna(vol_avg) else 0
    result["volume_ratio"] = float(volume.iloc[-1] / vol_avg) if vol_avg and not pd.isna(vol_avg) else 0

    # --- Price Info ---
    result["current_price"] = float(close.iloc[-1])
    result["prev_close"] = float(close.iloc[-2]) if len(close) >= 2 else None
    result["daily_change_pct"] = ((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
                                   if len(close) >= 2 and close.iloc[-2] else 0)

    # --- Trend Direction ---
    sma5 = result.get("sma_5")
    sma25 = result.get("sma_25")
    sma75 = result.get("sma_75")
    if sma5 and sma25 and sma75:
        if sma5 > sma25 > sma75:
            result["trend"] = "strong_up"
        elif sma5 > sma25:
            result["trend"] = "up"
        elif sma5 < sma25 < sma75:
            result["trend"] = "strong_down"
        elif sma5 < sma25:
            result["trend"] = "down"
        else:
            result["trend"] = "neutral"
    else:
        result["trend"] = "unknown"

    # --- Support / Resistance ---
    recent = df.tail(20)
    result["recent_high"] = float(recent["High"].max())
    result["recent_low"] = float(recent["Low"].min())
    result["support"] = round(float(recent["Low"].nsmallest(3).mean()), 1)
    result["resistance"] = round(float(recent["High"].nlargest(3).mean()), 1)

    # Clean NaN values
    for k, v in result.items():
        if isinstance(v, float) and (pd.isna(v) or np.isinf(v)):
            result[k] = None
        elif isinstance(v, float):
            result[k] = round(v, 4)
    return result


def analyze_batch(stock_data, params=None):
    """Run technical analysis on multiple stocks."""
    results = {}
    total = len(stock_data)
    for i, (ticker, df) in enumerate(stock_data.items()):
        if (i + 1) % 20 == 0:
            logger.info(f"Technical analysis: {i + 1}/{total}")
        analysis = analyze_stock(df, params)
        if analysis:
            results[ticker] = analysis
    logger.info(f"Technical analysis completed for {len(results)} stocks")
    return results
