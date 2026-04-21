"""Stock scoring model - expanded multi-factor scoring for daytrade and swing."""
import logging
from backend.config import DAYTRADE_SCORING, SWING_SCORING

logger = logging.getLogger("investnews.scoring")


def score_daytrade(ticker, tech, fund=None, sentiment_score=0, mtf_data=None,
                   sector_score=0, vix_regime=None):
    """Calculate daytrade score (0-100) with expanded factors."""
    weights = DAYTRADE_SCORING
    scores = {}

    # 1. Trend Clarity (15pts)
    adx = tech.get("adx") or 0
    trend = tech.get("trend", "neutral")
    s = 0
    if adx > 30: s += 12
    elif adx > 25: s += 9
    elif adx > 20: s += 6
    if trend in ("strong_up", "strong_down"): s += 3
    elif trend in ("up", "down"): s += 2
    scores["trend_clarity"] = min(s, weights["trend_clarity"])

    # 2. Volume Surge (15pts)
    vol_ratio = tech.get("volume_ratio", 0)
    if vol_ratio >= 3.0: s = 15
    elif vol_ratio >= 2.0: s = 13
    elif vol_ratio >= 1.5: s = 10
    elif vol_ratio >= 1.2: s = 7
    elif vol_ratio >= 1.0: s = 4
    else: s = 0
    scores["volume_surge"] = min(s, weights["volume_surge"])

    # 3. Technical Signals (15pts)
    s = 0
    if tech.get("macd_cross_bullish"): s += 4
    if tech.get("macd_hist") and tech["macd_hist"] > 0: s += 2
    rsi = tech.get("rsi")
    if rsi and 40 <= rsi <= 60: s += 4
    elif rsi and 30 <= rsi < 40: s += 3
    if tech.get("stoch_bullish"): s += 3
    if tech.get("psar_bullish"): s += 1
    if tech.get("above_cloud"): s += 1
    scores["technical_signals"] = min(s, weights["technical_signals"])

    # 4. Volatility (10pts)
    atr_pct = tech.get("atr_pct") or 0
    if 1.0 <= atr_pct <= 3.0: s = 10
    elif 0.5 <= atr_pct < 1.0 or 3.0 < atr_pct <= 5.0: s = 7
    elif atr_pct > 5.0: s = 4
    else: s = 2
    scores["volatility"] = min(s, weights["volatility"])

    # 5. Catalyst (10pts)
    s = int(max(0, min(1, abs(sentiment_score))) * 8)
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
            if rr >= 2.5: s = 10
            elif rr >= 2.0: s = 8
            elif rr >= 1.5: s = 6
            elif rr >= 1.0: s = 4
            else: s = 1
        else:
            s = 5
    else:
        s = 3
    scores["risk_reward"] = min(s, weights["risk_reward"])

    # 7. Multi-Timeframe Alignment (8pts) - NEW
    s = 0
    if mtf_data:
        s = mtf_data.get("mtf_score", 0)
    scores["mtf_alignment"] = min(s, weights["mtf_alignment"])

    # 8. Bollinger Band Squeeze (5pts) - NEW
    s = 0
    if tech.get("ttm_squeeze"): s += 4
    elif tech.get("bb_squeeze"): s += 3
    if tech.get("bb_pctb") and 0.2 < tech["bb_pctb"] < 0.8: s += 1
    scores["bb_squeeze"] = min(s, weights["bb_squeeze"])

    # 9. Candlestick Pattern (5pts) - NEW
    s = 0
    if tech.get("bullish_engulfing"): s += 3
    if tech.get("hammer"): s += 2
    if tech.get("morning_star"): s += 3
    if tech.get("three_white_soldiers"): s += 3
    if tech.get("doji"): s += 1
    scores["candle_pattern"] = min(s, weights["candle_pattern"])

    # 10. Divergence (4pts) - NEW
    s = 0
    if tech.get("bullish_divergence_rsi"): s += 3
    if tech.get("bullish_divergence_macd"): s += 2
    scores["divergence"] = min(s, weights["divergence"])

    # 11. VIX Adjustment (3pts) - NEW
    s = 1  # baseline
    if vix_regime:
        bias = vix_regime.get("score_bias", 0)
        s = max(0, min(3, 1 + bias))
    scores["vix_adjustment"] = min(s, weights["vix_adjustment"])

    total = sum(scores.values())
    return {"total": total, "breakdown": scores, "ticker": ticker}


