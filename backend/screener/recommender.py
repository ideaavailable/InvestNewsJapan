"""Final stock recommender - selects top picks with detailed analysis rationale."""
import logging
from backend.config import DAYTRADE_PICKS_COUNT, SWING_PICKS_COUNT, get_stock_info
from backend.screener.universe import filter_by_liquidity, filter_by_technical
from backend.screener.scoring import score_daytrade, score_swing

logger = logging.getLogger("investnews.recommender")


def select_daytrade_picks(tech_results, fund_results, sentiment_score=0, count=None):
    """Select top daytrade candidates."""
    count = count or DAYTRADE_PICKS_COUNT
    candidates = filter_by_liquidity(tech_results, fund_results, mode="daytrade")
    candidates = filter_by_technical(candidates, tech_results, mode="daytrade")
    scored = []
    for ticker in candidates:
        tech = tech_results.get(ticker, {})
        fund = fund_results.get(ticker, {})
        score = score_daytrade(ticker, tech, fund, sentiment_score)
        score["tech"] = tech
        score["fund"] = fund
        scored.append(score)
    scored.sort(key=lambda x: x["total"], reverse=True)
    picks = scored[:count]
    return [_format_daytrade_pick(p) for p in picks]


def select_swing_picks(tech_results, fund_results, sentiment_score=0, count=None):
    """Select top swing trade candidates."""
    count = count or SWING_PICKS_COUNT
    candidates = filter_by_liquidity(tech_results, fund_results, mode="swing")
    candidates = filter_by_technical(candidates, tech_results, mode="swing")
    scored = []
    for ticker in candidates:
        tech = tech_results.get(ticker, {})
        fund = fund_results.get(ticker, {})
        score = score_swing(ticker, tech, fund, sentiment_score)
        score["tech"] = tech
        score["fund"] = fund
        scored.append(score)
    scored.sort(key=lambda x: x["total"], reverse=True)
    picks = scored[:count]
    return [_format_swing_pick(p) for p in picks]


def _build_trend_commentary(tech):
    """Build detailed trend analysis text."""
    parts = []
    trend = tech.get("trend", "neutral")
    adx = tech.get("adx", 0) or 0
    price = tech.get("current_price", 0)
    sma5 = tech.get("sma_5")
    sma25 = tech.get("sma_25")
    sma75 = tech.get("sma_75")
    sma200 = tech.get("sma_200")

    if trend == "strong_up":
        parts.append("移動平均線が完全順配列（短期>中期>長期）を形成しており、明確な上昇トレンドが確認できる")
    elif trend == "up":
        parts.append("上昇トレンドが継続中")
    elif trend == "strong_down":
        parts.append("移動平均線が逆配列となっており、下降トレンドが鮮明")
    elif trend == "down":
        parts.append("下落基調にある")

    if adx > 30:
        parts.append(f"ADXが{adx:.0f}とトレンドの強さを示しており、トレンドフォロー戦略が有効")
    elif adx > 25:
        parts.append(f"ADXが{adx:.0f}と方向性が出始めている")

    if sma200 and price:
        if price > sma200:
            parts.append("200日移動平均線の上方に位置し、長期トレンドは上向き")
        else:
            parts.append("200日移動平均線を下回っており、長期トレンドには注意が必要")

    return "。".join(parts) + "。" if parts else ""


def _build_signal_commentary(tech):
    """Build detailed signal analysis text."""
    parts = []
    if tech.get("macd_cross_bullish"):
        parts.append("MACDがシグナル線を上抜けるゴールデンクロスが発生しており、短期的な買いシグナル")
    elif tech.get("macd_hist") and tech["macd_hist"] > 0:
        parts.append("MACDヒストグラムがプラス圏で推移しており、上昇モメンタムが維持されている")

    rsi = tech.get("rsi")
    if rsi:
        if rsi < 30:
            parts.append(f"RSIが{rsi:.0f}と売られすぎ水準まで低下。反発の可能性が高まっている")
        elif rsi < 40:
            parts.append(f"RSIが{rsi:.0f}とやや売られすぎの領域に接近。逆張りの好機となりうる")
        elif 40 <= rsi <= 60:
            parts.append(f"RSIは{rsi:.0f}と中立圏で、過熱感はなくまだ上昇余地がある")
        elif rsi > 70:
            parts.append(f"RSIが{rsi:.0f}と買われすぎ水準。短期的な調整リスクに留意")
        elif rsi > 60:
            parts.append(f"RSIは{rsi:.0f}とやや高めだが、強いトレンド下では許容範囲")

    if tech.get("above_cloud"):
        parts.append("一目均衡表の雲の上で推移しており、上値抵抗帯をクリアした強い形状")
    if tech.get("psar_bullish"):
        parts.append("パラボリックSARが買いシグナルを点灯中")
    if tech.get("stoch_bullish"):
        parts.append("ストキャスティクスが売られすぎ圏からの反転で買いサイン")

    return "。".join(parts) + "。" if parts else ""


