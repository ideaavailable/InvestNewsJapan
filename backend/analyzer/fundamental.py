"""Fundamental analysis module."""
import logging

logger = logging.getLogger("investnews.fundamental_analyzer")


def analyze_fundamentals(ticker, fund_data, sector_averages=None):
    """Evaluate fundamental quality of a stock."""
    result = {"valuation_score": 0, "quality_score": 0, "growth_score": 0, "summary": ""}
    if not fund_data:
        return result

    per = fund_data.get("per")
    pbr = fund_data.get("pbr")
    roe = fund_data.get("roe")
    div_yield = fund_data.get("dividend_yield")
    rev_growth = fund_data.get("revenue_growth")
    profit_margin = fund_data.get("profit_margin")

    # Valuation Score (0-100)
    v_score = 50
    if per is not None:
        if per < 10: v_score += 30
        elif per < 15: v_score += 20
        elif per < 20: v_score += 10
        elif per > 40: v_score -= 20
    if pbr is not None:
        if pbr < 1.0: v_score += 20
        elif pbr < 1.5: v_score += 10
        elif pbr > 5.0: v_score -= 10
    result["valuation_score"] = max(0, min(100, v_score))

    # Quality Score (0-100)
    q_score = 50
    if roe is not None:
        if roe > 15: q_score += 25
        elif roe > 10: q_score += 15
        elif roe > 5: q_score += 5
        elif roe < 0: q_score -= 20
    if profit_margin is not None:
        if profit_margin > 15: q_score += 15
        elif profit_margin > 10: q_score += 10
        elif profit_margin > 5: q_score += 5
    result["quality_score"] = max(0, min(100, q_score))

    # Growth Score (0-100)
    g_score = 50
    if rev_growth is not None:
        if rev_growth > 20: g_score += 30
        elif rev_growth > 10: g_score += 20
        elif rev_growth > 5: g_score += 10
        elif rev_growth < -5: g_score -= 15
    result["growth_score"] = max(0, min(100, g_score))

    # Summary
    parts = []
    if per: parts.append(f"PER {per:.1f}倍")
    if pbr: parts.append(f"PBR {pbr:.2f}倍")
    if roe: parts.append(f"ROE {roe:.1f}%")
    if div_yield: parts.append(f"配当利回り {div_yield:.1f}%")
    result["summary"] = "、".join(parts) if parts else "データなし"
    return result
