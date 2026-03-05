"""Stock universe definition and filtering."""
import logging
from backend.config import STOCK_UNIVERSE, MIN_AVG_VOLUME_DAYTRADE, MIN_AVG_VOLUME_SWING, MIN_MARKET_CAP

logger = logging.getLogger("investnews.universe")


def get_universe_tickers():
    """Get all tickers in yfinance format."""
    return [f"{code}.T" for code, _, _ in STOCK_UNIVERSE]


def filter_by_liquidity(tech_results, fund_results, mode="daytrade"):
    """Filter stocks by liquidity requirements."""
    min_vol = MIN_AVG_VOLUME_DAYTRADE if mode == "daytrade" else MIN_AVG_VOLUME_SWING
    filtered = []
    for ticker, tech in tech_results.items():
        vol_avg = tech.get("volume_avg", 0)
        if vol_avg and vol_avg >= min_vol:
            mc = fund_results.get(ticker, {}).get("market_cap")
            if mc is None or mc >= MIN_MARKET_CAP:
                filtered.append(ticker)
    logger.info(f"Liquidity filter ({mode}): {len(tech_results)} -> {len(filtered)}")
    return filtered


def filter_by_technical(tickers, tech_results, mode="daytrade"):
    """Filter stocks by technical criteria."""
    filtered = []
    for ticker in tickers:
        tech = tech_results.get(ticker, {})
        if not tech:
            continue
        price = tech.get("current_price")
        if not price or price <= 0:
            continue
        adx = tech.get("adx")
        if mode == "daytrade":
            vol_ratio = tech.get("volume_ratio", 0)
            if vol_ratio >= 1.0 or (adx and adx > 20):
                filtered.append(ticker)
        else:
            trend = tech.get("trend", "")
            if trend in ("strong_up", "up") or (adx and adx > 20):
                filtered.append(ticker)
            elif tech.get("rsi") and 30 < tech["rsi"] < 70:
                filtered.append(ticker)
    logger.info(f"Technical filter ({mode}): {len(tickers)} -> {len(filtered)}")
    return filtered
