"""Risk management module.

Implements Kelly Criterion position sizing, VIX-adaptive parameters,
portfolio correlation analysis, and maximum loss scenario calculation.
"""
import logging
import numpy as np

logger = logging.getLogger("investnews.risk_manager")


def calculate_position_sizing(perf_data, vix_value, picks, current_capital):
    """Calculate optimal position sizes using Kelly Criterion with safety factors.

    Args:
        perf_data: performance history
        vix_value: current VIX level
        picks: list of recommended picks
        current_capital: current portfolio capital

    Returns:
        dict with position sizing recommendations
    """
    from backend.config import VIX_REGIMES

    # Determine VIX regime
    regime = _get_vix_regime(vix_value, VIX_REGIMES)

    # Calculate Kelly fraction from historical performance
    kelly_fraction = _calc_kelly_fraction(perf_data)

    # Apply safety factor (Half Kelly is standard practice)
    safe_kelly = kelly_fraction * 0.5

    # Apply VIX multiplier
    position_mult = regime["position_mult"]
    adjusted_fraction = safe_kelly * position_mult

    # Calculate per-pick allocation
    num_picks = len(picks) if picks else 5
    per_pick_fraction = min(adjusted_fraction / num_picks, 0.10)  # Max 10% per stock
    per_pick_amount = int(current_capital * per_pick_fraction)

    # Max loss scenario
    max_loss = _calc_max_loss_scenario(picks, per_pick_amount)

    return {
        "regime": regime["name"],
        "kelly_fraction": round(kelly_fraction * 100, 1),
        "safe_kelly": round(safe_kelly * 100, 1),
        "vix_multiplier": position_mult,
        "per_pick_fraction": round(per_pick_fraction * 100, 1),
        "per_pick_amount": per_pick_amount,
        "total_exposure": round(per_pick_fraction * num_picks * 100, 1),
        "max_loss_scenario": max_loss,
        "recommendation": _size_recommendation(regime, adjusted_fraction),
    }


def check_portfolio_correlation(picks, tech_results):
    """Check correlation/concentration risks in recommended picks.

    Args:
        picks: list of pick dicts
        tech_results: technical analysis results

    Returns:
        dict with correlation warnings
    """
    warnings = []
    sector_count = {}

    for pick in picks:
        sector = pick.get("sector", "不明")
        sector_count[sector] = sector_count.get(sector, 0) + 1

    # Check sector concentration
    for sector, count in sector_count.items():
        if count >= 3:
            warnings.append({
                "type": "sector_concentration",
                "severity": "high",
                "message": f"⚠️ {sector}セクターに{count}銘柄が集中。分散投資の観点からリスクあり。",
            })
        elif count >= 2:
            warnings.append({
                "type": "sector_concentration",
                "severity": "medium",
                "message": f"📋 {sector}セクターに{count}銘柄。適度な分散は維持。",
            })

    # Check for correlated movements
    changes = []
    for pick in picks:
        ticker = f"{pick.get('code', '')}.T"
        tech = tech_results.get(ticker, {})
        change = tech.get("daily_change_pct", 0)
        if change is not None:
            changes.append(change)

    if len(changes) >= 3:
        avg_change = np.mean(changes)
        std_change = np.std(changes)
        if std_change < 0.5 and abs(avg_change) > 1:
            warnings.append({
                "type": "high_correlation",
                "severity": "medium",
                "message": "推奨銘柄の値動きが類似しており、同方向リスクが存在。",
            })

    # Overall risk assessment
    if any(w["severity"] == "high" for w in warnings):
        risk_level = "high"
    elif any(w["severity"] == "medium" for w in warnings):
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "warnings": warnings,
        "sector_distribution": sector_count,
        "risk_level": risk_level,
        "diversification_score": _calc_diversification(sector_count, len(picks)),
    }


def build_risk_dashboard(position_sizing, correlation_check, vix_value, perf_data):
    """Build comprehensive risk dashboard for frontend display.

    Returns:
        dict with all risk management data
    """
    return {
        "position_sizing": position_sizing,
        "portfolio_risk": correlation_check,
        "vix_level": round(vix_value, 1) if vix_value else None,
        "risk_metrics": _calc_risk_metrics(perf_data),
        "guidelines": _generate_risk_guidelines(vix_value, position_sizing),
    }


def _get_vix_regime(vix_value, regimes):
    """Determine current VIX regime."""
    if vix_value is None:
        return {"name": "normal", "threshold": 20, "rr_min": 1.5, "position_mult": 1.0, "score_bias": 0}

    for regime_name in ["low", "normal", "elevated", "high"]:
        r = regimes[regime_name]
        if vix_value < r["threshold"]:
            return {**r, "name": regime_name}

    return {**regimes["high"], "name": "high"}


