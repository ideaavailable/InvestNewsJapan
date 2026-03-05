"""Macro environment analysis module."""
import logging

logger = logging.getLogger("investnews.macro_analyzer")


def analyze_macro_environment(market_data, macro_data):
    """Analyze the macro environment and its impact on Japanese equities."""
    analysis = {
        "summary": "", "key_factors": [], "risk_level": "moderate",
        "market_forecast": {"direction": "neutral", "confidence": "low"},
        "sector_implications": {},
    }
    factors = []

    # US market impact
    sp500 = market_data.get("sp500", {})
    nasdaq = market_data.get("nasdaq", {})
    if sp500.get("change_pct") is not None:
        pct = sp500["change_pct"]
        if pct > 1.0:
            factors.append({"factor": "米国市場", "impact": "positive",
                           "detail": f"S&P500が{pct:+.2f}%と大幅上昇。日本株にもプラスの影響が期待される。"})
        elif pct < -1.0:
            factors.append({"factor": "米国市場", "impact": "negative",
                           "detail": f"S&P500が{pct:+.2f}%と大幅下落。日本株も軟調な展開が予想される。"})
        else:
            factors.append({"factor": "米国市場", "impact": "neutral",
                           "detail": f"S&P500は{pct:+.2f}%と小動き。"})

    # Forex impact
    usdjpy = market_data.get("usdjpy", {})
    if usdjpy.get("close"):
        rate = usdjpy["close"]
        if rate > 155:
            factors.append({"factor": "為替", "impact": "mixed",
                           "detail": f"USD/JPY {rate:.2f}円。円安は輸出企業にプラスだが、過度な円安は警戒感も。"})
        elif rate > 145:
            factors.append({"factor": "為替", "impact": "positive",
                           "detail": f"USD/JPY {rate:.2f}円。適度な円安水準で輸出企業に追い風。"})
        elif rate < 135:
            factors.append({"factor": "為替", "impact": "negative",
                           "detail": f"USD/JPY {rate:.2f}円。円高進行は輸出企業の収益を圧迫。"})

    # VIX impact
    vix = market_data.get("vix", {})
    if vix.get("close"):
        v = vix["close"]
        if v < 15:
            analysis["risk_level"] = "low"
        elif v < 20:
            analysis["risk_level"] = "moderate"
        elif v < 30:
            analysis["risk_level"] = "elevated"
            factors.append({"factor": "VIX", "impact": "negative",
                           "detail": f"VIX {v:.1f}とやや高水準。リスク管理を慎重に。"})
        else:
            analysis["risk_level"] = "high"
            factors.append({"factor": "VIX", "impact": "negative",
                           "detail": f"VIX {v:.1f}と高水準。市場の不安定さに警戒が必要。"})

    # CME Nikkei Futures
    cme = market_data.get("cme_nikkei", {})
    nikkei = market_data.get("nikkei225", {})
    if cme.get("close") and nikkei.get("close"):
        diff = cme["close"] - nikkei["close"]
        diff_pct = (diff / nikkei["close"]) * 100
        if diff_pct > 0.3:
            analysis["market_forecast"]["direction"] = "bullish"
            factors.append({"factor": "CME日経先物", "impact": "positive",
                           "detail": f"CME日経先物は大証比{diff:+.0f}円（{diff_pct:+.2f}%）。高寄りが予想される。"})
        elif diff_pct < -0.3:
            analysis["market_forecast"]["direction"] = "bearish"
            factors.append({"factor": "CME日経先物", "impact": "negative",
                           "detail": f"CME日経先物は大証比{diff:+.0f}円（{diff_pct:+.2f}%）。安寄りが予想される。"})

    analysis["key_factors"] = factors

    # Generate summary
    pos = sum(1 for f in factors if f["impact"] == "positive")
    neg = sum(1 for f in factors if f["impact"] == "negative")
    if pos > neg:
        analysis["summary"] = "マクロ環境はおおむねポジティブ。リスクオン姿勢での取引が可能。"
        analysis["market_forecast"]["confidence"] = "moderate"
    elif neg > pos:
        analysis["summary"] = "マクロ環境に懸念材料あり。慎重なポジション管理を推奨。"
        analysis["market_forecast"]["confidence"] = "moderate"
    else:
        analysis["summary"] = "マクロ環境は混在。個別銘柄の選別が重要な局面。"

    return analysis
