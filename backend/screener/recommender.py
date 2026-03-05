"""Final stock recommender - selects top picks from scored candidates."""
import logging
from backend.config import DAYTRADE_PICKS_COUNT, SWING_PICKS_COUNT, get_stock_info
from backend.screener.universe import filter_by_liquidity, filter_by_technical
from backend.screener.scoring import score_daytrade, score_swing

logger = logging.getLogger("investnews.recommender")


def select_daytrade_picks(tech_results, fund_results, sentiment_score=0, count=None):
    """Select top daytrade candidates."""
    count = count or DAYTRADE_PICKS_COUNT
    candidates = filter_by_liquidity(tech_results, fund_results, mode="daytrade")
    candidates = filter_by_technical(candidates, tech_results, mode="daytrade")
    scored = []
    for ticker in candidates:
        tech = tech_results.get(ticker, {})
        fund = fund_results.get(ticker, {})
        score = score_daytrade(ticker, tech, fund, sentiment_score)
        score["tech"] = tech
        score["fund"] = fund
        scored.append(score)
    scored.sort(key=lambda x: x["total"], reverse=True)
    picks = scored[:count]
    return [_format_daytrade_pick(p) for p in picks]


def select_swing_picks(tech_results, fund_results, sentiment_score=0, count=None):
    """Select top swing trade candidates."""
    count = count or SWING_PICKS_COUNT
    candidates = filter_by_liquidity(tech_results, fund_results, mode="swing")
    candidates = filter_by_technical(candidates, tech_results, mode="swing")
    scored = []
    for ticker in candidates:
        tech = tech_results.get(ticker, {})
        fund = fund_results.get(ticker, {})
        score = score_swing(ticker, tech, fund, sentiment_score)
        score["tech"] = tech
        score["fund"] = fund
        scored.append(score)
    scored.sort(key=lambda x: x["total"], reverse=True)
    picks = scored[:count]
    return [_format_swing_pick(p) for p in picks]


def _format_daytrade_pick(pick):
    """Format a daytrade pick for the report."""
    ticker = pick["ticker"]
    code = ticker.replace(".T", "")
    info = get_stock_info(code) or {"code": code, "name": code, "sector": "不明"}
    tech = pick.get("tech", {})
    price = tech.get("current_price", 0)
    atr = tech.get("atr", 0) or 0
    support = tech.get("support", price)
    resistance = tech.get("resistance", price)
    stop_loss = round(support - atr * 0.5, 1) if support and atr else round(price * 0.97, 1)
    target = round(resistance + atr * 0.3, 1) if resistance and atr else round(price * 1.03, 1)
    rr = round((target - price) / (price - stop_loss), 2) if price > stop_loss else 0

    rationale_parts = []
    if tech.get("macd_cross_bullish"): rationale_parts.append("MACDゴールデンクロス")
    if tech.get("above_cloud"): rationale_parts.append("一目均衡表の雲上")
    if tech.get("psar_bullish"): rationale_parts.append("パラボリックSAR買いシグナル")
    trend = tech.get("trend", "")
    if trend == "strong_up": rationale_parts.append("強い上昇トレンド（MA完全順配列）")
    elif trend == "up": rationale_parts.append("上昇トレンド")
    rsi = tech.get("rsi")
    if rsi: rationale_parts.append(f"RSI {rsi:.0f}")
    vol = tech.get("volume_ratio", 0)
    if vol > 1.5: rationale_parts.append(f"出来高急増（平均比{vol:.1f}倍）")

    return {
        "code": info["code"], "name": info["name"], "sector": info["sector"],
        "score": pick["total"], "score_breakdown": pick["breakdown"],
        "entry_point": round(price, 1), "target": target, "stop_loss": stop_loss,
        "risk_reward_ratio": rr,
        "rationale": {
            "technical": "、".join(rationale_parts) if rationale_parts else "テクニカル指標総合判断",
            "catalyst": "",
            "volume_analysis": f"直近出来高: {tech.get('volume_current', 0):,.0f}株（{tech.get('volume_ratio', 0):.1f}倍）",
        },
        "current_price": round(price, 1),
        "atr": round(atr, 2) if atr else None,
    }


def _format_swing_pick(pick):
    """Format a swing trade pick for the report."""
    ticker = pick["ticker"]
    code = ticker.replace(".T", "")
    info = get_stock_info(code) or {"code": code, "name": code, "sector": "不明"}
    tech = pick.get("tech", {})
    fund = pick.get("fund", {})
    price = tech.get("current_price", 0)
    atr = tech.get("atr", 0) or 0
    support = tech.get("support", price)
    resistance = tech.get("resistance", price)
    stop_loss = round(support - atr, 1) if support and atr else round(price * 0.95, 1)
    target = round(resistance + atr * 0.8, 1) if resistance and atr else round(price * 1.07, 1)
    rr = round((target - price) / (price - stop_loss), 2) if price > stop_loss else 0

    tech_parts = []
    if tech.get("above_cloud"): tech_parts.append("一目均衡表の雲上で推移")
    trend = tech.get("trend", "")
    if "up" in trend: tech_parts.append("中期上昇トレンド")
    if tech.get("obv_trend") == "up": tech_parts.append("OBV上昇（買い蓄積）")
    if tech.get("macd_hist") and tech["macd_hist"] > 0: tech_parts.append("MACDヒストグラムプラス")

    fund_parts = []
    per = fund.get("per")
    pbr = fund.get("pbr")
    roe = fund.get("roe")
    if per: fund_parts.append(f"PER {per:.1f}倍")
    if pbr: fund_parts.append(f"PBR {pbr:.2f}倍")
    if roe: fund_parts.append(f"ROE {roe:.1f}%")
    div_y = fund.get("dividend_yield")
    if div_y: fund_parts.append(f"配当利回り{div_y:.1f}%")

    return {
        "code": info["code"], "name": info["name"], "sector": info["sector"],
        "score": pick["total"], "score_breakdown": pick["breakdown"],
        "holding_period": "5〜10営業日",
        "entry_point": round(price, 1), "target": target, "stop_loss": stop_loss,
        "risk_reward_ratio": rr,
        "rationale": {
            "technical": "、".join(tech_parts) if tech_parts else "テクニカル指標総合判断",
            "fundamental": "、".join(fund_parts) if fund_parts else "データ取得中",
            "catalyst": "",
        },
        "fundamentals": {
            "per": per, "pbr": pbr, "roe": roe,
            "dividend_yield": div_y,
        },
        "current_price": round(price, 1),
    }
