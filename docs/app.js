/**
 * InvestNews Japan - Frontend Application
 * Loads daily report JSON, renders all sections, handles i18n.
 */

// === i18n ===
const I18N = {
  ja: {
    loading: "データを読み込み中...",
    status_premarket: "プレマーケット",
    section_market: "マーケットサマリー",
    section_macro: "グローバルマクロ概況",
    section_forecast: "本日の市場見通し",
    section_sector: "セクター分析",
    section_daytrade: "デイトレード推奨銘柄",
    section_swing: "スイングトレード推奨銘柄",
    section_method: "分析手法",
    footer_archive: "過去のレポート",
    footer_disclaimer: "免責事項",
    entry: "エントリー", target: "目標値", stop: "損切り",
    rr: "R/R比", score: "スコア", holding: "保有期間",
    technical: "テクニカル", fundamental: "ファンダメンタルズ",
    catalyst: "カタリスト", volume: "出来高分析",
    risk_level: "リスクレベル", methodology: "使用指標",
    screening: "スクリーニング", data_source: "データソース",
    no_data: "データが見つかりません。バックエンドを実行してレポートを生成してください。",
    disclaimer_title: "⚠️ リスク警告・免責事項",
    nikkei225: "日経平均", topix: "TOPIX", mothers: "マザーズ",
    sp500: "S&P 500", nasdaq: "NASDAQ", dow: "NYダウ",
    vix: "VIX恐怖指数", usdjpy: "USD/JPY", eurjpy: "EUR/JPY",
    crude_oil: "原油(WTI)", gold: "金(GOLD)", cme_nikkei: "CME日経先物",
  },
  en: {
    loading: "Loading data...",
    status_premarket: "Pre-Market",
    section_market: "Market Summary",
    section_macro: "Global Macro Overview",
    section_forecast: "Today's Market Outlook",
    section_sector: "Sector Analysis",
    section_daytrade: "Day Trade Recommendations",
    section_swing: "Swing Trade Recommendations",
    section_method: "Methodology",
    footer_archive: "Archives",
    footer_disclaimer: "Disclaimer",
    entry: "Entry", target: "Target", stop: "Stop Loss",
    rr: "R/R Ratio", score: "Score", holding: "Holding Period",
    technical: "Technical", fundamental: "Fundamentals",
    catalyst: "Catalyst", volume: "Volume Analysis",
    risk_level: "Risk Level", methodology: "Indicators Used",
    screening: "Screening", data_source: "Data Source",
    no_data: "No data found. Please run the backend to generate a report.",
    disclaimer_title: "⚠️ Risk Warning & Disclaimer",
    nikkei225: "Nikkei 225", topix: "TOPIX", mothers: "Mothers",
    sp500: "S&P 500", nasdaq: "NASDAQ", dow: "DOW",
    vix: "VIX", usdjpy: "USD/JPY", eurjpy: "EUR/JPY",
    crude_oil: "Crude Oil", gold: "Gold", cme_nikkei: "CME Nikkei",
  }
};
let currentLang = "ja";

function t(key) { return (I18N[currentLang] && I18N[currentLang][key]) || key; }

function setLang(lang) {
  currentLang = lang;
  document.querySelectorAll(".lang-toggle button").forEach(btn => {
    btn.classList.toggle("active", btn.textContent.trim() === (lang === "ja" ? "JP" : "EN"));
  });
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  if (window._reportData) renderReport(window._reportData);
}

// === Data Loading ===
async function loadReport() {
  const today = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    try {
      const resp = await fetch(`data/report-${dateStr}.json`);
      if (resp.ok) {
        const data = await resp.json();
        window._reportData = data;
        document.getElementById("loadingState").style.display = "none";
        document.getElementById("reportContent").style.display = "block";
        renderReport(data);
        return;
      }
    } catch (e) { /* try next date */ }
  }
  document.getElementById("loadingState").innerHTML =
    `<div style="text-align:center;color:var(--text-secondary);padding:60px 20px;">
      <div style="font-size:48px;margin-bottom:16px;">📊</div>
      <p>${t("no_data")}</p>
      <p style="margin-top:12px;font-size:13px;color:var(--text-muted);">python backend/main.py --force</p>
    </div>`;
}

// === Rendering ===
function renderReport(data) {
  renderDate(data);
  renderTicker(data.market_summary);
  renderMarketGrid(data.market_summary);
  renderMacro(data.macro_outlook);
  renderForecast(data.macro_outlook, data.market_summary);
  renderSectorHeatmap(data.sector_analysis);
  renderPicks("daytradeGrid", data.daytrade_picks, "daytrade");
  renderPicks("swingGrid", data.swing_picks, "swing");
  renderMethodology(data.methodology);
  renderDisclaimer(data.disclaimer);
}

function renderDate(data) {
  const d = data.report_date;
  const gen = data.generated_at;
  document.getElementById("reportDate").textContent = `${d} ${gen ? gen.split("T")[1]?.substring(0, 5) + " JST" : ""}`;
}

