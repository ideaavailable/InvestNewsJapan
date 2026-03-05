"""InvestNews Japan - Utility Functions"""
import json
import logging
from datetime import datetime, date, timedelta, timezone

JST = timezone(timedelta(hours=9))

def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    return logging.getLogger("investnews")

def get_today_jst():
    return datetime.now(JST).date()

def is_weekend(d):
    return d.weekday() >= 5

def is_market_holiday(d, holidays):
    return d.strftime("%Y-%m-%d") in holidays or is_weekend(d)

def get_previous_business_day(d, holidays):
    prev = d - timedelta(days=1)
    while is_market_holiday(prev, holidays):
        prev -= timedelta(days=1)
    return prev

def format_number(value, decimals=2):
    if value is None: return "N/A"
    return f"{value:,.{decimals}f}"

def format_percentage(value, decimals=2):
    if value is None: return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"

def format_japanese_number(value):
    if value is None: return "N/A"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1e8: return f"{sign}{abs_val/1e8:.1f}億"
    elif abs_val >= 1e4: return f"{sign}{abs_val/1e4:.1f}万"
    return f"{sign}{abs_val:,.0f}"

def safe_div(n, d, default=0.0):
    if d is None or d == 0: return default
    return n / d

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, 'item'):
            return obj.item()
        if hasattr(obj, 'tolist'):
            return obj.tolist()
        return super().default(obj)