def _build_volume_commentary(tech):
    """Build detailed volume analysis text."""
    vol_ratio = tech.get("volume_ratio", 0)
    vol_current = tech.get("volume_current", 0)
    obv_trend = tech.get("obv_trend", "")

    parts = []
    if vol_ratio >= 2.0:
        parts.append(f"直近出来高は{vol_current:,.0f}株で、20日平均比{vol_ratio:.1f}倍と大幅に増加。"
                    f"機関投資家の参入や材料性を示唆する出来高の急増であり、値動きの信頼性が高い")
    elif vol_ratio >= 1.5:
        parts.append(f"出来高は{vol_current:,.0f}株（平均比{vol_ratio:.1f}倍）と増加傾向。"
                    f"市場参加者の注目度が高まっている")
    elif vol_ratio >= 1.0:
        parts.append(f"出来高は{vol_current:,.0f}株（平均比{vol_ratio:.1f}倍）と平均的な水準")
    else:
        parts.append(f"出来高は{vol_current:,.0f}株（平均比{vol_ratio:.1f}倍）とやや低調。"
                    f"大口の参入は限定的な可能性がある")

    if obv_trend == "up":
        parts.append("OBV（出来高累計指標）は上昇トレンドにあり、価格上昇に買い蓄積が伴っていることを確認")
    elif obv_trend == "down":
        parts.append("OBVが下降傾向にあり、上昇局面でも売り圧力が潜在的に存在する点に注意")

    return "。".join(parts) + "。" if parts else ""


def _build_entry_rationale(price, entry, target, stop, atr, tech):
    """Build rationale for entry/target/stop levels."""
    parts = []
    support = tech.get("support", 0)
    resistance = tech.get("resistance", 0)

    if support and support > 0:
        parts.append(f"エントリーは現在値¥{entry:,.1f}付近。直近サポートが¥{support:,.1f}に位置する")
    if resistance and resistance > 0:
        parts.append(f"直近レジスタンス¥{resistance:,.1f}を突破すれば¥{target:,.1f}への上昇が期待できる")
    if atr:
        parts.append(f"ATR（14日）は{atr:.1f}円で、日中の平均値幅として適度なボラティリティ")
    if stop > 0:
        loss_pct = abs(entry - stop) / entry * 100 if entry > 0 else 0
        parts.append(f"損切りは¥{stop:,.1f}（エントリーから{loss_pct:.1f}%下方）に設定")

    return "。".join(parts) + "。" if parts else ""


def _format_daytrade_pick(pick):
    """Format a daytrade pick with comprehensive analysis."""
    ticker = pick["ticker"]
    code = ticker.replace(".T", "")
    info = get_stock_info(code) or {"code": code, "name": code, "sector": "不明"}
    tech = pick.get("tech", {})
    price = tech.get("current_price", 0)
    atr = tech.get("atr", 0) or 0
    support = tech.get("support", price)
    resistance = tech.get("resistance", price)
    stop_loss = round(support - atr * 0.5, 1) if support and atr else round(price * 0.97, 1)
    target = round(resistance + atr * 0.3, 1) if resistance and atr else round(price * 1.03, 1)
    rr = round((target - price) / (price - stop_loss), 2) if price > stop_loss else 0

    trend_text = _build_trend_commentary(tech)
    signal_text = _build_signal_commentary(tech)
    volume_text = _build_volume_commentary(tech)
    level_text = _build_entry_rationale(price, price, target, stop_loss, atr, tech)

    # Build concise signal list for quick reference
    quick_signals = []
    if tech.get("macd_cross_bullish"): quick_signals.append("MACDゴールデンクロス")
    if tech.get("above_cloud"): quick_signals.append("雲上")
    if tech.get("psar_bullish"): quick_signals.append("PSAR買い")
    if tech.get("trend") == "strong_up": quick_signals.append("MA順配列")
    rsi = tech.get("rsi")
    if rsi: quick_signals.append(f"RSI{rsi:.0f}")

    return {
        "code": info["code"], "name": info["name"], "sector": info["sector"],
        "score": pick["total"], "score_breakdown": pick["breakdown"],
        "entry_point": round(price, 1), "target": target, "stop_loss": stop_loss,
        "risk_reward_ratio": rr,
        "rationale": {
            "technical": " ".join([trend_text, signal_text]).strip() or "テクニカル指標総合判断",
            "volume_analysis": volume_text or f"直近出来高: {tech.get('volume_current', 0):,.0f}株",
            "entry_strategy": level_text,
            "quick_signals": quick_signals,
            "catalyst": "",
        },
        "current_price": round(price, 1),
        "atr": round(atr, 2) if atr else None,
    }


