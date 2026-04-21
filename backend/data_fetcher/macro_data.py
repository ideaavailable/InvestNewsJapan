"""Macro economic data fetcher - expanded with yield curve analysis."""
import yfinance as yf
import logging

logger = logging.getLogger("investnews.macro")


def fetch_macro_data():
    """Fetch macro economic indicators including yield curve data."""
    result = {"us_10y_yield": None, "us_2y_yield": None, "dxy": None,
              "yield_spread": None, "yield_curve_signal": None}
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

    # Calculate yield spread (10Y - 2Y)
    if result["us_10y_yield"] and result["us_2y_yield"]:
        result["yield_spread"] = round(result["us_10y_yield"] - result["us_2y_yield"], 2)
        if result["yield_spread"] < 0:
            result["yield_curve_signal"] = "inverted"
        elif result["yield_spread"] < 0.5:
            result["yield_curve_signal"] = "flat"
        elif result["yield_spread"] < 1.5:
            result["yield_curve_signal"] = "normal"
        else:
            result["yield_curve_signal"] = "steep"

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
