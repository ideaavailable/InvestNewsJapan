"""Macro environment analysis module - provides detailed market commentary."""
import logging

logger = logging.getLogger("investnews.macro_analyzer")


def analyze_macro_environment(market_data, macro_data):
    """Analyze the macro environment and its impact on Japanese equities."""
    analysis = {
        "summary": "", "key_factors": [], "risk_level": "moderate",
        "market_forecast": {"direction": "neutral", "confidence": "low"},
        "sector_implications": {},
        "detailed_commentary": "",
    }
    factors = []
    commentary_parts = []
    bullish_points = 0
    bearish_points = 0

    # ── US Market Analysis ──
    sp500 = market_data.get("sp500", {})
    nasdaq = market_data.get("nasdaq", {})
    dow = market_data.get("dow", {})
    sp_pct = sp500.get("change_pct")
    nas_pct = nasdaq.get("change_pct")
    dow_pct = dow.get("change_pct")

    if sp_pct is not None:
        # Determine US market consensus
        us_values = [v for v in [sp_pct, nas_pct, dow_pct] if v is not None]
        us_avg = sum(us_values) / len(us_values) if us_values else 0
        tech_led = nas_pct is not None and sp_pct is not None and nas_pct > sp_pct + 0.3

        if sp_pct > 1.5:
            impact = "positive"
            detail = f"S&P500が{sp_pct:+.2f}%と大幅上昇。"
            if tech_led:
                detail += f"特にNASDAQが{nas_pct:+.2f}%と力強く、ハイテク主導の上昇。"
            detail += "米国市場の強いリスクオン地合いが日本株にも好影響を与える公算が大きい。"
            commentary_parts.append(
                f"前日の米国市場はS&P500が{sp_pct:+.2f}%、NASDAQが{nas_pct:+.2f}% "
                f"と力強い上昇を見せた。{'半導体・ハイテク株が牽引する形で' if tech_led else ''}"
                f"投資家のリスク選好姿勢が明確であり、東京市場でも半導体・ハイテク関連を中心に"
                f"買い先行のスタートが見込まれる。"
            )
            bullish_points += 2
        elif sp_pct > 0.5:
            impact = "positive"
            detail = f"S&P500が{sp_pct:+.2f}%と堅調。日本株にもプラスの影響が期待される。"
            commentary_parts.append(
                f"前日の米国市場はS&P500が{sp_pct:+.2f}%と堅調に推移。"
                f"大きなサプライズはないものの、底堅い相場展開は日本株にとっても追い風材料。"
            )
            bullish_points += 1
        elif sp_pct < -1.5:
            impact = "negative"
            detail = f"S&P500が{sp_pct:+.2f}%と大幅下落。日本株にも売り圧力が予想される。"
            commentary_parts.append(
                f"前日の米国市場はS&P500が{sp_pct:+.2f}%と大幅に調整。"
                f"{'テクノロジーセクターが特に弱く、NASDAQは' + f'{nas_pct:+.2f}%と下落。' if nas_pct and nas_pct < -1.5 else ''}"
                f"リスク回避の動きが強まっており、東京市場でも寄り付きから売り優勢の展開が懸念される。"
                f"特にグロース株やバリュエーションの高い銘柄は下落圧力を受けやすい。"
            )
            bearish_points += 2
        elif sp_pct < -0.5:
            impact = "negative"
            detail = f"S&P500が{sp_pct:+.2f}%と軟調。日本株市場への重荷に。"
            commentary_parts.append(
                f"前日の米国市場はS&P500が{sp_pct:+.2f}%と小幅安。"
                f"相場の方向感に乏しく、東京市場でも上値追いの材料に欠ける展開が予想される。"
            )
            bearish_points += 1
        else:
            impact = "neutral"
            detail = f"S&P500は{sp_pct:+.2f}%と小動き。市場への影響は限定的。"
            commentary_parts.append(
                f"前日の米国市場はS&P500が{sp_pct:+.2f}%とほぼ横ばいで推移。"
                f"手掛かり材料に乏しく、方向感の定まらない展開だった。"
                f"東京市場への影響は中立的だが、独自材料での値動きが中心となりそうだ。"
            )

        factors.append({"factor": "米国市場", "impact": impact, "detail": detail})

    # ── Forex Analysis ──
    usdjpy = market_data.get("usdjpy", {})
    eurjpy = market_data.get("eurjpy", {})
    if usdjpy.get("close"):
        rate = usdjpy["close"]
        change = usdjpy.get("change_pct", 0) or 0

        if rate > 158:
            impact = "mixed"
            detail = (f"USD/JPY {rate:.2f}円（前日比{change:+.2f}%）。"
                     f"歴史的な円安水準が持続しており、輸出企業にはプラスだが、"
                     f"為替介入リスクや輸入コスト増が警戒材料。")
            commentary_parts.append(
                f"為替市場ではドル円が{rate:.2f}円と高水準を維持。"
                f"輸出企業の業績押し上げ効果が期待される一方、"
                f"政府・日銀による為替介入への警戒感も根強い。"
                f"この水準では自動車・電子部品セクターが恩恵を受けやすいが、"
                f"内需・輸入関連企業にとってはコスト増の重荷となる。"
            )
        elif rate > 150:
            impact = "positive"
            detail = f"USD/JPY {rate:.2f}円。円安基調は輸出企業の追い風。"
            commentary_parts.append(
                f"ドル円は{rate:.2f}円と円安基調が継続。"
                f"このレンジでは輸出企業の為替差益が拡大し、"
                f"トヨタ・ソニー等の大型輸出株にとって好環境が続く。"
            )
            bullish_points += 1
        elif rate > 140:
            impact = "neutral"
            detail = f"USD/JPY {rate:.2f}円。為替は安定的な水準で影響は限定的。"
        elif rate < 135:
            impact = "negative"
            detail = f"USD/JPY {rate:.2f}円。急速な円高は輸出企業の収益圧迫要因。"
            commentary_parts.append(
                f"ドル円が{rate:.2f}円まで円高が進行。"
                f"輸出企業の為替前提を下回る可能性があり、"
                f"業績下方修正リスクが意識されやすい局面。"
                f"内需株やディフェンシブセクターへのシフトが有効。"
            )
            bearish_points += 1
        else:
            impact = "neutral"
            detail = f"USD/JPY {rate:.2f}円。適度な水準で推移。"

        factors.append({"factor": "為替", "impact": impact, "detail": detail})

    # ── VIX Analysis ──
    vix = market_data.get("vix", {})
    if vix.get("close"):
        v = vix["close"]
        v_change = vix.get("change_pct", 0) or 0

        if v < 15:
            analysis["risk_level"] = "low"
            factors.append({"factor": "VIX", "impact": "positive",
                           "detail": f"VIX {v:.1f}と低水準。市場は安定しており、リスクテイクに好適な環境。"})
            commentary_parts.append(
                f"恐怖指数（VIX）は{v:.1f}と低水準で推移しており、"
                f"市場参加者のリスク許容度は高い状態にある。"
                f"この環境ではレバレッジを効かせたポジションも取りやすい。"
            )
        elif v < 20:
            analysis["risk_level"] = "moderate"
            factors.append({"factor": "VIX", "impact": "neutral",
                           "detail": f"VIX {v:.1f}と平常水準。通常のリスク管理で十分。"})
        elif v < 25:
            analysis["risk_level"] = "elevated"
            factors.append({"factor": "VIX", "impact": "negative",
                           "detail": f"VIX {v:.1f}とやや上昇。市場は不安定さを増しており、ポジション量の抑制を推奨。"})
            commentary_parts.append(
                f"VIXが{v:.1f}とやや高い水準にあり（前日比{v_change:+.1f}%）、"
                f"市場の先行き不透明感が意識されている。"
                f"デイトレードではポジションサイズを通常の70-80%に抑制し、"
                f"損切りラインを通常より浅めに設定することを推奨する。"
            )
            bearish_points += 1
        else:
            analysis["risk_level"] = "high"
            factors.append({"factor": "VIX", "impact": "negative",
                           "detail": f"VIX {v:.1f}と高水準。パニック相場の兆候あり。慎重な取引姿勢が不可欠。"})
            commentary_parts.append(
                f"VIXが{v:.1f}と危険水準に達しており、市場のパニック的な動きに警戒が必要。"
                f"このような高ボラティリティ環境では、デイトレードのポジションサイズを"
                f"通常の50%以下に縮小し、スイングトレードは新規エントリーを控えることが賢明。"
                f"損切りがATR×1.5以内に収まらない銘柄は見送りを推奨する。"
            )
            bearish_points += 2

    # ── CME Nikkei Futures ──
    cme = market_data.get("cme_nikkei", {})
    nikkei = market_data.get("nikkei225", {})
    if cme.get("close") and nikkei.get("close"):
        diff = cme["close"] - nikkei["close"]
        diff_pct = (diff / nikkei["close"]) * 100
        if diff_pct > 0.5:
            analysis["market_forecast"]["direction"] = "bullish"
            analysis["market_forecast"]["confidence"] = "high"
            factors.append({"factor": "CME日経先物", "impact": "positive",
                           "detail": f"CME日経先物は大証比{diff:+,.0f}円（{diff_pct:+.2f}%）。明確な上方乖離で高寄りが予想される。"})
            commentary_parts.append(
                f"CME日経225先物は大証終値比{diff:+,.0f}円（{diff_pct:+.2f}%）の上方乖離。"
                f"東京市場の寄り付きは大きくギャップアップしてスタートする見込み。"
                f"デイトレードでは寄り付き直後の飛び乗りではなく、"
                f"初動の値幅が落ち着いた後の押し目買いが有効な戦略となる。"
            )
            bullish_points += 2
        elif diff_pct > 0.2:
            analysis["market_forecast"]["direction"] = "bullish"
            analysis["market_forecast"]["confidence"] = "moderate"
            factors.append({"factor": "CME日経先物", "impact": "positive",
                           "detail": f"CME日経先物は大証比{diff:+,.0f}円（{diff_pct:+.2f}%）。小幅高寄りが予想される。"})
            bullish_points += 1
        elif diff_pct < -0.5:
            analysis["market_forecast"]["direction"] = "bearish"
            analysis["market_forecast"]["confidence"] = "high"
            factors.append({"factor": "CME日経先物", "impact": "negative",
                           "detail": f"CME日経先物は大証比{diff:+,.0f}円（{diff_pct:+.2f}%）。大幅安寄りの可能性。"})
            commentary_parts.append(
                f"CME日経225先物は大証終値比{diff:+,.0f}円（{diff_pct:+.2f}%）の下方乖離。"
                f"東京市場はギャップダウンで寄り付く可能性が高い。"
                f"デイトレードでは安易な逆張りを避け、下落が落ち着いた銘柄からの選別が重要。"
                f"スイングのホールド中銘柄は損切りラインの確認を徹底したい。"
            )
            bearish_points += 2
        elif diff_pct < -0.2:
            analysis["market_forecast"]["direction"] = "bearish"
            factors.append({"factor": "CME日経先物", "impact": "negative",
                           "detail": f"CME日経先物は大証比{diff:+,.0f}円（{diff_pct:+.2f}%）。やや安寄りの見通し。"})
            bearish_points += 1

    # ── Commodities ──
    crude = market_data.get("crude_oil", {})
    gold = market_data.get("gold", {})
    if crude.get("change_pct") and abs(crude["change_pct"]) > 2:
        c_pct = crude["change_pct"]
        if c_pct > 0:
            factors.append({"factor": "原油", "impact": "mixed",
                           "detail": f"WTI原油が{c_pct:+.1f}%上昇。エネルギー株にプラスだが、輸入コスト増の懸念も。"})
        else:
            factors.append({"factor": "原油", "impact": "mixed",
                           "detail": f"WTI原油が{c_pct:+.1f}%下落。エネルギー株に逆風だが、コスト低減は内需に好材料。"})

    if gold.get("change_pct") and abs(gold["change_pct"]) > 1.5:
        g_pct = gold["change_pct"]
        if g_pct > 0:
            factors.append({"factor": "金", "impact": "mixed",
                           "detail": f"金価格が{g_pct:+.1f}%上昇。安全資産需要の高まりを示唆。"})

    # ── Macro Data (Bond Yields, DXY) ──
    us10y = macro_data.get("us_10y_yield")
    if us10y and us10y > 4.5:
        factors.append({"factor": "米金利", "impact": "negative",
                       "detail": f"米10年債利回りが{us10y:.2f}%と高水準。グロース株への重荷に。"})
        commentary_parts.append(
            f"米国10年債利回りは{us10y:.2f}%と高水準を維持。"
            f"金利上昇局面ではPERの高いグロース株が理論的な株価下落圧力を受けやすく、"
            f"バリュー株や高配当株への選好が強まる可能性がある。"
        )

    analysis["key_factors"] = factors

    # ── Generate Summary ──
    net_score = bullish_points - bearish_points
    if net_score >= 3:
        analysis["summary"] = (
            "マクロ環境は強気。複数のポジティブ要因が重なっており、"
            "積極的なリスクテイクが可能な局面。上昇局面では利益確定の目標を引き上げることも検討したい。"
        )
        if analysis["market_forecast"]["direction"] == "neutral":
            analysis["market_forecast"]["direction"] = "bullish"
    elif net_score >= 1:
        analysis["summary"] = (
            "マクロ環境はやや強気。下支え要因が優勢であり、"
            "押し目買いのスタンスが有効な局面と判断される。"
        )
    elif net_score <= -3:
        analysis["summary"] = (
            "マクロ環境は明確に弱気。複数のリスク要因が顕在化しており、"
            "ポジション縮小と厳格なリスク管理が不可欠。新規のスイングポジションは慎重に。"
        )
        if analysis["market_forecast"]["direction"] == "neutral":
            analysis["market_forecast"]["direction"] = "bearish"
    elif net_score <= -1:
        analysis["summary"] = (
            "マクロ環境に懸念材料あり。慎重なポジション管理を推奨。"
            "損切りラインの遵守を徹底し、ポジションサイズは控えめに。"
        )
    else:
        analysis["summary"] = (
            "マクロ環境は強弱材料が混在。市場全体の方向感は不透明であり、"
            "個別銘柄のテクニカル・ファンダメンタルズに基づいた選別が重要な局面。"
        )

    analysis["detailed_commentary"] = " ".join(commentary_parts)
    analysis["market_forecast"]["confidence"] = (
        "high" if abs(net_score) >= 3 else "moderate" if abs(net_score) >= 1 else "low"
    )

    return analysis
