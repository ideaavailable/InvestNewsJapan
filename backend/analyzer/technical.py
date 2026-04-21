"""Technical analysis engine - comprehensive indicator suite.

Includes: SMA/EMA, MACD, RSI, ADX, Stochastic, CCI, Williams%R, Ichimoku,
ATR, Parabolic SAR, OBV, Bollinger Bands, Keltner Channel, MFI, VWAP,
Fibonacci, Pivot Points, Volume Profile, Candlestick Patterns, Divergence Detection.
"""
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
    open_ = df["Open"]

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

    # ============================================================
    # NEW INDICATORS
    # ============================================================

    # --- Bollinger Bands ---
    bb = ta.volatility.BollingerBands(close, window=p["bb_period"], window_dev=p["bb_std"])
    result["bb_upper"] = bb.bollinger_hband().iloc[-1]
    result["bb_middle"] = bb.bollinger_mavg().iloc[-1]
    result["bb_lower"] = bb.bollinger_lband().iloc[-1]
    bb_width = bb.bollinger_wband()
    result["bb_width"] = bb_width.iloc[-1]
    result["bb_pctb"] = bb.bollinger_pband().iloc[-1]  # %B
    # Squeeze detection: BB width below 20-period average of BB width
    if len(bb_width) >= 20:
        avg_width = bb_width.rolling(20).mean().iloc[-1]
        result["bb_squeeze"] = bool(bb_width.iloc[-1] < avg_width * 0.75)
    else:
        result["bb_squeeze"] = False
    # Band walk detection
    result["bb_upper_walk"] = bool(close.iloc[-1] > result["bb_upper"])
    result["bb_lower_walk"] = bool(close.iloc[-1] < result["bb_lower"])

    # --- Keltner Channel ---
    kc = ta.volatility.KeltnerChannel(high, low, close, window=p["keltner_period"],
                                       window_atr=p["atr_period"],
                                       multiplier=p["keltner_atr_mult"])
    result["kc_upper"] = kc.keltner_channel_hband().iloc[-1]
    result["kc_lower"] = kc.keltner_channel_lband().iloc[-1]
    # TTM Squeeze: BB inside Keltner Channel
    result["ttm_squeeze"] = bool(
        result["bb_upper"] and result["kc_upper"] and
        result["bb_upper"] < result["kc_upper"] and
        result["bb_lower"] > result["kc_lower"]
    )

    # --- MFI (Money Flow Index) ---
    mfi = ta.volume.MFIIndicator(high, low, close, volume, window=p["mfi_period"])
    result["mfi"] = mfi.money_flow_index().iloc[-1]
    result["mfi_overbought"] = bool(result["mfi"] and result["mfi"] > 80)
    result["mfi_oversold"] = bool(result["mfi"] and result["mfi"] < 20)

    # --- VWAP (approximation using rolling) ---
    try:
        typical_price = (high + low + close) / 3
        vwap_period = min(p["vwap_period"], len(df))
        cum_tp_vol = (typical_price * volume).rolling(window=vwap_period).sum()
        cum_vol = volume.rolling(window=vwap_period).sum()
        vwap = cum_tp_vol / cum_vol
        result["vwap"] = float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else None
        result["above_vwap"] = bool(result["vwap"] and close.iloc[-1] > result["vwap"])
        result["vwap_deviation"] = float((close.iloc[-1] - result["vwap"]) / result["vwap"] * 100) if result["vwap"] else None
    except Exception:
        result["vwap"] = None
        result["above_vwap"] = None
        result["vwap_deviation"] = None

    # --- Fibonacci Retracement ---
    result.update(_calc_fibonacci(df, p.get("fib_lookback", 60)))

    # --- Pivot Points (Classic) ---
    result.update(_calc_pivot_points(df))

    # --- Volume Profile ---
    result.update(_calc_volume_profile(df, p.get("volume_profile_bins", 20)))

    # --- Candlestick Patterns ---
    result.update(_detect_candle_patterns(df))

    # --- Divergence Detection ---
    result.update(_detect_divergences(close, rsi, macd_ind.macd(), p.get("divergence_lookback", 14)))

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

    # --- Signal Confluence Score (how many signals agree) ---
    bullish_signals = sum([
        bool(result.get("macd_cross_bullish")),
        bool(result.get("macd_hist") and result["macd_hist"] > 0),
        bool(result.get("rsi") and 40 <= result["rsi"] <= 60),
        bool(result.get("above_cloud")),
        bool(result.get("psar_bullish")),
        bool(result.get("stoch_bullish")),
        bool(result.get("above_vwap")),
        bool(result.get("obv_trend") == "up"),
        bool(result.get("mfi") and 40 < result["mfi"] < 60),
        bool(result.get("trend") in ("strong_up", "up")),
        bool(result.get("bullish_divergence_rsi")),
        bool(result.get("bullish_engulfing") or result.get("hammer")),
    ])
    result["signal_confluence"] = bullish_signals
    if bullish_signals >= 8:
        result["confidence"] = "high"
    elif bullish_signals >= 5:
        result["confidence"] = "medium"
    else:
        result["confidence"] = "low"

    # Clean NaN values
    for k, v in result.items():
        if isinstance(v, float) and (pd.isna(v) or np.isinf(v)):
            result[k] = None
        elif isinstance(v, float):
            result[k] = round(v, 4)
    return result


