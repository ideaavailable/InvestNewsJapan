"""Sentiment analysis module - comprehensive multi-factor sentiment scoring."""
import logging
from backend.data_fetcher.news_data import aggregate_sentiment

logger = logging.getLogger("investnews.sentiment_analyzer")


def analyze_market_sentiment(headlines, vix_data=None, market_data=None, tech_results=None):
    """Comprehensive market sentiment analysis combining multiple factors.

    Implements a Fear & Greed style composite indicator using:
    - News sentiment
    - VIX level
    - Market breadth (advance/decline ratio proxy)
    - Volume patterns
    """
    news_sentiment = aggregate_sentiment(headlines)

    # 1. VIX-based sentiment (-0.5 to +0.5)
    vix_sentiment = 0.0
    vix_level = None
    if vix_data and vix_data.get("close"):
        vix = vix_data["close"]
        vix_level = vix
        if vix < 15: vix_sentiment = 0.5
        elif vix < 18: vix_sentiment = 0.3
        elif vix < 20: vix_sentiment = 0.1
        elif vix < 25: vix_sentiment = -0.1
        elif vix < 30: vix_sentiment = -0.3
        else: vix_sentiment = -0.5

    # 2. Market breadth proxy (-0.3 to +0.3)
    breadth_sentiment = 0.0
    advancing = 0
    declining = 0
    if tech_results:
        for ticker, tech in tech_results.items():
            change = tech.get("daily_change_pct", 0)
            if change and change > 0:
                advancing += 1
            elif change and change < 0:
                declining += 1
        total = advancing + declining
        if total > 0:
            ad_ratio = advancing / total
            breadth_sentiment = (ad_ratio - 0.5) * 0.6  # Scale to -0.3 to +0.3

    # 3. Volume pattern sentiment (-0.2 to +0.2)
    volume_sentiment = 0.0
    if tech_results:
        high_vol_up = 0
        high_vol_down = 0
        for ticker, tech in tech_results.items():
            vol_ratio = tech.get("volume_ratio", 1) or 1
            change = tech.get("daily_change_pct", 0) or 0
            if vol_ratio > 1.5:
                if change > 0:
                    high_vol_up += 1
                else:
                    high_vol_down += 1
        if high_vol_up + high_vol_down > 0:
            volume_sentiment = (high_vol_up - high_vol_down) / (high_vol_up + high_vol_down) * 0.2

    # Composite score
    weights = {"news": 0.30, "vix": 0.30, "breadth": 0.25, "volume": 0.15}
    combined = (
        news_sentiment["score"] * weights["news"] +
        vix_sentiment * weights["vix"] +
        breadth_sentiment * weights["breadth"] +
        volume_sentiment * weights["volume"]
    )

    # Fear & Greed classification
    if combined > 0.3:
        overall = "極度の強気"
        fear_greed = "extreme_greed"
        fg_score = min(100, int(50 + combined * 100))
    elif combined > 0.15:
        overall = "強気"
        fear_greed = "greed"
        fg_score = min(85, int(50 + combined * 100))
    elif combined > 0.05:
        overall = "やや強気"
        fear_greed = "slight_greed"
        fg_score = int(50 + combined * 100)
    elif combined < -0.3:
        overall = "極度の弱気"
        fear_greed = "extreme_fear"
        fg_score = max(0, int(50 + combined * 100))
    elif combined < -0.15:
        overall = "弱気"
        fear_greed = "fear"
        fg_score = max(15, int(50 + combined * 100))
    elif combined < -0.05:
        overall = "やや弱気"
        fear_greed = "slight_fear"
        fg_score = int(50 + combined * 100)
    else:
        overall = "中立"
        fear_greed = "neutral"
        fg_score = 50

    return {
        "news_sentiment": news_sentiment,
        "vix_sentiment": round(vix_sentiment, 3),
        "breadth_sentiment": round(breadth_sentiment, 3),
        "volume_sentiment": round(volume_sentiment, 3),
        "combined_score": round(combined, 3),
        "overall": overall,
        "fear_greed_index": fg_score,
        "fear_greed_label": fear_greed,
        "market_breadth": {
            "advancing": advancing,
            "declining": declining,
            "ratio": round(advancing / max(1, advancing + declining), 2),
        },
        "vix_level": vix_level,
    }
