"""News data fetcher with simple sentiment scoring."""
import requests
import logging
from backend.config import NEWS_API_KEY, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS

logger = logging.getLogger("investnews.news")


def fetch_news_headlines(query="日本株 マーケット", language="jp", max_results=20):
    """Fetch news headlines. Uses NewsAPI if key is available, otherwise returns empty."""
    headlines = []
    if NEWS_API_KEY:
        try:
            resp = requests.get("https://newsapi.org/v2/everything", params={
                "q": query, "language": language, "sortBy": "publishedAt",
                "pageSize": max_results, "apiKey": NEWS_API_KEY
            }, timeout=10)
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                for art in articles:
                    headlines.append({
                        "title": art.get("title", ""),
                        "source": art.get("source", {}).get("name", ""),
                        "url": art.get("url", ""),
                        "published": art.get("publishedAt", ""),
                    })
        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")
    if not headlines:
        headlines = _generate_market_summary_headlines()
    return headlines


def score_headline_sentiment(title):
    """Score a single headline for sentiment. Returns -1.0 to 1.0."""
    if not title:
        return 0.0
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in title)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in title)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def aggregate_sentiment(headlines):
    """Calculate overall market sentiment from headlines."""
    if not headlines:
        return {"score": 0.0, "label": "中立", "positive_count": 0,
                "negative_count": 0, "neutral_count": 0}
    scores = [score_headline_sentiment(h.get("title", "")) for h in headlines]
    pos_count = sum(1 for s in scores if s > 0)
    neg_count = sum(1 for s in scores if s < 0)
    neutral_count = sum(1 for s in scores if s == 0)
    avg = sum(scores) / len(scores)
    if avg > 0.2:
        label = "強気"
    elif avg > 0.05:
        label = "やや強気"
    elif avg < -0.2:
        label = "弱気"
    elif avg < -0.05:
        label = "やや弱気"
    else:
        label = "中立"
    return {"score": round(avg, 3), "label": label, "positive_count": pos_count,
            "negative_count": neg_count, "neutral_count": neutral_count}


def _generate_market_summary_headlines():
    """Generate placeholder headlines when no API is available."""
    return [
        {"title": "本日の市場概況 - ニュースAPI未設定のためデータなし",
         "source": "InvestNews", "url": "", "published": ""},
    ]