function renderTicker(market) {
  const track = document.getElementById("tickerTrack");
  if (!market) return;
  const items = ["nikkei225", "topix", "sp500", "nasdaq", "dow", "usdjpy", "eurjpy", "vix", "crude_oil", "gold"];
  let html = "";
  for (let pass = 0; pass < 2; pass++) {
    items.forEach(key => {
      const d = market[key];
      if (!d || d.close === null) return;
      const cls = (d.change_pct || 0) >= 0 ? "positive" : "negative";
      const sign = (d.change_pct || 0) >= 0 ? "+" : "";
      html += `<div class="ticker-item">
        <span class="label">${t(key)}</span>
        <span class="value">${fmtNum(d.close)}</span>
        <span class="change ${cls}">${sign}${(d.change_pct || 0).toFixed(2)}%</span>
      </div>`;
    });
  }
  track.innerHTML = html;
}

function renderMarketGrid(market) {
  const grid = document.getElementById("marketGrid");
  if (!market) { grid.innerHTML = "<p>データなし</p>"; return; }
  const items = [
    "nikkei225", "topix", "sp500", "nasdaq", "dow",
    "usdjpy", "eurjpy", "vix", "crude_oil", "gold", "cme_nikkei",
  ];
  grid.innerHTML = items.map(key => {
    const d = market[key];
    if (!d || d.close === null) return "";
    const cls = (d.change_pct || 0) >= 0 ? "positive" : "negative";
    const sign = (d.change_pct || 0) >= 0 ? "+" : "";
    return `<div class="market-card">
      <div class="card-label">${t(key)}</div>
      <div class="card-value">${fmtNum(d.close)}</div>
      <div class="card-change ${cls}-text">${sign}${(d.change_pct || 0).toFixed(2)}%</div>
    </div>`;
  }).join("");
}

function renderMacro(macro) {
  const el = document.getElementById("macroContent");
  if (!macro) { el.innerHTML = "<p>データなし</p>"; return; }
  let html = `<p style="margin-bottom:20px;">${macro.summary || ""}</p>`;
  const risk = macro.risk_level || "moderate";
  const riskColor = risk === 'low' ? 'var(--green)' : risk === 'high' ? 'var(--red)' : 'var(--amber)';
  html += `<div class="risk-meter">
    <span style="font-size:12px;color:var(--text-muted);">${t("risk_level")}</span>
    <div class="risk-bar"><div class="risk-fill ${risk}"></div></div>
    <span class="risk-label" style="color:${riskColor}">${risk.toUpperCase()}</span>
  </div>`;
  if (macro.key_factors && macro.key_factors.length > 0) {
    html += `<ul class="factor-list">`;
    macro.key_factors.forEach(f => {
      html += `<li class="factor-item">
        <span class="factor-badge ${f.impact}">${f.factor}</span>
        <span>${f.detail}</span>
      </li>`;
    });
    html += `</ul>`;
  }
  el.innerHTML = html;
}

function renderForecast(macro, market) {
  const el = document.getElementById("forecastContent");
  const forecast = macro?.market_forecast || {};
  const dir = forecast.direction || "neutral";
  const dirText = { bullish: "強気（高寄り予想）", bearish: "弱気（安寄り予想）", neutral: "中立" };
  const dirColor = dir === 'bullish' ? 'var(--green)' : dir === 'bearish' ? 'var(--red)' : 'var(--text-secondary)';
  let html = `<div style="display:flex;gap:16px;align-items:center;margin-bottom:16px;">
    <span style="font-size:24px;font-weight:800;letter-spacing:-0.03em;color:${dirColor}">
      ${dir === "bullish" ? "↑" : dir === "bearish" ? "↓" : "→"} ${dirText[dir] || dir}
    </span>
  </div>`;
  const cme = market?.cme_nikkei;
  if (cme && cme.close) {
    html += `<p style="font-size:13px;color:var(--text-muted);">CME日経先物: <strong style="color:var(--text);font-family:var(--mono);">${fmtNum(cme.close)}</strong></p>`;
  }
  el.innerHTML = html;
}

function renderSectorHeatmap(sector) {
  const grid = document.getElementById("sectorHeatmap");
  if (!sector || !sector.heatmap) { grid.innerHTML = "<p>データなし</p>"; return; }
  const entries = Object.entries(sector.heatmap).sort((a, b) => b[1] - a[1]);
  grid.innerHTML = entries.map(([name, pct]) => {
    const intensity = Math.min(Math.abs(pct) / 3, 1);
    const bg = pct >= 0
      ? `rgba(0, 230, 118, ${0.1 + intensity * 0.3})`
      : `rgba(255, 23, 68, ${0.1 + intensity * 0.3})`;
    const color = pct >= 0 ? "var(--green)" : "var(--red)";
    const sign = pct >= 0 ? "+" : "";
    return `<div class="heatmap-cell" style="background:${bg}">
      <div class="sector-name">${name}</div>
      <div class="sector-change" style="color:${color}">${sign}${pct.toFixed(2)}%</div>
    </div>`;
  }).join("");
}

