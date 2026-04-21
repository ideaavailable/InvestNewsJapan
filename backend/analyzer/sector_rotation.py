"""Sector rotation analysis module.

Determines the current economic cycle phase and identifies which sectors
are being rotated into/out of. Calculates relative strength for each sector
to detect institutional money flow patterns.
"""
import logging
import numpy as np
from backend.config import STOCK_UNIVERSE, SECTORS, SECTOR_CYCLE

logger = logging.getLogger("investnews.sector_rotation")


def analyze_sector_rotation(tech_results, market_data, macro_data):
    """Comprehensive sector rotation analysis.

    Args:
        tech_results: dict of {ticker: tech_analysis}
        market_data: market index data
        macro_data: macro economic data

    Returns:
        dict with rotation analysis
    """
    # 1. Calculate sector metrics
    sector_metrics = _calc_sector_metrics(tech_results)

    # 2. Determine economic phase
    phase = _estimate_economic_phase(market_data, macro_data)

    # 3. Calculate relative strength
    rs_ranking = _calc_relative_strength(sector_metrics)

    # 4. Identify rotation signals
    rotation_signals = _identify_rotation(sector_metrics, rs_ranking, phase)

    # 5. Build sector scores for stock selection
    sector_scores = _build_sector_scores(rs_ranking, phase)

    return {
        "economic_phase": phase,
        "rs_ranking": rs_ranking,
        "rotation_signals": rotation_signals,
        "sector_scores": sector_scores,
        "sector_metrics": sector_metrics,
    }


def _calc_sector_metrics(tech_results):
    """Calculate aggregate metrics per sector."""
    sector_data = {}
    for code, name, sector in STOCK_UNIVERSE:
        ticker = f"{code}.T"
        if ticker not in tech_results:
            continue
        tech = tech_results[ticker]
        if sector not in sector_data:
            sector_data[sector] = {
                "daily_changes": [], "volume_ratios": [],
                "adx_values": [], "rsi_values": [],
                "trend_scores": [], "stocks": [],
            }
        change = tech.get("daily_change_pct", 0) or 0
        sector_data[sector]["daily_changes"].append(change)
        sector_data[sector]["volume_ratios"].append(tech.get("volume_ratio", 1) or 1)
        if tech.get("adx"):
            sector_data[sector]["adx_values"].append(tech["adx"])
        if tech.get("rsi"):
            sector_data[sector]["rsi_values"].append(tech["rsi"])
        # Trend score: +2 strong_up, +1 up, -1 down, -2 strong_down
        trend_map = {"strong_up": 2, "up": 1, "neutral": 0, "down": -1, "strong_down": -2}
        sector_data[sector]["trend_scores"].append(trend_map.get(tech.get("trend", "neutral"), 0))
        sector_data[sector]["stocks"].append({"code": code, "name": name, "change": change})

    metrics = {}
    for sector, data in sector_data.items():
        if not data["daily_changes"]:
            continue
        metrics[sector] = {
            "avg_change": round(np.mean(data["daily_changes"]), 3),
            "avg_volume_ratio": round(np.mean(data["volume_ratios"]), 2),
            "avg_adx": round(np.mean(data["adx_values"]), 1) if data["adx_values"] else None,
            "avg_rsi": round(np.mean(data["rsi_values"]), 1) if data["rsi_values"] else None,
            "trend_consensus": round(np.mean(data["trend_scores"]), 2),
            "stock_count": len(data["daily_changes"]),
            "top_movers": sorted(data["stocks"], key=lambda x: abs(x["change"]), reverse=True)[:3],
        }
    return metrics