def _format_swing_pick(pick):
    """Format a swing trade pick with comprehensive analysis."""
    ticker = pick["ticker"]
    code = ticker.replace(".T", "")
    info = get_stock_info(code) or {"code": code, "name": code, "sector": "不明"}
    tech = pick.get("tech", {})
    fund = pick.get("fund", {})
    price = tech.get("current_price", 0)
    atr = tech.get("atr", 0) or 0
    support = tech.get("support", price)
    resistance = tech.get("resistance", price)
    stop_loss = round(support - atr, 1) if support and atr else round(price * 0.95, 1)
    target = round(resistance + atr * 0.8, 1) if resistance and atr else round(price * 1.07, 1)
    rr = round((target - price) / (price - stop_loss), 2) if price > stop_loss else 0

    trend_text = _build_trend_commentary(tech)
    signal_text = _build_signal_commentary(tech)
    volume_text = _build_volume_commentary(tech)
    level_text = _build_entry_rationale(price, price, target, stop_loss, atr, tech)

    # Build fundamental commentary
    fund_commentary = _build_fundamental_commentary(fund)

    per = fund.get("per")
    pbr = fund.get("pbr")
    roe = fund.get("roe")
    div_y = fund.get("dividend_yield")

    # Quick signal list
    quick_signals = []
    if tech.get("above_cloud"): quick_signals.append("雲上")
    if "up" in tech.get("trend", ""): quick_signals.append("上昇トレンド")
    if tech.get("obv_trend") == "up": quick_signals.append("OBV上昇")
    if tech.get("macd_hist", 0) and tech["macd_hist"] > 0: quick_signals.append("MACDプラス")

    return {
        "code": info["code"], "name": info["name"], "sector": info["sector"],
        "score": pick["total"], "score_breakdown": pick["breakdown"],
        "holding_period": "5〜10営業日",
        "entry_point": round(price, 1), "target": target, "stop_loss": stop_loss,
        "risk_reward_ratio": rr,
        "rationale": {
            "technical": " ".join([trend_text, signal_text]).strip() or "テクニカル指標総合判断",
            "fundamental": fund_commentary,
            "volume_analysis": volume_text,
            "entry_strategy": level_text,
            "quick_signals": quick_signals,
            "catalyst": "",
        },
        "fundamentals": {
            "per": per, "pbr": pbr, "roe": roe,
            "dividend_yield": div_y,
        },
        "current_price": round(price, 1),
    }


def _build_fundamental_commentary(fund):
    """Build detailed fundamental analysis text."""
    parts = []
    per = fund.get("per")
    pbr = fund.get("pbr")
    roe = fund.get("roe")
    div_y = fund.get("dividend_yield")
    rev_g = fund.get("revenue_growth")

    if per:
        if per < 10:
            parts.append(f"PER {per:.1f}倍と割安水準にあり、バリュー投資の観点から魅力的")
        elif per < 15:
            parts.append(f"PER {per:.1f}倍と適正〜やや割安な水準で、投資妙味がある")
        elif per < 25:
            parts.append(f"PER {per:.1f}倍と適正水準")
        else:
            parts.append(f"PER {per:.1f}倍とやや高めの評価であり、成長期待が株価に織り込まれている")

    if pbr:
        if pbr < 1.0:
            parts.append(f"PBR {pbr:.2f}倍と解散価値を下回る水準で、資産面での下値サポートが期待できる")
        elif pbr < 2.0:
            parts.append(f"PBR {pbr:.2f}倍")

    if roe:
        if roe > 15:
            parts.append(f"ROE {roe:.1f}%と高い資本効率を誇り、経営の質の高さを示す")
        elif roe > 10:
            parts.append(f"ROE {roe:.1f}%と安定した収益性")
        elif roe > 0:
            parts.append(f"ROE {roe:.1f}%")

    if div_y and 0 < div_y < 15:
        if div_y > 3.5:
            parts.append(f"配当利回り{div_y:.1f}%と高配当で下値サポート要因")
        elif div_y > 2.0:
            parts.append(f"配当利回り{div_y:.1f}%")

    if rev_g and rev_g > 10:
        parts.append(f"売上成長率{rev_g:.1f}%と力強い成長を維持")

    return "。".join(parts) + "。" if parts else "ファンダメンタルズデータ確認中"