def score_swing(ticker, tech, fund=None, sentiment_score=0, mtf_data=None,
                sector_score=0, vix_regime=None):
    """Calculate swing trade score (0-100) with expanded factors."""
    weights = SWING_SCORING
    scores = {}
    fund = fund or {}

    # 1. Medium-term Trend (15pts)
    sma25 = tech.get("sma_25")
    sma75 = tech.get("sma_75")
    price = tech.get("current_price", 0)
    s = 0
    if sma25 and sma75:
        if price > sma25 > sma75: s = 15
        elif price > sma25: s = 11
        elif price > sma75: s = 6
        else: s = 2
    scores["medium_term_trend"] = min(s, weights["medium_term_trend"])

    # 2. Technical Signals (12pts)
    s = 0
    if tech.get("above_cloud"): s += 4
    if tech.get("macd_hist") and tech["macd_hist"] > 0: s += 2
    rsi = tech.get("rsi")
    if rsi and 40 <= rsi <= 65: s += 3
    if tech.get("obv_trend") == "up": s += 2
    if tech.get("above_vwap"): s += 1
    scores["technical_signals"] = min(s, weights["technical_signals"])

    # 3. Valuation (12pts)
    per = fund.get("per")
    pbr = fund.get("pbr")
    ev_ebitda = fund.get("ev_ebitda")
    s = 5
    if per:
        if per < 10: s += 4
        elif per < 15: s += 3
        elif per < 20: s += 1
        elif per > 35: s -= 3
    if pbr:
        if pbr < 1.0: s += 3
        elif pbr < 2.0: s += 1
        elif pbr > 5.0: s -= 2
    scores["valuation"] = max(0, min(s, weights["valuation"]))

    # 4. Fundamentals (12pts)
    roe = fund.get("roe")
    s = 4
    if roe:
        if roe > 20: s += 6
        elif roe > 15: s += 5
        elif roe > 10: s += 3
        elif roe > 5: s += 1
    rev_g = fund.get("revenue_growth")
    if rev_g:
        if rev_g > 15: s += 2
        elif rev_g > 5: s += 1
    scores["fundamentals"] = min(s, weights["fundamentals"])

    # 5. Sector Momentum (8pts) - now data-driven
    s = max(0, min(8, int(sector_score * 0.8)))
    scores["sector_momentum"] = min(s, weights["sector_momentum"])

    # 6. Sentiment (8pts)
    s = 4 + int(sentiment_score * 4)
    scores["sentiment"] = max(0, min(s, weights["sentiment"]))

    # 7. Risk/Reward (12pts)
    resistance = tech.get("resistance", price)
    support = tech.get("support", price)
    if price and support and resistance and price > 0:
        potential_gain = resistance - price
        potential_loss = price - support
        if potential_loss > 0:
            rr = potential_gain / potential_loss
            if rr >= 2.5: s = 12
            elif rr >= 2.0: s = 10
            elif rr >= 1.5: s = 7
            elif rr >= 1.0: s = 4
            else: s = 2
        else:
            s = 6
    else:
        s = 4
    scores["risk_reward"] = min(s, weights["risk_reward"])

    # 8. MTF Alignment (8pts) - NEW
    s = 0
    if mtf_data:
        s = mtf_data.get("mtf_score", 0)
    scores["mtf_alignment"] = min(s, weights["mtf_alignment"])

    # 9. Financial Health (5pts) - NEW
    s = 2
    de = fund.get("debt_equity")
    cr = fund.get("current_ratio")
    if de is not None:
        if de < 0.5: s += 2
        elif de > 2.0: s -= 1
    if cr is not None:
        if cr > 1.5: s += 1
        elif cr < 0.8: s -= 1
    scores["financial_health"] = max(0, min(s, weights["financial_health"]))

    # 10. Divergence (4pts) - NEW
    s = 0
    if tech.get("bullish_divergence_rsi"): s += 3
    if tech.get("bullish_divergence_macd"): s += 2
    scores["divergence"] = min(s, weights["divergence"])

    # 11. VIX Adjustment (4pts) - NEW
    s = 2
    if vix_regime:
        bias = vix_regime.get("score_bias", 0)
        s = max(0, min(4, 2 + bias))
    scores["vix_adjustment"] = min(s, weights["vix_adjustment"])

    total = sum(scores.values())
    return {"total": total, "breakdown": scores, "ticker": ticker}