def _calc_fibonacci(df, lookback=60):
    """Calculate Fibonacci retracement levels from recent swing high/low."""
    result = {}
    recent = df.tail(lookback)
    if len(recent) < 10:
        return {"fib_levels": None}
    swing_high = float(recent["High"].max())
    swing_low = float(recent["Low"].min())
    diff = swing_high - swing_low
    if diff <= 0:
        return {"fib_levels": None}
    result["fib_0"] = round(swing_low, 1)
    result["fib_236"] = round(swing_low + diff * 0.236, 1)
    result["fib_382"] = round(swing_low + diff * 0.382, 1)
    result["fib_500"] = round(swing_low + diff * 0.500, 1)
    result["fib_618"] = round(swing_low + diff * 0.618, 1)
    result["fib_786"] = round(swing_low + diff * 0.786, 1)
    result["fib_1000"] = round(swing_high, 1)
    # Identify nearest fib level to current price
    price = float(df["Close"].iloc[-1])
    fib_levels = [result["fib_236"], result["fib_382"], result["fib_500"],
                  result["fib_618"], result["fib_786"]]
    nearest = min(fib_levels, key=lambda x: abs(x - price))
    result["fib_nearest"] = nearest
    result["fib_nearest_dist_pct"] = round(abs(price - nearest) / price * 100, 2)
    result["fib_levels"] = {
        "0%": result["fib_0"], "23.6%": result["fib_236"],
        "38.2%": result["fib_382"], "50%": result["fib_500"],
        "61.8%": result["fib_618"], "78.6%": result["fib_786"],
        "100%": result["fib_1000"],
    }
    return result


def _calc_pivot_points(df):
    """Calculate classic pivot points from previous day."""
    result = {}
    if len(df) < 2:
        return {"pivot": None}
    prev = df.iloc[-2]
    h, l, c = float(prev["High"]), float(prev["Low"]), float(prev["Close"])
    pivot = (h + l + c) / 3
    result["pivot"] = round(pivot, 1)
    result["pivot_r1"] = round(2 * pivot - l, 1)
    result["pivot_r2"] = round(pivot + (h - l), 1)
    result["pivot_r3"] = round(h + 2 * (pivot - l), 1)
    result["pivot_s1"] = round(2 * pivot - h, 1)
    result["pivot_s2"] = round(pivot - (h - l), 1)
    result["pivot_s3"] = round(l - 2 * (h - pivot), 1)
    return result


