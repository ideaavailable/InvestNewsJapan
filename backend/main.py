"""InvestNews Japan - Main Entry Point
Orchestrates data fetching, analysis, screening, and report generation.
Run daily at 06:00 JST to generate the morning report.
"""
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import (STOCK_UNIVERSE, JP_HOLIDAYS_2026, get_yf_tickers)
from backend.utils.helpers import setup_logging, get_today_jst, is_market_holiday
from backend.data_fetcher.market_data import fetch_index_data, fetch_stock_data
from backend.data_fetcher.fundamental_data import fetch_fundamentals_batch
from backend.data_fetcher.macro_data import fetch_macro_data
from backend.data_fetcher.news_data import fetch_news_headlines
from backend.analyzer.technical import analyze_batch
from backend.analyzer.fundamental import analyze_fundamentals
from backend.analyzer.sentiment import analyze_market_sentiment
from backend.analyzer.macro import analyze_macro_environment
from backend.screener.recommender import select_daytrade_picks, select_swing_picks
from backend.reporter.json_generator import generate_report, save_report
from backend.reporter.templates import build_sector_analysis

logger = setup_logging()


def main(force=False):
    """Run the full analysis pipeline."""
    today = get_today_jst()
    logger.info(f"=== InvestNews Japan Daily Report: {today} ===")

    # Check if market is open
    if not force and is_market_holiday(today, JP_HOLIDAYS_2026):
        logger.info("Market holiday. Skipping report generation.")
        return None

    # Step 1: Fetch market overview
    logger.info("[1/7] Fetching market overview data...")
    market_data = fetch_index_data()
    logger.info(f"  Market data: {len(market_data)} items")

    # Step 2: Fetch macro data
    logger.info("[2/7] Fetching macro data...")
    macro_raw = fetch_macro_data()

    # Step 3: Fetch stock data
    logger.info("[3/7] Fetching stock OHLCV data...")
    tickers = get_yf_tickers()
    stock_data = fetch_stock_data(tickers)
    logger.info(f"  Stock data: {len(stock_data)} stocks")

    # Step 4: Technical analysis
    logger.info("[4/7] Running technical analysis...")
    tech_results = analyze_batch(stock_data)
    logger.info(f"  Analyzed: {len(tech_results)} stocks")

    # Step 5: Fundamental analysis
    logger.info("[5/7] Fetching fundamentals...")
    # Only fetch fundamentals for technically interesting stocks
    interesting = list(tech_results.keys())[:80]  # Limit to save API calls
    fund_results = fetch_fundamentals_batch(interesting)
    logger.info(f"  Fundamentals: {len(fund_results)} stocks")

    # Step 6: Sentiment & Macro analysis
    logger.info("[6/7] Analyzing sentiment & macro...")
    headlines = fetch_news_headlines()
    vix_data = market_data.get("vix", {})
    sentiment = analyze_market_sentiment(headlines, vix_data)
    macro_analysis = analyze_macro_environment(market_data, macro_raw)
    sentiment_score = sentiment.get("combined_score", 0)

    # Sector analysis
    sector_data = build_sector_analysis(tech_results, STOCK_UNIVERSE)

    # Step 7: Select picks & generate report
    logger.info("[7/7] Selecting picks and generating report...")
    daytrade_picks = select_daytrade_picks(tech_results, fund_results, sentiment_score)
    swing_picks = select_swing_picks(tech_results, fund_results, sentiment_score)
    logger.info(f"  Daytrade picks: {len(daytrade_picks)}, Swing picks: {len(swing_picks)}")

    # Build and save report
    report = generate_report(
        report_date=today,
        market_data=market_data,
        macro_analysis=macro_analysis,
        sentiment_analysis=sentiment,
        sector_data=sector_data,
        daytrade_picks=daytrade_picks,
        swing_picks=swing_picks,
    )
    filepath = save_report(report, today)
    logger.info(f"=== Report generated: {filepath} ===")
    return filepath


if __name__ == "__main__":
    force = "--force" in sys.argv
    main(force=force)
