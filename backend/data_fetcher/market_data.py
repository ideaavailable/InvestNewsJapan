"""Market data fetcher using yfinance."""
import yfinance as yf
import pandas as pd
import logging
from backend.config import INDICES, FOREX, COMMODITIES, CME_NIKKEI, DATA_PERIOD, DATA_INTERVAL, BATCH_SIZE

logger = logging.getLogger("investnews.market_data")


def fetch_index_data():
    """Fetch major market indices data."""
    result = {}
    all_tickers = {**INDICES, **FOREX, **COMMODITIES, "cme_nikkei": CME_NIKKEI}
    ticker_str = " ".join(all_tickers.values())
    try:
        data = yf.download(ticker_str, period="5d", interval="1d", progress=False, group_by='ticker')
        for name, ticker in all_tickers.items():
            try:
                if len(all_tickers) == 1:
                    df = data
                else:
                    df = data[ticker] if ticker in data.columns.get_level_values(0) else pd.DataFrame()
                if df.empty or len(df) < 1:
                    result[name] = {"close": None, "change": None, "change_pct": None}
                    continue
                df = df.dropna(subset=["Close"])
                if len(df) < 1:
                    result[name] = {"close": None, "change": None, "change_pct": None}
                    continue
                close = float(df["Close"].iloc[-1])
                if len(df) >= 2:
                    prev_close = float(df["Close"].iloc[-2])
                    change = close - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close else 0
                else:
                    change = 0
                    change_pct = 0
                result[name] = {"close": round(close, 2), "change": round(change, 2),
                                "change_pct": round(change_pct, 2)}
            except Exception as e:
                logger.warning(f"Error processing {name}: {e}")
                result[name] = {"close": None, "change": None, "change_pct": None}
    except Exception as e:
        logger.error(f"Error fetching index data: {e}")
    return result


def fetch_stock_data(tickers, period=None, interval=None):
    """Fetch OHLCV data for multiple stocks in batches."""
    period = period or DATA_PERIOD
    interval = interval or DATA_INTERVAL
    all_data = {}
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        ticker_str = " ".join(batch)
        logger.info(f"Fetching batch {i // BATCH_SIZE + 1}: {len(batch)} tickers")
        try:
            data = yf.download(ticker_str, period=period, interval=interval, progress=False,
                               group_by='ticker', threads=True)
            if len(batch) == 1:
                if not data.empty:
                    all_data[batch[0]] = data.copy()
            else:
                for ticker in batch:
                    try:
                        if ticker in data.columns.get_level_values(0):
                            df = data[ticker].dropna(subset=["Close"])
                            if not df.empty and len(df) >= 30:
                                all_data[ticker] = df.copy()
                    except Exception as e:
                        logger.warning(f"Error extracting {ticker}: {e}")
        except Exception as e:
            logger.error(f"Error fetching batch: {e}")
    logger.info(f"Successfully fetched data for {len(all_data)} stocks")
    return all_data


def fetch_single_stock(ticker, period=None):
    """Fetch data for a single stock."""
    period = period or DATA_PERIOD
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if not df.empty:
            return df
    except Exception as e:
        logger.warning(f"Error fetching {ticker}: {e}")
    return pd.DataFrame()
