"""Stock scoring model for daytrade and swing recommendations."""
import logging
from backend.config import DAYTRADE_SCORING, SWING_SCORING

logger = logging.getLogger("investnews.scoring")


def score_daytrade(ticker, tech, fund=None, sentiment_score=0):
    """Calculate daytrade score (0-100)."""
    weights = DAYTRADE_SCORING
    scores = {}

    # 1. Trend Clarity (20pts)
    adx = tech.get("adx") or 0
    trend = tech.get("trend", "neutral")
    s = 0
    if adx > 30: s += 15
    elif adx > 25: s += 12
    elif adx > 20: s += 8
    if trend in ("strong_up", "strong_down"): s += 5
    elif trend in ("up", "down"): s += 3
    scores["trend_clarity"] = min(s, weights["trend_clarity"])

    # 2. Volume Surge (20pts)
    vol_ratio = tech.get("volume_ratio", 0)
    if vol_ratio >= 3.0: s = 20
    elif vol_ratio >= 2.0: s = 16
    elif vol_ratio >= 1.5: s = 12
    elif vol_ratio >= 1.2: s = 8
    elif vol_ratio >= 1.0: s = 4
    else: s = 0
    scores["volume_surge"] = min(s, weights["volume_surge"])

    # 3. Technical Signals (20pts)
    s = 0
    if tech.get("macd_cross_bullish"): s += 5
    if tech.get("macd_hist") and tech["macd_hist"] > 0: s += 2
    rsi = tech.get("rsi")
    if rsi and 40 <= rsi <= 60: s += 5
    elif rsi and 30 <= rsi < 40: s += 4
    if tech.get("stoch_bullish"): s += 4
    if tech.get("psar_bullish"): s += 2
    if tech.get("above_cloud"): s += 2
    scores["technical_signals"] = min(s, weights["technical_signals"])

    # 4. Volatility (15pts)
    atr_pct = tech.get("atr_pct") or 0
    if 1.0 <= atr_pct <= 3.0: s = 15
    elif 0.5 <= atr_pct < 1.0 or 3.0 < atr_pct <= 5.0: s = 10
    elif atr_pct > 5.0: s = 5
    else: s = 3
    scores["volatility"] = min(s, weights["volatility"])

    # 5. Catalyst (15pts)
    s = int(max(0, min(1, abs(sentiment_score))) * 10)
    scores["catalyst"] = min(s, weights["catalyst"])

    # 6. Risk/Reward (10pts)
    price = tech.get("current_price", 0)
    resistance = tech.get("resistance", price)
    support = tech.get("support", price)
    if price and support and resistance and price > 0:
        potential_gain = resistance - price
        potential_loss = price - support
        if potential_loss > 0:
            rr = potential_gain / potential_loss
            if rr >= 2.0: s = 10
            elif rr >= 1.5: s = 7
            elif rr >= 1.0: s = 4
            else: s = 1
        else:
            s = 5
    else:
        s = 3
    scores["risk_reward"] = min(s, weights["risk_reward"])

    total = sum(scores.values())
    return {"total": total, "breakdown": scores, "ticker": ticker}


def score_swing(ticker, tech, fund=None, sentiment_score=0):
    """Calculate swing trade score (0-100)."""
    weights = SWING_SCORING
    scores = {}
    fund = fund or {}

    # 1. Medium-term Trend (20pts)
    sma25 = tech.get("sma_25")
    sma75 = tech.get("sma_75")
    price = tech.get("current_price", 0)
    s = 0
    if sma25 and sma75:
        if price > sma25 > sma75: s = 20
        elif price > sma25: s = 14
        elif price > sma75: s = 8
        else: s = 3
    scores["medium_term_trend"] = min(s, weights["medium_term_trend"])

    # 2. Technical Signals (15pts)
    s = 0
    if tech.get("above_cloud"): s += 5
    if tech.get("macd_hist") and tech["macd_hist"] > 0: s += 3
    rsi = tech.get("rsi")
    if rsi and 40 <= rsi <= 65: s += 4
    if tech.get("obv_trend") == "up": s += 3
    scores["technical_signals"] = min(s, weights["technical_signals"])

    # 3. Valuation (15pts)
    per = fund.get("per")
    pbr = fund.get("pbr")
    s = 7
    if per:
        if per < 12: s += 4
        elif per < 18: s += 2
        elif per > 35: s -= 3
    if pbr:
        if pbr < 1.0: s += 4
        elif pbr < 2.0: s += 2
        elif pbr > 5.0: s -= 2
    scores["valuation"] = max(0, min(s, weights["valuation"]))

    # 4. Fundamentals (15pts)
    roe = fund.get("roe")
    s = 5
    if roe:
        if roe > 15: s += 8
        elif roe > 10: s += 5
        elif roe > 5: s += 2
    rev_g = fund.get("revenue_growth")
    if rev_g:
        if rev_g > 10: s += 2
    scores["fundamentals"] = min(s, weights["fundamentals"])

    # 5. Sector Momentum (10pts)
    scores["sector_momentum"] = 5  # Baseline

    # 6. Sentiment (10pts)
    s = 5 + int(sentiment_score * 5)
    scores["sentiment"] = max(0, min(s, weights["sentiment"]))

    # 7. Risk/Reward (15pts)
    resistance = tech.get("resistance", price)
    support = tech.get("support", price)
    if price and support and resistance and price > 0:
        potential_gain = resistance - price
        potential_loss = price - support
        if potential_loss > 0:
            rr = potential_gain / potential_loss
            if rr >= 2.5: s = 15
            elif rr >= 2.0: s = 12
            elif rr >= 1.5: s = 8
            elif rr >= 1.0: s = 5
            else: s = 2
        else:
            s = 7
    else:
        s = 5
    scores["risk_reward"] = min(s, weights["risk_reward"])

    total = sum(scores.values())
    return {"total": total, "breakdown": scores, "ticker": ticker}