def _estimate_economic_phase(market_data, macro_data):
    """Estimate current economic cycle phase using available data."""
    score = 0
    signals = []

    # VIX-based assessment
    vix = market_data.get("vix", {}).get("close")
    if vix:
        if vix < 15:
            score += 2
            signals.append("VIX低水準→リスクオン")
        elif vix < 20:
            score += 1
        elif vix > 25:
            score -= 2
            signals.append("VIX高水準→リスクオフ")
        elif vix > 20:
            score -= 1

    # US market momentum
    sp_pct = market_data.get("sp500", {}).get("change_pct")
    if sp_pct is not None:
        if sp_pct > 1:
            score += 1
        elif sp_pct < -1:
            score -= 1

    # Yield curve (10Y - 2Y spread)
    us10y = macro_data.get("us_10y_yield")
    us2y = macro_data.get("us_2y_yield")
    if us10y and us2y:
        spread = us10y - us2y
        if spread < 0:
            score -= 2
            signals.append("逆イールド→景気後退懸念")
        elif spread < 0.5:
            score -= 1
            signals.append("イールドカーブフラット化")
        elif spread > 1.5:
            score += 1
            signals.append("正常なイールドカーブ")

    # Commodity signals
    crude_pct = market_data.get("crude_oil", {}).get("change_pct")
    if crude_pct and crude_pct > 2:
        score += 0.5  # inflationary / expansion signal

    # Determine phase
    if score >= 3:
        phase = "expansion"
        desc = "景気拡大期：グロース株・シクリカル株が有利"
    elif score >= 1:
        phase = "recovery"
        desc = "景気回復期：テクノロジー・不動産が先行して回復"
    elif score <= -3:
        phase = "contraction"
        desc = "景気縮小期：ディフェンシブ株・高配当株が有利"
    else:
        phase = "peak"
        desc = "景気ピーク/転換期：素材・エネルギーが堅調、選別が重要"

    return {
        "phase": phase,
        "description": desc,
        "score": round(score, 1),
        "signals": signals,
        "favored_sectors": SECTOR_CYCLE.get(phase, []),
    }


def _calc_relative_strength(sector_metrics):
    """Calculate relative strength ranking of sectors."""
    if not sector_metrics:
        return []

    ranking = []
    for sector, m in sector_metrics.items():
        # Composite RS score: change + trend consensus + volume interest
        rs = (
            m["avg_change"] * 40 +
            m["trend_consensus"] * 30 +
            (m["avg_volume_ratio"] - 1) * 20 +
            ((m["avg_rsi"] - 50) / 50 * 10 if m["avg_rsi"] else 0)
        )
        ranking.append({
            "sector": sector,
            "rs_score": round(rs, 2),
            "avg_change": m["avg_change"],
            "trend_consensus": m["trend_consensus"],
            "avg_volume_ratio": m["avg_volume_ratio"],
        })

    ranking.sort(key=lambda x: x["rs_score"], reverse=True)

    # Add rank
    for i, item in enumerate(ranking):
        item["rank"] = i + 1

    return ranking


def _identify_rotation(sector_metrics, rs_ranking, phase):
    """Identify sector rotation signals."""
    signals = []
    if not rs_ranking:
        return signals

    favored = phase.get("favored_sectors", [])

    # Top rotating INTO
    for item in rs_ranking[:3]:
        sector = item["sector"]
        is_favored = sector in favored
        signals.append({
            "sector": sector,
            "direction": "inflow",
            "strength": "strong" if item["rs_score"] > 10 else "moderate",
            "phase_aligned": is_favored,
            "comment": (
                f"{sector}セクターに資金流入の兆候"
                + ("（景気サイクル的にも追い風）" if is_favored else "")
            ),
        })

    # Bottom rotating OUT OF
    for item in rs_ranking[-2:]:
        sector = item["sector"]
        if item["rs_score"] < -5:
            signals.append({
                "sector": sector,
                "direction": "outflow",
                "strength": "strong" if item["rs_score"] < -10 else "moderate",
                "comment": f"{sector}セクターから資金流出の傾向",
            })

    return signals


def _build_sector_scores(rs_ranking, phase):
    """Build sector scores for use in stock selection scoring."""
    scores = {}
    if not rs_ranking:
        return scores

    total = len(rs_ranking)
    favored = phase.get("favored_sectors", [])

    for item in rs_ranking:
        sector = item["sector"]
        # Base score from RS ranking (0-10)
        rank_score = max(0, (total - item["rank"] + 1) / total * 8)
        # Bonus for phase-aligned sectors
        phase_bonus = 2 if sector in favored else 0
        scores[sector] = round(min(10, rank_score + phase_bonus), 1)

    return scores
