"""Report templates - sector analysis helpers."""
import logging

logger = logging.getLogger("investnews.templates")


def build_sector_analysis(tech_results, stock_universe):
    """Build sector performance heatmap data."""
    sector_map = {}
    for code, name, sector in stock_universe:
        ticker = f"{code}.T"
        if ticker in tech_results:
            tech = tech_results[ticker]
            change = tech.get("daily_change_pct", 0)
            if change is not None:
                if sector not in sector_map:
                    sector_map[sector] = {"changes": [], "stocks": []}
                sector_map[sector]["changes"].append(change)
                sector_map[sector]["stocks"].append({"code": code, "name": name, "change": change})

    heatmap = {}
    focus_sectors = []
    for sector, data in sector_map.items():
        changes = data["changes"]
        if not changes:
            continue
        avg = sum(changes) / len(changes)
        heatmap[sector] = round(avg, 2)
        top_stocks = sorted(data["stocks"], key=lambda x: abs(x.get("change", 0)), reverse=True)[:3]
        if abs(avg) > 1.0:
            direction = "上昇" if avg > 0 else "下落"
            focus_sectors.append({
                "sector": sector, "change_pct": round(avg, 2), "direction": direction,
                "reason": f"セクター全体が{direction}傾向（平均{avg:+.2f}%）",
                "notable_stocks": top_stocks,
            })

    focus_sectors.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return {"heatmap": heatmap, "focus_sectors": focus_sectors[:5]}
