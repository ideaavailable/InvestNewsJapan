"""Multi-timeframe analysis module.

Analyzes weekly timeframe to provide context for daily trading decisions.
Checks trend alignment between daily and weekly for higher-confidence signals.
"""
import logging
import ta
import pandas as pd

logger = logging.getLogger("investnews.multi_timeframe")


def analyze_weekly(stock_data_daily, params=None):
    """Convert daily data to weekly and analyze for trend context.

    Args:
        stock_data_daily: dict of {ticker: daily_df}
        params: optional parameters override

    Returns:
        dict of {ticker: weekly_analysis}
    """
    from backend.config import MTF_PARAMS
    p = params or MTF_PARAMS
    results = {}
    total = len(stock_data_daily)

    for i, (ticker, df) in enumerate(stock_data_daily.items()):
        if (i + 1) % 30 == 0:
            logger.info(f"Weekly analysis: {i + 1}/{total}")
        try:
            weekly = _resample_to_weekly(df)
            if weekly is None or len(weekly) < 26:
                continue
            analysis = _analyze_weekly_frame(weekly, p)
            if analysis:
                results[ticker] = analysis
        except Exception as e:
            logger.warning(f"Weekly analysis failed for {ticker}: {e}")

    logger.info(f"Weekly analysis completed for {len(results)} stocks")
    return results


def _resample_to_weekly(df):
    """Resample daily OHLCV to weekly."""
    if df is None or df.empty:
        return None
    try:
        weekly = df.resample("W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }).dropna()
        return weekly if len(weekly) >= 10 else None
    except Exception:
        return None


def _analyze_weekly_frame(weekly, p):
    """Run analysis on weekly data."""
    result = {}
    close = weekly["Close"]
    high = weekly["High"]
    low = weekly["Low"]

    # Weekly SMAs
    for period in p.get("weekly_sma_periods", [13, 26]):
        if len(weekly) >= period:
            sma = ta.trend.sma_indicator(close, window=period)
            result[f"w_sma_{period}"] = float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else None
        else:
            result[f"w_sma_{period}"] = None

    # Weekly RSI
    rsi_period = p.get("weekly_rsi_period", 14)
    if len(weekly) >= rsi_period + 5:
        rsi = ta.momentum.RSIIndicator(close, window=rsi_period).rsi()
        result["w_rsi"] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
    else:
        result["w_rsi"] = None

    # Weekly MACD
    if len(weekly) >= 26:
        macd_ind = ta.trend.MACD(close)
        result["w_macd_hist"] = float(macd_ind.macd_diff().iloc[-1]) if not pd.isna(macd_ind.macd_diff().iloc[-1]) else None
    else:
        result["w_macd_hist"] = None

    # Weekly trend
    sma13 = result.get("w_sma_13")
    sma26 = result.get("w_sma_26")
    price = float(close.iloc[-1])

    if sma13 and sma26:
        if price > sma13 > sma26:
            result["w_trend"] = "strong_up"
        elif price > sma13:
            result["w_trend"] = "up"
        elif price < sma13 < sma26:
            result["w_trend"] = "strong_down"
        elif price < sma13:
            result["w_trend"] = "down"
        else:
            result["w_trend"] = "neutral"
    else:
        result["w_trend"] = "unknown"

    # Weekly support/resistance
    recent = weekly.tail(10)
    result["w_support"] = round(float(recent["Low"].nsmallest(3).mean()), 1)
    result["w_resistance"] = round(float(recent["High"].nlargest(3).mean()), 1)

    return result


def get_mtf_alignment(daily_tech, weekly_analysis):
    """Calculate multi-timeframe alignment score.

    Returns:
        dict with alignment info
    """
    if not weekly_analysis:
        return {"mtf_aligned": False, "mtf_score": 0, "mtf_context": "週足データなし"}

    daily_trend = daily_tech.get("trend", "unknown")
    weekly_trend = weekly_analysis.get("w_trend", "unknown")

    # Check trend alignment
    daily_bullish = daily_trend in ("strong_up", "up")
    weekly_bullish = weekly_trend in ("strong_up", "up")
    daily_bearish = daily_trend in ("strong_down", "down")
    weekly_bearish = weekly_trend in ("strong_down", "down")

    aligned = (daily_bullish and weekly_bullish) or (daily_bearish and weekly_bearish)

    score = 0
    context_parts = []

    if aligned:
        score += 5
        if daily_trend.startswith("strong") and weekly_trend.startswith("strong"):
            score += 3
            context_parts.append("日足・週足ともに強いトレンドが一致しており、高確信度のシグナル")
        else:
            context_parts.append(f"日足（{_trend_ja(daily_trend)}）と週足（{_trend_ja(weekly_trend)}）のトレンドが一致")
    else:
        if daily_bullish and weekly_bearish:
            score -= 2
            context_parts.append("日足は上昇だが週足は下降トレンド。短期的なリバウンドの可能性あり、注意が必要")
        elif daily_bearish and weekly_bullish:
            score += 1
            context_parts.append("日足は調整中だが週足は上昇トレンド維持。押し目買いの好機となりうる")
        else:
            context_parts.append("日足と週足のトレンド方向が不一致")

    # Weekly RSI context
    w_rsi = weekly_analysis.get("w_rsi")
    if w_rsi:
        if w_rsi > 70:
            context_parts.append(f"週足RSI {w_rsi:.0f}と過熱感あり")
            score -= 1
        elif w_rsi < 30:
            context_parts.append(f"週足RSI {w_rsi:.0f}と売られすぎ域")
            score += 1

    # Weekly MACD context
    w_macd = weekly_analysis.get("w_macd_hist")
    if w_macd is not None:
        if w_macd > 0 and daily_bullish:
            score += 1
            context_parts.append("週足MACDもプラス推移で上昇基調を裏付け")

    return {
        "mtf_aligned": aligned,
        "mtf_score": max(0, min(8, score)),
        "mtf_context": "。".join(context_parts) + "。" if context_parts else "",
        "w_trend": weekly_trend,
        "w_support": weekly_analysis.get("w_support"),
        "w_resistance": weekly_analysis.get("w_resistance"),
    }


def _trend_ja(trend):
    """Convert trend to Japanese."""
    mapping = {
        "strong_up": "強い上昇", "up": "上昇",
        "strong_down": "強い下降", "down": "下降",
        "neutral": "中立", "unknown": "不明",
    }
    return mapping.get(trend, trend)
