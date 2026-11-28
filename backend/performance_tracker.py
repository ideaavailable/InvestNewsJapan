"""
Performance Tracker v2 - Trend-swing simulation with ¥10,000,000 capital.

Rebuilt for the v2 strategy. Key differences from v1:

- Positions are held across days (swing), not force-closed after one day.
- Win/loss is decided by the actual P&L sign. (In v1, a trade whose
  target sat below the entry could be booked as a "win" while losing
  money; that accounting bug is gone.)
- Position size comes from risk: a stopped-out trade loses ~0.5% of
  capital. Stops are 2 x ATR, target is +2R, half is taken off at +1R
  and the stop then moves to breakeven. Time stop: 15 trading days.
- Entries fill at the next trading day's open after the report date,
  with 0.05% slippage on both sides and 0.1% commission on entry value.
- current_capital is cash + open positions marked to the latest close.
"""
import json
import os
import logging
from datetime import datetime, timedelta
from backend.config import DATA_DIR, JST
from backend.strategy_v2 import PARAMS

logger = logging.getLogger("investnews.performance")

INITIAL_CAPITAL = 10_000_000  # ¥10M
COMMISSION_RATE = 0.001       # 0.1% of entry value, charged at close
SLIPPAGE_RATE = 0.0005        # 0.05% adverse slippage per side
PERFORMANCE_FILE = os.path.join(DATA_DIR, "performance.json")

P = PARAMS


def _fresh_state():
    return {
        "initial_capital": INITIAL_CAPITAL,
        "current_capital": INITIAL_CAPITAL,
        "cash": INITIAL_CAPITAL,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "total_profit": 0,
        "total_loss": 0,
        "max_drawdown": 0,
        "peak_capital": INITIAL_CAPITAL,
        "daily_results": [],
        "open_positions": [],
        "pending_entries": [],
        "last_entered_report_date": None,
        "last_processed_date": None,
        "strategy": "v2",
        "strategy_started": datetime.now(JST).date().isoformat(),
    }


def load_performance():
    """Load performance data; legacy v1 files are replaced by a fresh v2 state."""
    if os.path.exists(PERFORMANCE_FILE):
        try:
            with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "open_positions" in data and data.get("strategy") == "v2":
                state = _fresh_state()
                state.update(data)
                pend = state.get("pending_entries")
                if isinstance(pend, dict):
                    state["pending_entries"] = [pend]
                elif pend is None:
                    state["pending_entries"] = []
                return state
            logger.warning("Legacy v1 performance file detected; starting fresh v2 state")
        except Exception as e:
            logger.warning(f"Failed to load performance file: {e}")
    return _fresh_state()


