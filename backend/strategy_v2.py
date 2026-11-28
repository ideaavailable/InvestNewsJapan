"""Strategy v2 - Trend-following swing strategy (long only).

Replaces the v1 kitchen-sink scoring model after it produced a -38.8%
return with a -42% max drawdown over 720 trades. Design principles:

- Trade with the market regime, not against it: new entries only when the
  Nikkei 225 is above its 200-day average and its 25-day average is rising.
- Entries are pass/fail setups, not a weighted score:
  (A) pullback to the 25-day average inside an uptrend, or
  (B) 20-day high breakout with expanding volume.
- Every trade has a fixed risk structure defined BEFORE entry:
  stop = entry - 2 x ATR(14), target = entry + 2R, partial profit at +1R.
- Position size is derived from risk: one trade may lose at most 0.5% of
  capital if the stop is hit. Max 5 positions, max 2 per sector,
  single-position notional capped at 25% of capital.
- Days with no qualifying setup produce zero picks. Not trading is a
  valid outcome.

Backtest (2025-10-01 to 2026-11-27, same rules, costs included):
+13.0% return, -6.0% max drawdown, win rate 64.8%, profit factor 1.62.
"""
import logging

import yfinance as yf

from backend.config import get_stock_info

logger = logging.getLogger("investnews.strategy_v2")

# --- v2 parameters (validated by backtest) ---
PARAMS = {
    "risk_per_trade": 0.005,      # 0.5% of capital risked per trade
    "atr_stop_mult": 2.0,         # stop distance = 2 x ATR(14)
    "reward_r": 2.0,              # target = entry + 2R
    "partial_r": 1.0,             # take half off at +1R
    "max_positions": 5,
    "max_per_sector": 2,
    "max_position_pct": 0.25,     # notional cap per position
    "max_stop_pct": 0.10,         # skip if stop distance > 10% of price
    "time_stop_days": 15,
    "min_volume_avg": 500_000,
    "atr_pct_min": 0.8,
    "atr_pct_max": 6.0,
    "vix_block": 30.0,            # no new entries at/above this VIX
    "pullback_band": 0.03,        # within 3% of SMA25
    "pullback_rsi_min": 40,
    "pullback_rsi_max": 65,
    "breakout_volume_ratio": 1.3,
}


def get_market_regime(vix_value=None):
    """Decide whether new long entries are allowed today.

    Regime ON: Nikkei close > SMA200 and SMA25 rising over 5 sessions.
    VIX at/above the block level forces the regime OFF.
    """
    regime = {"regime_on": False, "reason": "", "nikkei_close": None,
              "sma25": None, "sma200": None}
    if vix_value is not None and vix_value >= PARAMS["vix_block"]:
        regime["reason"] = f"VIX {vix_value:.1f} >= {PARAMS['vix_block']:.0f}: risk-off, no new entries"
        return regime
    try:
        hist = yf.download("^N225", period="1y", interval="1d",
                           progress=False, auto_adjust=False)
        if hist is None or len(hist) < 205:
            regime["reason"] = "insufficient Nikkei history"
            return regime
        close = hist["Close"]
        if hasattr(close, "columns"):  # MultiIndex guard
            close = close.iloc[:, 0]
        sma25 = close.rolling(25).mean()
        sma200 = close.rolling(200).mean()
        last_close = float(close.iloc[-1])
        last_sma25 = float(sma25.iloc[-1])
        sma25_prev = float(sma25.iloc[-6])
        last_sma200 = float(sma200.iloc[-1])
        regime.update({
            "nikkei_close": round(last_close, 1),
            "sma25": round(last_sma25, 1),
            "sma200": round(last_sma200, 1),
        })
        if last_close > last_sma200 and last_sma25 > sma25_prev:
            regime["regime_on"] = True
            regime["reason"] = "Nikkei above SMA200 and SMA25 rising"
        else:
            regime["reason"] = "Nikkei regime is not risk-on"
    except Exception as e:
        logger.warning(f"Regime check failed: {e}")
        regime["reason"] = f"regime check failed: {e}"
    return regime


def _rank_score(setup, volume_ratio, adx):
    """Ranking only (never a gate). Mirrors the backtested formula."""
    score = 2.0 if setup == "breakout" else 1.0
    score += min(volume_ratio or 0.0, 3.0)
    score += (adx / 50.0) if adx else 0.0
    return round(score, 2)


