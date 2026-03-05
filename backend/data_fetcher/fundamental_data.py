"""Fundamental data fetcher using yfinance."""
import yfinance as yf
import logging

logger = logging.getLogger("investnews.fundamental")


def fetch_fundamentals(ticker):
    """Fetch fundamental data for a single stock."""
    result = {"per": None, "pbr": None, "roe": None, "market_cap": None,
              "dividend_yield": None, "revenue_growth": None, "profit_margin": None,
              "sector": None, "industry": None, "name": None}
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info:
            return result
        result["per"] = info.get("trailingPE") or info.get("forwardPE")
        result["pbr"] = info.get("priceToBook")
        result["roe"] = info.get("returnOnEquity")
        if result["roe"]:
            result["roe"] = round(result["roe"] * 100, 2)
        result["market_cap"] = info.get("marketCap")
        result["dividend_yield"] = info.get("dividendYield")
        if result["dividend_yield"]:
            val = result["dividend_yield"] * 100
            result["dividend_yield"] = round(val, 2) if val < 30 else round(result["dividend_yield"], 2)
        result["revenue_growth"] = info.get("revenueGrowth")
        if result["revenue_growth"]:
            result["revenue_growth"] = round(result["revenue_growth"] * 100, 2)
        result["profit_margin"] = info.get("profitMargins")
        if result["profit_margin"]:
            result["profit_margin"] = round(result["profit_margin"] * 100, 2)
        result["sector"] = info.get("sector")
        result["industry"] = info.get("industry")
        result["name"] = info.get("shortName") or info.get("longName")
    except Exception as e:
        logger.warning(f"Error fetching fundamentals for {ticker}: {e}")
    return result


def fetch_fundamentals_batch(tickers):
    """Fetch fundamentals for multiple tickers."""
    results = {}
    for i, ticker in enumerate(tickers):
        if (i + 1) % 20 == 0:
            logger.info(f"Fetching fundamentals: {i + 1}/{len(tickers)}")
        results[ticker] = fetch_fundamentals(ticker)
    return results