function renderPicks(containerId, picks, type) {
  const grid = document.getElementById(containerId);
  if (!picks || picks.length === 0) {
    grid.innerHTML = `<p style="color:var(--text-muted);padding:20px;">推奨銘柄なし</p>`;
    return;
  }
  grid.innerHTML = picks.map(pick => {
    const rr = pick.risk_reward_ratio || 0;
    const rrClass = rr >= 2 ? "good" : rr >= 1.5 ? "moderate" : "poor";
    let rationaleHtml = "";
    if (pick.rationale) {
      if (pick.rationale.technical)
        rationaleHtml += `<p><strong>${t("technical")}:</strong> ${pick.rationale.technical}</p>`;
      if (pick.rationale.fundamental)
        rationaleHtml += `<p><strong>${t("fundamental")}:</strong> ${pick.rationale.fundamental}</p>`;
      if (pick.rationale.volume_analysis)
        rationaleHtml += `<p><strong>${t("volume")}:</strong> ${pick.rationale.volume_analysis}</p>`;
    }
    let fundHtml = "";
    if (type === "swing" && pick.fundamentals) {
      const f = pick.fundamentals;
      const items = [];
      if (f.per) items.push(`<span class="fund-item"><span class="fund-label">PER</span> <span class="fund-value">${f.per.toFixed(1)}</span></span>`);
      if (f.pbr) items.push(`<span class="fund-item"><span class="fund-label">PBR</span> <span class="fund-value">${f.pbr.toFixed(2)}</span></span>`);
      if (f.roe) items.push(`<span class="fund-item"><span class="fund-label">ROE</span> <span class="fund-value">${f.roe.toFixed(1)}%</span></span>`);
      if (f.dividend_yield) items.push(`<span class="fund-item"><span class="fund-label">配当</span> <span class="fund-value">${f.dividend_yield.toFixed(1)}%</span></span>`);
      if (items.length) fundHtml = `<div class="fundamentals-row">${items.join("")}</div>`;
    }
    let holdingHtml = "";
    if (type === "swing" && pick.holding_period) {
      holdingHtml = `<p style="font-size:12px;color:var(--text-muted);margin-top:8px;">${t("holding")}: ${pick.holding_period}</p>`;
    }
    return `<div class="pick-card">
      <div class="pick-header">
        <div class="pick-stock-info">
          <h3><span class="stock-code">${pick.code}</span> ${pick.name}</h3>
          <div class="pick-sector">${pick.sector}</div>
        </div>
        <div class="pick-score">${pick.score}</div>
      </div>
      <div class="pick-body">
        <div class="price-levels">
          <div class="price-level entry">
            <div class="level-label">${t("entry")}</div>
            <div class="level-value">¥${fmtNum(pick.entry_point)}</div>
          </div>
          <div class="price-level target">
            <div class="level-label">${t("target")}</div>
            <div class="level-value">¥${fmtNum(pick.target)}</div>
          </div>
          <div class="price-level stop">
            <div class="level-label">${t("stop")}</div>
            <div class="level-value">¥${fmtNum(pick.stop_loss)}</div>
          </div>
        </div>
        <div class="rr-badge ${rrClass}">${t("rr")}: ${rr.toFixed(2)}</div>
        <div class="rationale">${rationaleHtml}</div>
        ${fundHtml}
        ${holdingHtml}
      </div>
    </div>`;
  }).join("");
}

function renderMethodology(method) {
  const el = document.getElementById("methodContent");
  if (!method) { el.innerHTML = ""; return; }
  let html = "";
  if (method.technical_indicators) {
    html += `<h3 style="color:var(--gold);font-size:15px;margin-bottom:8px;">${t("methodology")}</h3>`;
    html += `<div class="method-list">${method.technical_indicators.map(i => `<span class="method-tag">${i}</span>`).join("")}</div>`;
  }
  if (method.screening_process) {
    html += `<h3 style="color:var(--gold);font-size:15px;margin:20px 0 8px;">${t("screening")}</h3>`;
    html += `<p style="color:var(--text-secondary);font-size:14px;">${method.screening_process}</p>`;
  }
  if (method.data_source) {
    html += `<p style="margin-top:12px;font-size:13px;color:var(--text-muted);">${t("data_source")}: ${method.data_source}</p>`;
  }
  el.innerHTML = html;
}

function renderDisclaimer(text) {
  const el = document.getElementById("disclaimerContent");
  el.innerHTML = `<h3>${t("disclaimer_title")}</h3><p>${text || ""}</p>`;
}

// === Helpers ===
function fmtNum(v) {
  if (v === null || v === undefined) return "N/A";
  if (typeof v === "string") return v;
  if (Math.abs(v) >= 1000) return v.toLocaleString("ja-JP", { maximumFractionDigits: 2 });
  return v.toFixed(2);
}

// === Init ===
document.addEventListener("DOMContentLoaded", loadReport);
