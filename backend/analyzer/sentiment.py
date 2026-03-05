"""Sentiment analysis module."""
import logging
from backend.data_fetcher.news_data import aggregate_sentiment

logger = logging.getLogger("investnews.sentiment_analyzer")


def analyze_market_sentiment(headlines, vix_data=None):
    """Comprehensive market sentiment analysis."""
    news_sentiment = aggregate_sentiment(headlines)
    vix_sentiment = 0.0
    if vix_data and vix_data.get("close"):
        vix = vix_data["close"]
        if vix < 15: vix_sentiment = 0.5
        elif vix < 20: vix_sentiment = 0.2
        elif vix < 25: vix_sentiment = -0.1
        elif vix < 30: vix_sentiment = -0.3
        else: vix_sentiment = -0.5
    combined = news_sentiment["score"] * 0.6 + vix_sentiment * 0.4
    if combined > 0.2: overall = "強気"
    elif combined > 0.05: overall = "やや強気"
    elif combined < -0.2: overall = "弱気"
    elif combined < -0.05: overall = "やや弱気"
    else: overall = "中立"
    return {
        "news_sentiment": news_sentiment, "vix_sentiment": round(vix_sentiment, 3),
        "combined_score": round(combined, 3), "overall": overall,
    }