def _calc_kelly_fraction(perf_data):
    """Calculate Kelly Criterion optimal fraction.

    Kelly% = W - (1-W)/R
    Where W = win rate, R = average win/average loss
    """
    if not perf_data:
        return 0.10  # Default conservative

    total = perf_data.get("total_trades", 0)
    wins = perf_data.get("wins", 0)
    total_profit = perf_data.get("total_profit", 0)
    total_loss = perf_data.get("total_loss", 0)

    if total < 10:
        return 0.10  # Not enough data, be conservative

    win_rate = wins / total if total > 0 else 0.5
    avg_win = total_profit / wins if wins > 0 else 1
    avg_loss = total_loss / (total - wins) if (total - wins) > 0 else 1
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1

    kelly = win_rate - (1 - win_rate) / win_loss_ratio

    # Clamp to reasonable range
    return max(0.02, min(0.25, kelly))


def _calc_max_loss_scenario(picks, per_pick_amount):
    """Calculate worst-case loss scenario."""
    if not picks:
        return {"max_loss": 0, "max_loss_pct": 0}

    total_loss = 0
    for pick in picks:
        entry = pick.get("entry_point", 0) or pick.get("current_price", 0)
        stop = pick.get("stop_loss", 0)
        if entry and stop and entry > 0:
            loss_pct = (entry - stop) / entry
            shares = int(per_pick_amount / entry) if entry > 0 else 0
            total_loss += shares * (entry - stop)

    return {
        "max_loss": round(total_loss),
        "max_loss_pct": round(total_loss / (per_pick_amount * len(picks)) * 100, 2) if picks and per_pick_amount > 0 else 0,
    }


def _calc_diversification(sector_count, total_picks):
    """Calculate diversification score (0-100)."""
    if total_picks <= 1:
        return 50
    unique_sectors = len(sector_count)
    # Perfect diversification = all different sectors
    max_possible = min(total_picks, 10)
    score = (unique_sectors / max_possible) * 100
    # Penalize high concentration
    max_in_one = max(sector_count.values()) if sector_count else 0
    if max_in_one > total_picks * 0.5:
        score *= 0.7
    return round(min(100, score))


def _calc_risk_metrics(perf_data):
    """Calculate risk metrics from performance data."""
    if not perf_data:
        return {}

    daily_results = perf_data.get("daily_results", [])
    if len(daily_results) < 5:
        return {}

    pnls = [d.get("day_pnl", 0) for d in daily_results]
    initial = perf_data.get("initial_capital", 10_000_000)

    # Daily returns
    returns = [p / initial for p in pnls]

    if not returns:
        return {}

    avg_return = np.mean(returns)
    std_return = np.std(returns) if len(returns) > 1 else 0.01

    # Sharpe Ratio (annualized, assuming 245 trading days)
    sharpe = (avg_return / std_return * np.sqrt(245)) if std_return > 0 else 0

    # Sortino Ratio (downside deviation only)
    downside = [r for r in returns if r < 0]
    downside_std = np.std(downside) if len(downside) > 1 else 0.01
    sortino = (avg_return / downside_std * np.sqrt(245)) if downside_std > 0 else 0

    # Calmar Ratio
    max_dd_pct = perf_data.get("max_drawdown", 0) / perf_data.get("peak_capital", initial) if perf_data.get("peak_capital", 0) > 0 else 0.01
    annual_return = avg_return * 245
    calmar = annual_return / max_dd_pct if max_dd_pct > 0 else 0

    return {
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "calmar_ratio": round(calmar, 2),
        "avg_daily_return_pct": round(avg_return * 100, 3),
        "daily_volatility_pct": round(std_return * 100, 3),
        "trading_days": len(returns),
    }


def _size_recommendation(regime, fraction):
    """Generate position sizing recommendation text."""
    name = regime["name"]
    if name == "low":
        return "低ボラティリティ環境。通常よりやや大きめのポジションが可能。トレンドフォロー戦略を推奨。"
    elif name == "normal":
        return "通常のボラティリティ環境。標準的なポジションサイズで選別的にトレード。"
    elif name == "elevated":
        return "⚠️ ボラティリティ上昇中。ポジションサイズを通常の70%に縮小し、損切りを厳格に管理すること。"
    else:
        return "🚨 高ボラティリティ警戒。ポジションサイズを通常の50%以下に縮小。新規スイングは見送り推奨。"


def _generate_risk_guidelines(vix_value, position_sizing):
    """Generate actionable risk management guidelines."""
    guidelines = []
    regime = position_sizing.get("regime", "normal")

    guidelines.append({
        "title": "推奨ポジションサイズ",
        "value": f"1銘柄あたり ¥{position_sizing.get('per_pick_amount', 0):,}",
        "detail": f"全体エクスポージャー: {position_sizing.get('total_exposure', 0)}%",
    })

    if regime in ("elevated", "high"):
        guidelines.append({
            "title": "損切り厳格化",
            "value": "ATR×1.5以内",
            "detail": "損切りラインを超えた銘柄は即座にロスカット",
        })

    guidelines.append({
        "title": "最大損失シナリオ",
        "value": f"¥{position_sizing.get('max_loss_scenario', {}).get('max_loss', 0):,}",
        "detail": f"全銘柄が損切りに到達した場合の想定損失",
    })

    return guidelines
