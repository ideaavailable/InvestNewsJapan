"""Macro economic data fetcher."""
import yfinance as yf
import logging

logger = logging.getLogger("investnews.macro")


def fetch_macro_data():
    """Fetch macro economic indicators."""
    result = {"us_10y_yield": None, "us_2y_yield": None, "dxy": None}
    macro_tickers = {"us_10y_yield": "^TNX", "us_2y_yield": "^IRX", "dxy": "DX-Y.NYB"}
    for name, ticker in macro_tickers.items():
        try:
            data = yf.download(ticker, period="5d", interval="1d", progress=False)
            if not data.empty:
                val = data["Close"].iloc[-1]
                if hasattr(val, 'item'):
                    val = val.item()
                result[name] = round(float(val), 2)
        except Exception as e:
            logger.warning(f"Error fetching {name}: {e}")
    return result


def get_market_regime(vix_value, us_10y=None):
    """Determine current market regime based on VIX and yields."""
    if vix_value is None:
        return {"regime": "不明", "risk_level": "unknown", "description": "データ取得不可"}
    if vix_value < 15:
        regime = "低ボラティリティ"
        risk = "low"
        desc = "市場は安定的。リスクオン環境でトレンドフォロー戦略が有効。"
    elif vix_value < 20:
        regime = "通常"
        risk = "moderate"
        desc = "市場は通常の変動範囲内。選別的な銘柄選びが重要。"
    elif vix_value < 30:
        regime = "やや不安定"
        risk = "elevated"
        desc = "ボラティリティ上昇中。ポジションサイズに注意し、損切りを厳格に。"
    else:
        regime = "高ボラティリティ"
        risk = "high"
        desc = "市場は大きく動揺中。デイトレードは慎重に、スイングは見送り推奨。"
    return {"regime": regime, "risk_level": risk, "description": desc, "vix": vix_value}