def select_v2_picks(tech_results, fund_results, open_positions, capital,
                    vix_value=None):
    """Select new swing entries under the v2 rules.

    Returns pick dicts in the same shape as the v1 swing picks (so the
    report/site pipeline is unchanged), plus v2 fields used by the
    performance tracker: strategy, setup, atr, partial_target,
    planned_shares, risk_amount.
    """
    if vix_value is not None and vix_value >= PARAMS["vix_block"]:
        logger.info("V2: VIX block active, no picks")
        return []

    open_positions = open_positions or []
    slots = PARAMS["max_positions"] - len(open_positions)
    if slots <= 0:
        logger.info("V2: portfolio full, no picks")
        return []

    held_codes = {p["code"] for p in open_positions}
    sector_counts = {}
    for p in open_positions:
        sector_counts[p.get("sector", "不明")] = sector_counts.get(p.get("sector", "不明"), 0) + 1

    candidates = []
    for ticker, tech in tech_results.items():
        code = ticker.replace(".T", "")
        if code in held_codes:
            continue
        price = tech.get("current_price")
        atr = tech.get("atr")
        sma25 = tech.get("sma_25")
        sma75 = tech.get("sma_75")
        sma200 = tech.get("sma_200")
        rsi = tech.get("rsi")
        if not price or not atr or not sma25 or not sma75 or not sma200:
            continue
        # Trend gate: uptrend structure only
        if not (price > sma200 and price > sma25 and sma25 > sma75):
            continue
        atr_pct = atr / price * 100
        if not (PARAMS["atr_pct_min"] <= atr_pct <= PARAMS["atr_pct_max"]):
            continue
        vol_avg = tech.get("volume_avg", 0) or 0
        if vol_avg < PARAMS["min_volume_avg"]:
            continue
        # Setup detection (pass/fail)
        setup = None
        if (abs(price / sma25 - 1) <= PARAMS["pullback_band"]
                and rsi is not None
                and PARAMS["pullback_rsi_min"] <= rsi <= PARAMS["pullback_rsi_max"]):
            setup = "pullback"
        elif (tech.get("recent_high") and price >= tech["recent_high"] * 0.995
                and (tech.get("volume_ratio", 0) or 0) >= PARAMS["breakout_volume_ratio"]):
            setup = "breakout"
        if not setup:
            continue
        candidates.append({
            "ticker": ticker, "code": code, "tech": tech,
            "fund": (fund_results or {}).get(ticker, {}),
            "setup": setup,
            "score": _rank_score(setup, tech.get("volume_ratio", 0), tech.get("adx")),
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    logger.info(f"V2: {len(candidates)} candidates passed the gates")

    picks = []
    for cand in candidates:
        if len(picks) >= slots:
            break
        tech = cand["tech"]
        info = get_stock_info(cand["code"]) or {"code": cand["code"], "name": cand["code"], "sector": "不明"}
        sector = info["sector"]
        if sector_counts.get(sector, 0) >= PARAMS["max_per_sector"]:
            continue
        price = float(tech["current_price"])
        atr = float(tech["atr"])
        stop = round(price - PARAMS["atr_stop_mult"] * atr, 1)
        risk_per_share = price - stop
        if risk_per_share <= 0 or risk_per_share / price > PARAMS["max_stop_pct"]:
            continue
        target = round(price + PARAMS["reward_r"] * risk_per_share, 1)
        partial = round(price + PARAMS["partial_r"] * risk_per_share, 1)
        # Risk-based position size (planned; tracker re-sizes at the fill)
        risk_budget = capital * PARAMS["risk_per_trade"]
        shares = int(risk_budget / risk_per_share)
        shares = (shares // 100) * 100
        max_by_notional = int(capital * PARAMS["max_position_pct"] / price)
        shares = min(shares, (max_by_notional // 100) * 100)
        if shares < 100:
            continue
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        picks.append(_format_v2_pick(cand, info, price, atr, stop, target,
                                     partial, shares, risk_budget))
    logger.info(f"V2: selected {len(picks)} picks")
    return picks


def _format_v2_pick(cand, info, price, atr, stop, target, partial, shares,
                    risk_budget):
    """Format a v2 pick in the report's swing-pick shape."""
    from backend.screener.recommender import (
        _build_trend_commentary, _build_signal_commentary,
        _build_volume_commentary, _build_fundamental_commentary,
    )
    tech = cand["tech"]
    fund = cand["fund"]
    setup = cand["setup"]
    setup_label = "押し目買い（25日線付近）" if setup == "pullback" else "高値ブレイクアウト"
    risk_per_share = price - stop

    quick_signals = [f"v2: {setup_label}"]
    if tech.get("trend") == "strong_up":
        quick_signals.append("MA順配列")
    if tech.get("above_cloud"):
        quick_signals.append("雲上")
    rsi = tech.get("rsi")
    if rsi:
        quick_signals.append(f"RSI{rsi:.0f}")
    vol_ratio = tech.get("volume_ratio", 0) or 0
    if vol_ratio >= 1.3:
        quick_signals.append(f"出来高{vol_ratio:.1f}倍")

    entry_strategy = (
        f"損切り ¥{stop:,.1f}（2×ATR）、利確 ¥{target:,.1f}（+2R）、"
        f"+1R到達（¥{partial:,.1f}）で半分利確し残りは損切りを建値へ移動。"
        f"最大保有15営業日。1トレードのリスクは資金の0.5%"
        f"（約¥{risk_budget:,.0f}）、予定株数 {shares:,}株。"
    )

    return {
        "code": info["code"], "name": info["name"], "sector": info["sector"],
        "score": cand["score"],
        "score_breakdown": {"v2_rank_score": cand["score"], "setup": setup},
        "confidence": "high" if cand["score"] >= 4.5 else "medium",
        "holding_period": "最大15営業日（スイング）",
        "entry_point": round(price, 1), "target": target, "stop_loss": stop,
        "risk_reward_ratio": PARAMS["reward_r"],
        "rationale": {
            "technical": _build_trend_commentary(tech) or "上昇トレンド構造を確認",
            "fundamental": _build_fundamental_commentary(fund),
            "volume_analysis": _build_volume_commentary(tech),
            "entry_strategy": entry_strategy,
            "mtf_context": "",
            "quick_signals": quick_signals,
            "catalyst": "",
        },
        "fundamentals": {
            "per": fund.get("per"), "pbr": fund.get("pbr"),
            "roe": fund.get("roe"), "dividend_yield": fund.get("dividend_yield"),
            "ev_ebitda": fund.get("ev_ebitda"), "roic": fund.get("roic"),
        },
        "current_price": round(price, 1),
        "atr": round(atr, 2),
        # v2 fields consumed by the performance tracker
        "strategy": "v2",
        "setup": setup,
        "partial_target": partial,
        "planned_shares": shares,
        "risk_amount": round(risk_budget),
        "risk_per_share": round(risk_per_share, 1),
    }
