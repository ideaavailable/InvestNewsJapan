"""
Performance Tracker - Daily daytrade simulation with ¥10,000,000 capital.

Evaluates previous day's recommendations against actual price action,
tracks cumulative P&L, win rate, and other key metrics.
"""
import json
import os
import logging
from datetime import datetime, timedelta
from backend.config import DATA_DIR, JST

logger = logging.getLogger("investnews.performance")

INITIAL_CAPITAL = 10_000_000  # ¥10M
COMMISSION_RATE = 0.001       # 0.1% round-trip
PERFORMANCE_FILE = os.path.join(DATA_DIR, "performance.json")


def load_performance():
    """Load existing performance data."""
    if os.path.exists(PERFORMANCE_FILE):
        try:
            with open(PERFORMANCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "initial_capital": INITIAL_CAPITAL,
        "current_capital": INITIAL_CAPITAL,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "total_profit": 0,
        "total_loss": 0,
        "max_drawdown": 0,
        "peak_capital": INITIAL_CAPITAL,
        "daily_results": [],
    }


def save_performance(perf):
    """Save performance data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PERFORMANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(perf, f, ensure_ascii=False, indent=2)
    logger.info(f"Performance data saved: {PERFORMANCE_FILE}")


def evaluate_previous_day(report_date=None):
    """
    Evaluate previous trading day's daytrade picks against actual results.
    Uses intraday high/low to determine if target or stop was hit first.
    """
    import yfinance as yf

    if report_date is None:
        report_date = datetime.now(JST).date()

    # Find the previous report
    prev_report = _find_previous_report(report_date)
    if not prev_report:
        logger.info("No previous report found to evaluate")
        return None

    prev_date = prev_report["report_date"]
    picks = prev_report.get("daytrade_picks", [])
    if not picks:
        logger.info("No daytrade picks in previous report")
        return None

    perf = load_performance()

    # Check if already evaluated
    evaluated_dates = [d["date"] for d in perf["daily_results"]]
    if prev_date in evaluated_dates:
        logger.info(f"Already evaluated: {prev_date}")
        return perf

    # Get actual price data for the evaluation day (the day after the report)
    eval_date = _get_next_trading_day(prev_date)
    logger.info(f"Evaluating picks from {prev_date} using prices on {eval_date}")

    # Fetch intraday data for all picks
    tickers = [f"{p['code']}.T" for p in picks]
    try:
        data = yf.download(
            tickers, start=eval_date,
            end=(datetime.strptime(eval_date, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d"),
            interval="1d", progress=False
        )
    except Exception as e:
        logger.error(f"Failed to fetch evaluation data: {e}")
        return None

    # Calculate allocation per stock
    num_picks = len(picks)
    capital_per_pick = perf["current_capital"] / num_picks

    day_results = []
    day_pnl = 0

    for pick in picks:
        ticker = f"{pick['code']}.T"
        entry = pick["entry_point"]
        target = pick["target"]
        stop = pick["stop_loss"]

        try:
            if len(tickers) == 1:
                stock_data = data
            else:
                stock_data = data.xs(ticker, axis=1, level=1) if isinstance(data.columns, __import__('pandas').MultiIndex) else data

            if stock_data.empty or len(stock_data) == 0:
                logger.warning(f"No data for {ticker} on {eval_date}")
                continue

            row = stock_data.iloc[0]
            open_price = float(row["Open"])
            high = float(row["High"])
            low = float(row["Low"])
            close = float(row["Close"])
        except Exception as e:
            logger.warning(f"Error processing {ticker}: {e}")
            continue

        # Determine actual entry (use open price as realistic entry)
        actual_entry = open_price

        # Determine outcome: did target or stop get hit?
        # Check if high reached target and low reached stop
        target_hit = high >= target
        stop_hit = low <= stop

        if target_hit and stop_hit:
            # Both hit - assume stop hit first if open is closer to stop
            if abs(actual_entry - stop) < abs(actual_entry - target):
                result = "loss"
                exit_price = stop
            else:
                result = "win"
                exit_price = target
        elif target_hit:
            result = "win"
            exit_price = target
        elif stop_hit:
            result = "loss"
            exit_price = stop
        else:
            # Neither hit - use close price
            result = "win" if close > actual_entry else "loss"
            exit_price = close

        # Calculate P&L
        shares = int(capital_per_pick / actual_entry)
        if shares <= 0:
            continue
        gross_pnl = (exit_price - actual_entry) * shares
        commission = actual_entry * shares * COMMISSION_RATE
        net_pnl = gross_pnl - commission
        pnl_pct = (net_pnl / (actual_entry * shares)) * 100

        day_results.append({
            "code": pick["code"],
            "name": pick["name"],
            "entry": round(actual_entry, 1),
            "target": target,
            "stop": stop,
            "exit": round(exit_price, 1),
            "result": result,
            "shares": shares,
            "pnl": round(net_pnl),
            "pnl_pct": round(pnl_pct, 2),
        })

        day_pnl += net_pnl

        if result == "win":
            perf["wins"] += 1
            perf["total_profit"] += max(0, net_pnl)
        else:
            perf["losses"] += 1
            perf["total_loss"] += abs(min(0, net_pnl))

        perf["total_trades"] += 1

    # Update capital
    perf["current_capital"] += day_pnl

    # Update peak and drawdown
    if perf["current_capital"] > perf["peak_capital"]:
        perf["peak_capital"] = perf["current_capital"]
    drawdown = perf["peak_capital"] - perf["current_capital"]
    if drawdown > perf["max_drawdown"]:
        perf["max_drawdown"] = drawdown

    # Record daily result
    perf["daily_results"].append({
        "date": prev_date,
        "eval_date": eval_date,
        "trades": day_results,
        "day_pnl": round(day_pnl),
        "capital_after": round(perf["current_capital"]),
    })

    # Keep only last 90 days of detailed results
    if len(perf["daily_results"]) > 90:
        perf["daily_results"] = perf["daily_results"][-90:]

    save_performance(perf)

    # Log summary
    wins_today = sum(1 for t in day_results if t["result"] == "win")
    logger.info(
        f"Day result: {wins_today}/{len(day_results)} wins, "
        f"P&L: ¥{day_pnl:+,.0f}, Capital: ¥{perf['current_capital']:,.0f}"
    )

    return perf


def get_summary_stats(perf=None):
    """Calculate summary statistics for display."""
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
        "daily_results": perf["daily_results"][-30:],  # Last 30 days for chart
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


def _get_next_trading_day(date_str):
    """Get the next trading day after a given date."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    d += timedelta(days=1)
    # Skip weekends
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = evaluate_previous_day()
    if result:
        stats = get_summary_stats(result)
        print(f"\n=== Performance Summary ===")
        print(f"Capital: ¥{stats['current_capital']:,} (P&L: ¥{stats['cumulative_pnl']:+,})")
        print(f"Win Rate: {stats['win_rate']}% ({stats['wins']}W / {stats['losses']}L)")
        print(f"Profit Factor: {stats['profit_factor']}")
        print(f"Max Drawdown: ¥{stats['max_drawdown']:,} ({stats['max_drawdown_pct']}%)")
