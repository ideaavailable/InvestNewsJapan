"""InvestNews Japan - Main Entry Point
Orchestrates data fetching, analysis, screening, and report generation.
Run daily at 06:00 JST to generate the morning report.

Enhanced with multi-timeframe analysis, sector rotation, and risk management.
"""
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import (STOCK_UNIVERSE, JP_HOLIDAYS_2026, get_yf_tickers, VIX_REGIMES)
from backend.utils.helpers import setup_logging, get_today_jst, is_market_holiday
from backend.data_fetcher.market_data import fetch_index_data, fetch_stock_data
from backend.data_fetcher.fundamental_data import fetch_fundamentals_batch
from backend.data_fetcher.macro_data import fetch_macro_data
from backend.data_fetcher.news_data import fetch_news_headlines
from backend.analyzer.technical import analyze_batch
from backend.analyzer.fundamental import analyze_fundamentals
from backend.analyzer.sentiment import analyze_market_sentiment
from backend.analyzer.macro import analyze_macro_environment
from backend.analyzer.multi_timeframe import analyze_weekly, get_mtf_alignment
from backend.analyzer.sector_rotation import analyze_sector_rotation
from backend.analyzer.risk_manager import (
    calculate_position_sizing, check_portfolio_correlation, build_risk_dashboard
)
from backend.screener.recommender import select_daytrade_picks, select_swing_picks
from backend.reporter.json_generator import generate_report, save_report
from backend.reporter.templates import build_sector_analysis

logger = setup_logging()


def _get_vix_regime(vix_value):
    """Get current VIX regime dict."""
    if vix_value is None:
        return VIX_REGIMES["normal"]
    for regime_name in ["low", "normal", "elevated", "high"]:
        r = VIX_REGIMES[regime_name]
        if vix_value < r["threshold"]:
            return {**r, "name": regime_name}
    return {**VIX_REGIMES["high"], "name": "high"}


def main(force=False):
    """Run the full analysis pipeline."""
    today = get_today_jst()
    logger.info(f"=== InvestNews Japan Daily Report: {today} ===")

    # Check if market is open
    if not force and is_market_holiday(today, JP_HOLIDAYS_2026):
        logger.info("Market holiday. Skipping report generation.")
        return None

    # Step 1: Fetch market overview
    logger.info("[1/9] Fetching market overview data...")
    market_data = fetch_index_data()
    logger.info(f"  Market data: {len(market_data)} items")

    # Step 2: Fetch macro data
    logger.info("[2/9] Fetching macro data...")
    macro_raw = fetch_macro_data()

    # Step 3: Fetch stock data
    logger.info("[3/9] Fetching stock OHLCV data...")
    tickers = get_yf_tickers()
    stock_data = fetch_stock_data(tickers)
    logger.info(f"  Stock data: {len(stock_data)} stocks")

    # Step 4: Technical analysis
    logger.info("[4/9] Running technical analysis (expanded indicators)...")
    tech_results = analyze_batch(stock_data)
    logger.info(f"  Analyzed: {len(tech_results)} stocks")

    # Step 5: Multi-timeframe analysis (NEW)
    logger.info("[5/9] Running multi-timeframe analysis...")
    weekly_results = analyze_weekly(stock_data)
    logger.info(f"  Weekly analysis: {len(weekly_results)} stocks")

    # Step 6: Fundamental analysis
    logger.info("[6/9] Fetching fundamentals (expanded metrics)...")
    interesting = list(tech_results.keys())[:80]
    fund_results = fetch_fundamentals_batch(interesting)
    logger.info(f"  Fundamentals: {len(fund_results)} stocks")

    # Step 7: Sentiment, Macro, Sector Rotation analysis
    logger.info("[7/9] Analyzing sentiment, macro & sector rotation...")
    headlines = fetch_news_headlines()
    vix_data = market_data.get("vix", {})
    vix_value = vix_data.get("close")
    vix_regime = _get_vix_regime(vix_value)
    logger.info(f"  VIX regime: {vix_regime.get('name', 'unknown')}")

    sentiment = analyze_market_sentiment(headlines, vix_data, market_data, tech_results)
    macro_analysis = analyze_macro_environment(market_data, macro_raw)
    sentiment_score = sentiment.get("combined_score", 0)

    # Sector analysis
    sector_data = build_sector_analysis(tech_results, STOCK_UNIVERSE)

    # Sector rotation (NEW)
    rotation = analyze_sector_rotation(tech_results, market_data, macro_raw)
    sector_scores = rotation.get("sector_scores", {})
    logger.info(f"  Economic phase: {rotation.get('economic_phase', {}).get('phase', 'unknown')}")

    # Step 8: Select picks & generate report
    logger.info("[8/9] Selecting picks with expanded scoring...")
    daytrade_picks = select_daytrade_picks(
        tech_results, fund_results, sentiment_score,
        weekly_results=weekly_results, sector_scores=sector_scores, vix_regime=vix_regime
    )
    swing_picks = select_swing_picks(
        tech_results, fund_results, sentiment_score,
        weekly_results=weekly_results, sector_scores=sector_scores, vix_regime=vix_regime
    )
    logger.info(f"  Daytrade picks: {len(daytrade_picks)}, Swing picks: {len(swing_picks)}")

    # Risk management (NEW)
    perf_data = None
    try:
        from backend.performance_tracker import load_performance
        perf_data = load_performance()
    except Exception:
        pass

    position_sizing = calculate_position_sizing(
        perf_data, vix_value, daytrade_picks,
        perf_data.get("current_capital", 10_000_000) if perf_data else 10_000_000
    )
    correlation_check = check_portfolio_correlation(daytrade_picks, tech_results)
    risk_dashboard = build_risk_dashboard(position_sizing, correlation_check, vix_value, perf_data)

    # Build and save report
    report = generate_report(
        report_date=today,
        market_data=market_data,
        macro_analysis=macro_analysis,
        sentiment_analysis=sentiment,
        sector_data=sector_data,
        daytrade_picks=daytrade_picks,
        swing_picks=swing_picks,
        sector_rotation=rotation,
        risk_dashboard=risk_dashboard,
    )
    filepath = save_report(report, today)
    logger.info(f"=== Report generated: {filepath} ===")

    # Step 9: Evaluate previous day's performance
    logger.info("[9/9] Evaluating previous day's performance...")
    try:
        from backend.performance_tracker import evaluate_previous_day, get_summary_stats
        perf = evaluate_previous_day(today)
        if perf:
            stats = get_summary_stats(perf)
            logger.info(
                f"  Performance: ¥{stats['current_capital']:,} "
                f"(P&L: ¥{stats['cumulative_pnl']:+,}, "
                f"Win: {stats['win_rate']}%, PF: {stats['profit_factor']})"
            )
    except Exception as e:
        logger.warning(f"  Performance evaluation skipped: {e}")

    return filepath


if __name__ == "__main__":
    force = "--force" in sys.argv
    main(force=force)