def _calc_volume_profile(df, bins=20):
    """Calculate volume profile - price levels with highest volume."""
    result = {}
    if len(df) < 20:
        return {"vol_poc": None}
    recent = df.tail(60)
    price_min = float(recent["Low"].min())
    price_max = float(recent["High"].max())
    if price_max <= price_min:
        return {"vol_poc": None}
    bin_edges = np.linspace(price_min, price_max, bins + 1)
    vol_at_price = np.zeros(bins)
    for _, row in recent.iterrows():
        low_val, high_val, vol_val = float(row["Low"]), float(row["High"]), float(row["Volume"])
        for j in range(bins):
            if bin_edges[j + 1] >= low_val and bin_edges[j] <= high_val:
                overlap = min(high_val, bin_edges[j + 1]) - max(low_val, bin_edges[j])
                total_range = high_val - low_val if high_val > low_val else 1
                vol_at_price[j] += vol_val * (overlap / total_range)
    poc_idx = np.argmax(vol_at_price)
    result["vol_poc"] = round((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2, 1)
    # Value Area (70% of volume)
    total_vol = vol_at_price.sum()
    if total_vol > 0:
        sorted_idx = np.argsort(vol_at_price)[::-1]
        cum_vol = 0
        va_indices = []
        for idx in sorted_idx:
            cum_vol += vol_at_price[idx]
            va_indices.append(idx)
            if cum_vol >= total_vol * 0.7:
                break
        va_low_idx = min(va_indices)
        va_high_idx = max(va_indices)
        result["vol_va_high"] = round(bin_edges[va_high_idx + 1], 1)
        result["vol_va_low"] = round(bin_edges[va_low_idx], 1)
    else:
        result["vol_va_high"] = None
        result["vol_va_low"] = None
    return result


def _detect_candle_patterns(df):
    """Detect common candlestick patterns."""
    result = {
        "bullish_engulfing": False, "bearish_engulfing": False,
        "hammer": False, "inverted_hammer": False,
        "doji": False, "morning_star": False, "evening_star": False,
        "three_white_soldiers": False, "three_black_crows": False,
    }
    if len(df) < 3:
        return result
    c0 = df.iloc[-1]  # current
    c1 = df.iloc[-2]  # previous
    c2 = df.iloc[-3]  # two ago

    o0, h0, l0, cl0 = float(c0["Open"]), float(c0["High"]), float(c0["Low"]), float(c0["Close"])
    o1, h1, l1, cl1 = float(c1["Open"]), float(c1["High"]), float(c1["Low"]), float(c1["Close"])
    o2, h2, l2, cl2 = float(c2["Open"]), float(c2["High"]), float(c2["Low"]), float(c2["Close"])

    body0 = abs(cl0 - o0)
    body1 = abs(cl1 - o1)
    range0 = h0 - l0 if h0 > l0 else 0.01
    range1 = h1 - l1 if h1 > l1 else 0.01

    # Bullish Engulfing
    if cl1 < o1 and cl0 > o0 and o0 <= cl1 and cl0 >= o1:
        result["bullish_engulfing"] = True

    # Bearish Engulfing
    if cl1 > o1 and cl0 < o0 and o0 >= cl1 and cl0 <= o1:
        result["bearish_engulfing"] = True

    # Hammer (long lower shadow, small body at top)
    lower_shadow0 = min(o0, cl0) - l0
    upper_shadow0 = h0 - max(o0, cl0)
    if body0 > 0 and lower_shadow0 >= body0 * 2 and upper_shadow0 < body0 * 0.5:
        result["hammer"] = True

    # Inverted Hammer
    if body0 > 0 and upper_shadow0 >= body0 * 2 and lower_shadow0 < body0 * 0.5:
        result["inverted_hammer"] = True

    # Doji
    if body0 < range0 * 0.1:
        result["doji"] = True

    # Morning Star (3-candle bullish reversal)
    body2 = abs(cl2 - o2)
    if cl2 < o2 and body1 < body2 * 0.3 and cl0 > o0 and cl0 > (o2 + cl2) / 2:
        result["morning_star"] = True

    # Evening Star (3-candle bearish reversal)
    if cl2 > o2 and body1 < body2 * 0.3 and cl0 < o0 and cl0 < (o2 + cl2) / 2:
        result["evening_star"] = True

    # Three White Soldiers
    if len(df) >= 3:
        if (cl2 > o2 and cl1 > o1 and cl0 > o0 and
            cl0 > cl1 > cl2 and o0 > o1 > o2):
            result["three_white_soldiers"] = True

    # Three Black Crows
    if len(df) >= 3:
        if (cl2 < o2 and cl1 < o1 and cl0 < o0 and
            cl0 < cl1 < cl2 and o0 < o1 < o2):
            result["three_black_crows"] = True

    return result


def _detect_divergences(close, rsi_series, macd_series, lookback=14):
    """Detect RSI and MACD divergences."""
    result = {
        "bullish_divergence_rsi": False, "bearish_divergence_rsi": False,
        "bullish_divergence_macd": False, "bearish_divergence_macd": False,
    }
    if len(close) < lookback + 5 or len(rsi_series) < lookback + 5:
        return result

    try:
        recent_close = close.iloc[-lookback:]
        recent_rsi = rsi_series.iloc[-lookback:]
        recent_macd = macd_series.iloc[-lookback:]

        # Find local minima/maxima in price
        price_vals = recent_close.values
        rsi_vals = recent_rsi.values
        macd_vals = recent_macd.values

        # Bullish divergence: price makes lower low, indicator makes higher low
        half = lookback // 2
        price_first_half_min = np.min(price_vals[:half])
        price_second_half_min = np.min(price_vals[half:])
        rsi_first_half_min = np.min(rsi_vals[:half])
        rsi_second_half_min = np.min(rsi_vals[half:])
        macd_first_half_min = np.min(macd_vals[:half])
        macd_second_half_min = np.min(macd_vals[half:])

        if price_second_half_min < price_first_half_min and rsi_second_half_min > rsi_first_half_min:
            result["bullish_divergence_rsi"] = True
        if price_second_half_min < price_first_half_min and macd_second_half_min > macd_first_half_min:
            result["bullish_divergence_macd"] = True

        # Bearish divergence: price makes higher high, indicator makes lower high
        price_first_half_max = np.max(price_vals[:half])
        price_second_half_max = np.max(price_vals[half:])
        rsi_first_half_max = np.max(rsi_vals[:half])
        rsi_second_half_max = np.max(rsi_vals[half:])
        macd_first_half_max = np.max(macd_vals[:half])
        macd_second_half_max = np.max(macd_vals[half:])

        if price_second_half_max > price_first_half_max and rsi_second_half_max < rsi_first_half_max:
            result["bearish_divergence_rsi"] = True
        if price_second_half_max > price_first_half_max and macd_second_half_max < macd_first_half_max:
            result["bearish_divergence_macd"] = True
    except Exception:
        pass

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
