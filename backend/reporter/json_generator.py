"""JSON report generator."""
import json
import os
import logging
from datetime import datetime
from backend.config import DATA_DIR, JST
from backend.utils.helpers import JSONEncoder

logger = logging.getLogger("investnews.reporter")


def generate_report(report_date, market_data, macro_analysis, sentiment_analysis,
                    sector_data, daytrade_picks, swing_picks):
    """Generate the full daily report as a dict."""
    report = {
        "report_date": report_date.isoformat(),
        "generated_at": datetime.now(JST).isoformat(),
        "market_summary": _build_market_summary(market_data),
        "macro_outlook": macro_analysis,
        "sentiment": sentiment_analysis,
        "market_forecast": macro_analysis.get("market_forecast", {}),
        "sector_analysis": sector_data,
        "daytrade_picks": daytrade_picks,
        "swing_picks": swing_picks,
        "methodology": {
            "technical_indicators": [
                "SMA (5/25/75/200日)", "EMA (5/25/75日)", "MACD (12,26,9)",
                "RSI (14日)", "ADX (14日)", "ストキャスティクス (%K14, %D3)",
                "CCI (20日)", "Williams %R (14日)", "一目均衡表 (9,26,52)",
                "パラボリックSAR", "OBV", "ATR (14日)",
            ],
            "screening_process": (
                "全上場銘柄 → 流動性フィルタ（出来高・時価総額）→ "
                "テクニカルスクリーニング → ファンダメンタルズ評価 → "
                "多因子スコアリング → 上位銘柄選出"
            ),
            "scoring_model": "テクニカル・ファンダメンタルズ・センチメント・リスクリワードの多軸評価",
            "data_source": "Yahoo Finance (yfinance)",
        },
        "disclaimer": (
            "当サイトは投資助言・投資勧誘を目的としたものではありません。"
            "掲載情報は「情報提供」を目的としており、特定の有価証券の売買を推奨するものではありません。"
            "投資に関する最終判断はご自身の責任で行ってください。"
            "過去のパフォーマンスは将来の成果を保証するものではありません。"
        ),
    }
    return report


def save_report(report, report_date=None):
    """Save report as JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    date_str = report_date.isoformat() if report_date else report.get("report_date", "unknown")
    filepath = os.path.join(DATA_DIR, f"report-{date_str}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, cls=JSONEncoder)
    # Update index
    _update_index(date_str)
    logger.info(f"Report saved: {filepath}")
    return filepath


def _update_index(date_str):
    """Update the report index file."""
    index_path = os.path.join(DATA_DIR, "index.json")
    index = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = []
    if date_str not in index:
        index.append(date_str)
        index.sort(reverse=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _build_market_summary(market_data):
    """Build market summary section."""
    summary = {}
    for key in ["nikkei225", "topix", "mothers", "sp500", "nasdaq", "dow", "vix",
                "usdjpy", "eurjpy", "crude_oil", "gold", "cme_nikkei"]:
        data = market_data.get(key, {})
        if isinstance(data, dict):
            summary[key] = data
        else:
            summary[key] = {"close": data, "change": None, "change_pct": None}
    return summary