def save_performance(perf):
    """Save performance data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(perf, f, ensure_ascii=False, indent=2)
    logger.info(f"Performance data saved: {PERFORMANCE_FILE}")


def _fetch_bars(codes, start, end):
    """Fetch daily OHLC bars: {code: {date_str: (open, high, low, close)}}."""
    import yfinance as yf

    result = {}
    if not codes:
        return result
    tickers = [f"{c}.T" for c in codes]
    try:
        data = yf.download(tickers, start=start, end=end, interval="1d",
                           progress=False, group_by="ticker", auto_adjust=False)
    except Exception as e:
        logger.error(f"Bar download failed: {e}")
        return result
    for code, ticker in zip(codes, tickers):
        try:
            try:
                frame = data[ticker]
            except Exception:
                frame = data
            bars = {}
            for idx, row in frame.iterrows():
                try:
                    o, h, l, c = (float(row["Open"]), float(row["High"]),
                                  float(row["Low"]), float(row["Close"]))
                except Exception:
                    continue
                if o != o or c != c:  # NaN guard
                    continue
                bars[idx.strftime("%Y-%m-%d")] = (o, h, l, c)
            result[code] = bars
        except Exception as e:
            logger.warning(f"No bars for {ticker}: {e}")
    return result


def _trading_dates(start, end):
    """Trading dates (Nikkei sessions) between start and end (exclusive/inclusive)."""
    import yfinance as yf

    try:
        data = yf.download("^N225", start=start, end=end, interval="1d",
                           progress=False, auto_adjust=False)
        return [idx.strftime("%Y-%m-%d") for idx in data.index]
    except Exception as e:
        logger.error(f"Nikkei calendar fetch failed: {e}")
        return []


def evaluate_previous_day(report_date=None):
    """Advance the v2 simulation to the latest available trading day.

    1. Register the previous report's v2 picks as pending entries.
    2. Enter pending picks at the open of the next trading day.
    3. Walk every open position day by day, applying the exit rules.
    """
    if report_date is None:
        report_date = datetime.now(JST).date()
    report_date_str = str(report_date)[:10]

    perf = load_performance()

    # 1) Queue pending entries from the previous report (v2 picks only).
    #    A queue is required: a report's picks enter at the NEXT session's
    #    open, whose bar only becomes available at the following run, so a
    #    new report can arrive while an older entry is still waiting.
    prev_report = _find_previous_report(report_date)
    if prev_report and prev_report.get("report_date") != perf.get("last_entered_report_date"):
        picks = [p for p in prev_report.get("swing_picks", [])
                 if p.get("strategy") == "v2"]
        queue = perf.get("pending_entries") or []
        if isinstance(queue, dict):
            queue = [queue]
        if not any(q.get("report_date") == prev_report["report_date"] for q in queue):
            queue.append({"report_date": prev_report["report_date"], "picks": picks})
        perf["pending_entries"] = queue
        perf["last_entered_report_date"] = prev_report["report_date"]
        logger.info(f"Queued {len(picks)} pending entries from {prev_report['report_date']}")

    last_processed = perf.get("last_processed_date")
    today_str = datetime.now(JST).date().isoformat()
    queue_dates = [q.get("report_date") for q in (perf.get("pending_entries") or [])
                   if isinstance(q, dict) and q.get("report_date")]
    window_start = last_processed or (min(queue_dates) if queue_dates else today_str)
    start_dt = datetime.strptime(window_start, "%Y-%m-%d") - timedelta(days=7)
    end_dt = datetime.now(JST) + timedelta(days=1)

    all_dates = _trading_dates(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
    if not all_dates:
        save_performance(perf)
        return perf
    latest_date = all_dates[-1]
    new_dates = [d for d in all_dates if last_processed is None or d > last_processed]

    if not new_dates:
        save_performance(perf)
        return perf

    # Baseline: nothing to simulate -> just advance the watermark
    if not perf["open_positions"] and not perf.get("pending_entries"):
        perf["last_processed_date"] = latest_date
        save_performance(perf)
        return perf

    codes = {p["code"] for p in perf["open_positions"]}
    for pend in (perf.get("pending_entries") or []):
        if isinstance(pend, dict):
            codes.update(p["code"] for p in pend.get("picks", []))
    bars = _fetch_bars(sorted(codes), start_dt.strftime("%Y-%m-%d"),
                       end_dt.strftime("%Y-%m-%d"))

    for date in new_dates:
        bucket = {"date": date, "eval_date": date, "trades": [], "day_pnl": 0}

        # 2) Entries at today's open for any queued report whose entry
        #    session is today
        if perf.get("pending_entries"):
            remaining = []
            for pend in perf["pending_entries"]:
                after = [d for d in all_dates if d > pend["report_date"]]
                entry_date = after[0] if after else None
                if entry_date == date:
                    _enter_pending(perf, pend.get("picks", []), bars, date)
                else:
                    remaining.append(pend)
            perf["pending_entries"] = remaining

        # 3) Manage open positions with today's bar
        for pos in list(perf["open_positions"]):
            bar = bars.get(pos["code"], {}).get(date)
            if bar is None:
                continue
            o, h, l, c = bar
            pos["days_held"] = pos.get("days_held", 0) + 1
            pos["last_close"] = c

            if not pos.get("partial_done"):
                if l <= pos["stop"]:
                    _close_position(perf, pos, pos["shares"], pos["stop"], "stop", date, bucket)
                elif h >= pos["partial_target"]:
                    half = (pos["initial_shares"] // 2 // 100) * 100
                    if half <= 0 or half >= pos["shares"]:
                        half = pos["shares"]
                    _close_position(perf, pos, half, pos["partial_target"], "partial", date, bucket)
                    if pos["shares"] > 0:
                        pos["partial_done"] = True
                        pos["stop"] = pos["entry"]  # breakeven
            else:
                if l <= pos["stop"]:
                    _close_position(perf, pos, pos["shares"], pos["stop"], "breakeven_stop", date, bucket)
                elif h >= pos["target"]:
                    _close_position(perf, pos, pos["shares"], pos["target"], "target", date, bucket)

            if pos["shares"] > 0 and pos.get("days_held", 0) >= P["time_stop_days"]:
                _close_position(perf, pos, pos["shares"], c, "time_stop", date, bucket)

        perf["open_positions"] = [p for p in perf["open_positions"] if p["shares"] > 0]

        # Mark-to-market snapshot for the day
        mtm = perf["cash"]
        for pos in perf["open_positions"]:
            bar = bars.get(pos["code"], {}).get(date)
            px = bar[3] if bar else pos.get("last_close", pos["entry"])
            mtm += pos["shares"] * px
        bucket["capital_after"] = round(mtm)
        bucket["day_pnl"] = round(bucket["day_pnl"])
        perf["daily_results"].append(bucket)
        perf["last_processed_date"] = date

    # Final mark-to-market
    mtm = perf["cash"]
    for pos in perf["open_positions"]:
        mtm += pos["shares"] * pos.get("last_close", pos["entry"])
    perf["current_capital"] = mtm
    if perf["current_capital"] > perf["peak_capital"]:
        perf["peak_capital"] = perf["current_capital"]
    drawdown = perf["peak_capital"] - perf["current_capital"]
    if drawdown > perf["max_drawdown"]:
        perf["max_drawdown"] = drawdown

    if len(perf["daily_results"]) > 90:
        perf["daily_results"] = perf["daily_results"][-90:]

    save_performance(perf)
    logger.info(
        f"V2 sim advanced to {perf['last_processed_date']}: "
        f"capital ¥{perf['current_capital']:,.0f}, "
        f"open positions {len(perf['open_positions'])}"
    )
    return perf


def _enter_pending(perf, picks, bars, date):
    """Enter pending picks at today's open with risk-based sizing."""
    for pick in picks:
        if len(perf["open_positions"]) >= P["max_positions"]:
            break
        code = pick["code"]
        if any(p["code"] == code for p in perf["open_positions"]):
            continue
        sector = pick.get("sector", "不明")
        same_sector = sum(1 for p in perf["open_positions"] if p.get("sector") == sector)
        if same_sector >= P["max_per_sector"]:
            continue
        bar = bars.get(code, {}).get(date)
        atr = pick.get("atr")
        if bar is None or not atr:
            continue
        entry = bar[0] * (1 + SLIPPAGE_RATE)
        stop = entry - P["atr_stop_mult"] * atr
        risk_per_share = entry - stop
        if risk_per_share <= 0 or risk_per_share / entry > P["max_stop_pct"]:
            continue
        equity_ref = perf["cash"] + sum(
            p["shares"] * p.get("last_close", p["entry"]) for p in perf["open_positions"])
        risk_budget = equity_ref * P["risk_per_trade"]
        shares = (int(risk_budget / risk_per_share) // 100) * 100
        max_by_notional = (int(equity_ref * P["max_position_pct"] / entry) // 100) * 100
        shares = min(shares, max_by_notional)
        max_by_cash = (int(perf["cash"] / entry) // 100) * 100
        shares = min(shares, max_by_cash)
        if shares < 100:
            continue
        perf["cash"] -= shares * entry
        perf["open_positions"].append({
            "code": code,
            "name": pick.get("name", code),
            "sector": sector,
            "entry_date": date,
            "entry": round(entry, 1),
            "shares": shares,
            "initial_shares": shares,
            "stop": round(stop, 1),
            "target": round(entry + P["reward_r"] * risk_per_share, 1),
            "partial_target": round(entry + P["partial_r"] * risk_per_share, 1),
            "partial_done": False,
            "atr": atr,
            "setup": pick.get("setup", ""),
            "days_held": 0,
            "last_close": bar[3],
        })
        logger.info(f"V2 entry: {code} {shares} shares @ ¥{entry:,.1f} (stop ¥{stop:,.1f})")


def _close_position(perf, pos, shares, price, reason, date, bucket):
    """Close (part of) a position at a rule price; record the trade by P&L sign."""
    if shares <= 0:
        return
    exit_adj = price * (1 - SLIPPAGE_RATE)
    proceeds = shares * exit_adj
    commission = pos["entry"] * shares * COMMISSION_RATE
    pnl = proceeds - commission - shares * pos["entry"]
    perf["cash"] += proceeds - commission
    pos["shares"] -= shares

    result = "win" if pnl > 0 else "loss"
    if result == "win":
        perf["wins"] += 1
        perf["total_profit"] += pnl
    else:
        perf["losses"] += 1
        perf["total_loss"] += abs(pnl)
    perf["total_trades"] += 1

    bucket["trades"].append({
        "code": pos["code"],
        "name": pos["name"],
        "entry": pos["entry"],
        "target": pos["target"],
        "stop": pos["stop"],
        "exit": round(price, 1),
        "result": result,
        "shares": shares,
        "pnl": round(pnl),
        "pnl_pct": round(pnl / (pos["entry"] * shares) * 100, 2),
        "reason": reason,
        "setup": pos.get("setup", ""),
        "entry_date": pos.get("entry_date", ""),
    })
    bucket["day_pnl"] += pnl


def get_summary_stats(perf=None):
    """Calculate summary statistics for display (v1-compatible keys)."""
    if perf is None:
        perf = load_performance()

    total = perf["total_trades"]
    wins = perf["wins"]
    win_rate = (wins / total * 100) if total > 0 else 0
    profit_factor = (perf["total_profit"] / perf["total_loss"]) if perf["total_loss"] > 0 else 0
    cumulative_pnl = perf["current_capital"] - perf["initial_capital"]
    cumulative_return = (cumulative_pnl / perf["initial_capital"]) * 100

    return {
        "initial_capital": perf["initial_capital"],
        "current_capital": round(perf["current_capital"]),
        "cumulative_pnl": round(cumulative_pnl),
        "cumulative_return_pct": round(cumulative_return, 2),
        "total_trades": total,
        "wins": wins,
        "losses": perf["losses"],
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(perf["max_drawdown"]),
        "max_drawdown_pct": round(perf["max_drawdown"] / perf["peak_capital"] * 100, 2) if perf["peak_capital"] > 0 else 0,
        "open_positions": len(perf.get("open_positions", [])),
        "cash": round(perf.get("cash", 0)),
        "strategy": perf.get("strategy", "v2"),
        "daily_results": perf["daily_results"][-30:],
    }


def _find_previous_report(current_date):
    """Find the most recent report before current_date."""
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, "%Y-%m-%d").date()

    for i in range(1, 8):
        d = current_date - timedelta(days=i)
        filepath = os.path.join(DATA_DIR, f"report-{d.isoformat()}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = evaluate_previous_day()
    if result:
        stats = get_summary_stats(result)
        print(f"\n=== Performance Summary (v2) ===")
        print(f"Capital: ¥{stats['current_capital']:,} (P&L: ¥{stats['cumulative_pnl']:+,})")
        print(f"Win Rate: {stats['win_rate']}% ({stats['wins']}W / {stats['losses']}L)")
        print(f"Profit Factor: {stats['profit_factor']}")
        print(f"Open Positions: {stats['open_positions']}")
