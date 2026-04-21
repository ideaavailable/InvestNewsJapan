"""Fundamental data fetcher using yfinance - expanded metrics."""
import yfinance as yf
import logging

logger = logging.getLogger("investnews.fundamental")


def fetch_fundamentals(ticker):
    """Fetch comprehensive fundamental data for a single stock."""
    result = {
        "per": None, "pbr": None, "roe": None, "market_cap": None,
        "dividend_yield": None, "revenue_growth": None, "profit_margin": None,
        "sector": None, "industry": None, "name": None,
        # New fields
        "ev_ebitda": None, "roic": None, "fcf_yield": None,
        "debt_equity": None, "current_ratio": None, "peg_ratio": None,
        "payout_ratio": None, "eps_growth": None, "operating_margin": None,
        "beta": None, "short_ratio": None,
    }
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info:
            return result

        # Original fields
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

        # New expanded fields
        result["ev_ebitda"] = info.get("enterpriseToEbitda")
        if result["ev_ebitda"] and result["ev_ebitda"] < 0:
            result["ev_ebitda"] = None

        # ROIC approximation: returnOnAssets can serve as proxy
        roa = info.get("returnOnAssets")
        if roa:
            result["roic"] = round(roa * 100, 2)

        # FCF yield
        fcf = info.get("freeCashflow")
        mcap = info.get("marketCap")
        if fcf and mcap and mcap > 0:
            result["fcf_yield"] = round(fcf / mcap * 100, 2)

        # Debt/Equity
        result["debt_equity"] = info.get("debtToEquity")
        if result["debt_equity"]:
            result["debt_equity"] = round(result["debt_equity"] / 100, 2)  # yfinance gives in %

        # Current ratio
        result["current_ratio"] = info.get("currentRatio")
        if result["current_ratio"]:
            result["current_ratio"] = round(result["current_ratio"], 2)

        # PEG ratio
        result["peg_ratio"] = info.get("pegRatio")
        if result["peg_ratio"]:
            result["peg_ratio"] = round(result["peg_ratio"], 2)

        # Payout ratio
        result["payout_ratio"] = info.get("payoutRatio")
        if result["payout_ratio"]:
            result["payout_ratio"] = round(result["payout_ratio"] * 100, 1)

        # EPS growth (trailing vs forward PE diff as proxy)
        trailing = info.get("trailingPE")
        forward = info.get("forwardPE")
        if trailing and forward and forward > 0 and trailing > 0:
            result["eps_growth"] = round((trailing / forward - 1) * 100, 1)

        # Operating margin
        result["operating_margin"] = info.get("operatingMargins")
        if result["operating_margin"]:
            result["operating_margin"] = round(result["operating_margin"] * 100, 2)

        # Beta
        result["beta"] = info.get("beta")
        if result["beta"]:
            result["beta"] = round(result["beta"], 2)

        # Short ratio
        result["short_ratio"] = info.get("shortRatio")

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
