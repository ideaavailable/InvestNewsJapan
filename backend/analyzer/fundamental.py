"""Fundamental analysis module - comprehensive quality & valuation scoring."""
import logging

logger = logging.getLogger("investnews.fundamental_analyzer")


def analyze_fundamentals(ticker, fund_data, sector_averages=None):
    """Evaluate fundamental quality of a stock with expanded metrics."""
    result = {
        "valuation_score": 0, "quality_score": 0, "growth_score": 0,
        "financial_health_score": 0, "shareholder_return_score": 0,
        "total_fundamental_score": 0, "summary": "",
    }
    if not fund_data:
        return result

    per = fund_data.get("per")
    pbr = fund_data.get("pbr")
    roe = fund_data.get("roe")
    div_yield = fund_data.get("dividend_yield")
    rev_growth = fund_data.get("revenue_growth")
    profit_margin = fund_data.get("profit_margin")
    ev_ebitda = fund_data.get("ev_ebitda")
    roic = fund_data.get("roic")
    fcf_yield = fund_data.get("fcf_yield")
    debt_equity = fund_data.get("debt_equity")
    current_ratio = fund_data.get("current_ratio")
    peg_ratio = fund_data.get("peg_ratio")
    payout_ratio = fund_data.get("payout_ratio")
    eps_growth = fund_data.get("eps_growth")
    op_margin = fund_data.get("operating_margin")

    # ── Valuation Score (0-100) ──
    v_score = 50
    if per is not None:
        if per < 8: v_score += 30
        elif per < 12: v_score += 25
        elif per < 15: v_score += 20
        elif per < 20: v_score += 10
        elif per > 40: v_score -= 20
        elif per > 30: v_score -= 10
    if pbr is not None:
        if pbr < 0.8: v_score += 20
        elif pbr < 1.0: v_score += 15
        elif pbr < 1.5: v_score += 10
        elif pbr > 5.0: v_score -= 10
        elif pbr > 3.0: v_score -= 5
    if ev_ebitda is not None:
        if ev_ebitda < 6: v_score += 10
        elif ev_ebitda < 10: v_score += 5
        elif ev_ebitda > 20: v_score -= 5
    if peg_ratio is not None and peg_ratio > 0:
        if peg_ratio < 1.0: v_score += 10
        elif peg_ratio < 1.5: v_score += 5
        elif peg_ratio > 3.0: v_score -= 5
    result["valuation_score"] = max(0, min(100, v_score))

    # ── Quality Score (0-100) ──
    q_score = 50
    if roe is not None:
        if roe > 20: q_score += 30
        elif roe > 15: q_score += 25
        elif roe > 10: q_score += 15
        elif roe > 5: q_score += 5
        elif roe < 0: q_score -= 20
    if roic is not None:
        if roic > 15: q_score += 15
        elif roic > 10: q_score += 10
        elif roic > 5: q_score += 5
    if profit_margin is not None:
        if profit_margin > 20: q_score += 15
        elif profit_margin > 15: q_score += 10
        elif profit_margin > 10: q_score += 5
        elif profit_margin > 5: q_score += 2
    if op_margin is not None:
        if op_margin > 20: q_score += 5
        elif op_margin > 15: q_score += 3
    result["quality_score"] = max(0, min(100, q_score))

    # ── Growth Score (0-100) ──
    g_score = 50
    if rev_growth is not None:
        if rev_growth > 30: g_score += 30
        elif rev_growth > 20: g_score += 25
        elif rev_growth > 10: g_score += 15
        elif rev_growth > 5: g_score += 10
        elif rev_growth < -10: g_score -= 20
        elif rev_growth < -5: g_score -= 10
    if eps_growth is not None:
        if eps_growth > 30: g_score += 15
        elif eps_growth > 15: g_score += 10
        elif eps_growth > 5: g_score += 5
        elif eps_growth < -10: g_score -= 10
    result["growth_score"] = max(0, min(100, g_score))

    # ── Financial Health Score (0-100) ──
    h_score = 60
    if debt_equity is not None:
        if debt_equity < 0.3: h_score += 20
        elif debt_equity < 0.5: h_score += 15
        elif debt_equity < 1.0: h_score += 5
        elif debt_equity > 2.0: h_score -= 15
        elif debt_equity > 1.5: h_score -= 10
    if current_ratio is not None:
        if current_ratio > 2.0: h_score += 15
        elif current_ratio > 1.5: h_score += 10
        elif current_ratio > 1.0: h_score += 5
        elif current_ratio < 0.8: h_score -= 15
    if fcf_yield is not None:
        if fcf_yield > 8: h_score += 10
        elif fcf_yield > 5: h_score += 5
        elif fcf_yield < 0: h_score -= 10
    result["financial_health_score"] = max(0, min(100, h_score))

    # ── Shareholder Return Score (0-100) ──
    s_score = 50
    if div_yield is not None and 0 < div_yield < 20:
        if div_yield > 4.0: s_score += 25
        elif div_yield > 3.0: s_score += 20
        elif div_yield > 2.0: s_score += 10
        elif div_yield > 1.0: s_score += 5
    if payout_ratio is not None:
        if 20 < payout_ratio < 50: s_score += 15  # Sustainable payout
        elif 50 <= payout_ratio < 70: s_score += 10
        elif payout_ratio > 90: s_score -= 10  # Unsustainable
    result["shareholder_return_score"] = max(0, min(100, s_score))

    # ── Total Fundamental Score ──
    weights = {
        "valuation": 0.25, "quality": 0.25, "growth": 0.20,
        "financial_health": 0.15, "shareholder_return": 0.15,
    }
    total = (
        result["valuation_score"] * weights["valuation"] +
        result["quality_score"] * weights["quality"] +
        result["growth_score"] * weights["growth"] +
        result["financial_health_score"] * weights["financial_health"] +
        result["shareholder_return_score"] * weights["shareholder_return"]
    )
    result["total_fundamental_score"] = round(total, 1)

    # ── Summary ──
    parts = []
    if per: parts.append(f"PER {per:.1f}倍")
    if pbr: parts.append(f"PBR {pbr:.2f}倍")
    if roe: parts.append(f"ROE {roe:.1f}%")
    if roic: parts.append(f"ROIC {roic:.1f}%")
    if div_yield and 0 < div_yield < 20: parts.append(f"配当利回り {div_yield:.1f}%")
    if ev_ebitda: parts.append(f"EV/EBITDA {ev_ebitda:.1f}倍")
    if debt_equity is not None: parts.append(f"D/E {debt_equity:.2f}")
    result["summary"] = "、".join(parts) if parts else "データなし"
    return result
