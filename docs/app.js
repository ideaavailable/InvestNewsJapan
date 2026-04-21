/**
 * InvestNews Japan - Frontend Application
 * Loads daily report JSON, renders all sections, handles i18n.
 * Enhanced with sentiment dashboard, sector rotation, risk management,
 * mobile navigation, section accordion, and pick card toggle.
 */

// === i18n ===
const I18N = {
  ja: {
    loading: "データを読み込み中...",
    status_premarket: "プレマーケット",
    section_market: "マーケットサマリー",
    section_sentiment: "市場センチメント",
    section_macro: "グローバルマクロ概況",
    section_forecast: "本日の市場見通し",
    section_sector: "セクター分析",
    section_rotation: "セクターローテーション",
    section_daytrade: "デイトレード推奨銘柄",
    section_swing: "スイングトレード推奨銘柄",
    section_risk: "リスク管理ダッシュボード",
    section_method: "分析手法",
    footer_archive: "過去のレポート",
    footer_disclaimer: "免責事項",
    entry: "エントリー", target: "目標値", stop: "損切り",
    rr: "R/R比", score: "スコア", holding: "保有期間",
    technical: "テクニカル", fundamental: "ファンダメンタルズ",
    catalyst: "カタリスト", volume: "出来高分析",
    risk_level: "リスクレベル", methodology: "使用指標",
    screening: "スクリーニング", data_source: "データソース",
    section_performance: "デイトレード実績（¥10M シミュレーション）",
    perf_capital: "現在資金", perf_pnl: "累積損益", perf_return: "累積利回り",
    perf_winrate: "勝率", perf_pf: "PF", perf_dd: "最大DD",
    no_data: "データが見つかりません。バックエンドを実行してレポートを生成してください。",
    disclaimer_title: "⚠️ リスク警告・免責事項",
    nikkei225: "日経平均", topix: "TOPIX", mothers: "マザーズ",
    sp500: "S&P 500", nasdaq: "NASDAQ", dow: "NYダウ",
    vix: "VIX恐怖指数", usdjpy: "USD/JPY", eurjpy: "EUR/JPY",
    crude_oil: "原油(WTI)", gold: "金(GOLD)", cme_nikkei: "CME日経先物",
    mtf: "マルチタイムフレーム",
  },
  en: {
    loading: "Loading data...",
    status_premarket: "Pre-Market",
    section_market: "Market Summary",
    section_sentiment: "Market Sentiment",
    section_macro: "Global Macro Overview",
    section_forecast: "Today's Market Outlook",
    section_sector: "Sector Analysis",
    section_rotation: "Sector Rotation",
    section_daytrade: "Day Trade Recommendations",
    section_swing: "Swing Trade Recommendations",
    section_risk: "Risk Management Dashboard",
    section_method: "Methodology",
    footer_archive: "Archives",
    footer_disclaimer: "Disclaimer",
    entry: "Entry", target: "Target", stop: "Stop Loss",
    rr: "R/R Ratio", score: "Score", holding: "Holding Period",
    technical: "Technical", fundamental: "Fundamentals",
    catalyst: "Catalyst", volume: "Volume Analysis",
    risk_level: "Risk Level", methodology: "Indicators Used",
    screening: "Screening", data_source: "Data Source",
    section_performance: "Daytrade Performance (¥10M Sim)",
    perf_capital: "Capital", perf_pnl: "Cumulative P&L", perf_return: "Return",
    perf_winrate: "Win Rate", perf_pf: "PF", perf_dd: "Max DD",
    no_data: "No data found. Please run the backend to generate a report.",
    disclaimer_title: "⚠️ Risk Warning & Disclaimer",
    nikkei225: "Nikkei 225", topix: "TOPIX", mothers: "Mothers",
    sp500: "S&P 500", nasdaq: "NASDAQ", dow: "DOW",
    vix: "VIX", usdjpy: "USD/JPY", eurjpy: "EUR/JPY",
    crude_oil: "Crude Oil", gold: "Gold", cme_nikkei: "CME Nikkei",
    mtf: "Multi-Timeframe",
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

// === Mobile Navigation ===
function openMobileNav() { document.getElementById("mobileNav").classList.add("open"); }
function closeMobileNav() { document.getElementById("mobileNav").classList.remove("open"); }

// === Section Accordion ===
function toggleSection(sectionId) {
  const body = document.getElementById(sectionId + "Body");
  const toggle = body?.previousElementSibling?.querySelector(".section-toggle");
  if (!body) return;
  body.classList.toggle("collapsed");
  if (toggle) toggle.classList.toggle("collapsed");
}

// === Pick Card Toggle (mobile) ===
function togglePickBody(el) {
  const body = el.nextElementSibling;
  if (body) body.classList.toggle("collapsed");
}

// === Bottom Nav Active State ===
function updateBottomNav() {
  const sections = document.querySelectorAll(".section[id]");
  const navLinks = document.querySelectorAll(".bottom-nav a");
  let current = "";
  sections.forEach(section => {
    const top = section.getBoundingClientRect().top;
    if (top < 200) current = "#" + section.id;
  });
  navLinks.forEach(link => {
    link.classList.toggle("active", link.getAttribute("href") === current);
  });
}
window.addEventListener("scroll", updateBottomNav, { passive: true });

// === Data Loading ===
async function loadReport() {
  try {
    const indexResp = await fetch(`data/index.json?t=${Date.now()}`);
    if (indexResp.ok) {
      const dates = await indexResp.json();
      for (const dateStr of dates) {
        try {
          const resp = await fetch(`data/report-${dateStr}.json?t=${Date.now()}`);
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
    }
  } catch (e) { /* index.json fetch failed */ }
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
  renderSentiment(data.sentiment);
  renderMacro(data.macro_outlook);
  renderForecast(data.macro_outlook, data.market_summary);
  loadPerformance();
  renderSectorHeatmap(data.sector_analysis);
  renderSectorRotation(data.sector_rotation);
  renderPicks("daytradeGrid", data.daytrade_picks, "daytrade");
  renderPicks("swingGrid", data.swing_picks, "swing");
  renderRiskDashboard(data.risk_dashboard);
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
  const items = ["nikkei225", "topix", "sp500", "nasdaq", "dow", "usdjpy", "eurjpy", "vix", "crude_oil", "gold", "cme_nikkei"];
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

// === NEW: Sentiment Dashboard ===
function renderSentiment(sentiment) {
  const grid = document.getElementById("sentimentGrid");
  if (!sentiment) { grid.innerHTML = ""; return; }
  const fgScore = sentiment.fear_greed_index || 50;
  const fgLabel = sentiment.overall || "中立";
  const breadth = sentiment.market_breadth || {};
  const adv = breadth.advancing || 0;
  const dec = breadth.declining || 0;
  const total = adv + dec || 1;
  const advPct = (adv / total * 100).toFixed(0);
  const decPct = (dec / total * 100).toFixed(0);

  grid.innerHTML = `
    <div class="fear-greed-gauge">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Fear & Greed Index</div>
      <div class="fg-score">${fgScore}</div>
      <div class="fg-label">${fgLabel}</div>
      <div class="fg-bar"><div class="fg-indicator" style="left:${fgScore}%"></div></div>
      <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:10px;color:var(--text-muted);">
        <span>😨 極度の恐怖</span><span>😊 極度の強気</span>
      </div>
    </div>
    <div class="breadth-card">
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">マーケット・ブレッドス</div>
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
        <span class="positive-text">上昇 ${adv}銘柄（${advPct}%）</span>
        <span class="negative-text">下落 ${dec}銘柄（${decPct}%）</span>
      </div>
      <div class="breadth-bar-container">
        <div class="breadth-advance" style="width:${advPct}%"></div>
        <div class="breadth-decline" style="width:${decPct}%"></div>
      </div>
      <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;">
        <div><span style="color:var(--text-muted);">VIX</span> <span style="color:var(--text);font-family:var(--mono);font-weight:600;">${sentiment.vix_level ? sentiment.vix_level.toFixed(1) : 'N/A'}</span></div>
        <div><span style="color:var(--text-muted);">複合スコア</span> <span style="color:var(--text);font-family:var(--mono);font-weight:600;">${sentiment.combined_score ? sentiment.combined_score.toFixed(3) : '0'}</span></div>
      </div>
    </div>`;
}

function renderMacro(macro) {
  const el = document.getElementById("macroContent");
  if (!macro) { el.innerHTML = "<p>データなし</p>"; return; }
  let html = `<p style="margin-bottom:20px;font-weight:500;">${macro.summary || ""}</p>`;
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
  if (macro.detailed_commentary) {
    html += `<div style="margin-top:20px;padding-top:20px;border-top:1px solid var(--border);">
      <h4 style="font-size:13px;color:var(--accent);margin-bottom:10px;font-weight:600;">📝 詳細解説</h4>
      <p style="font-size:13px;color:var(--text-secondary);line-height:2;">${macro.detailed_commentary}</p>
    </div>`;
  }
  el.innerHTML = html;
}

function renderForecast(macro, market) {
  const el = document.getElementById("forecastContent");
  const forecast = macro?.market_forecast || {};
  const dir = forecast.direction || "neutral";
  const conf = forecast.confidence || "low";
  const dirText = { bullish: "強気（高寄り予想）", bearish: "弱気（安寄り予想）", neutral: "中立" };
  const confText = { high: "確信度：高", moderate: "確信度：中", low: "確信度：低" };
  const dirColor = dir === 'bullish' ? 'var(--green)' : dir === 'bearish' ? 'var(--red)' : 'var(--text-secondary)';
  let html = `<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:16px;">
    <span style="font-size:24px;font-weight:800;letter-spacing:-0.03em;color:${dirColor}">
      ${dir === "bullish" ? "↑" : dir === "bearish" ? "↓" : "→"} ${dirText[dir] || dir}
    </span>
    <span style="font-size:11px;padding:3px 10px;border-radius:100px;background:var(--bg-elevated);color:var(--text-muted);">${confText[conf] || conf}</span>
  </div>`;
  const cme = market?.cme_nikkei;
  const nikkei = market?.nikkei225;
  if (cme && cme.close && nikkei && nikkei.close) {
    const diff = cme.close - nikkei.close;
    const diffPct = (diff / nikkei.close * 100).toFixed(2);
    const sign = diff >= 0 ? "+" : "";
    html += `<p style="font-size:13px;color:var(--text-secondary);line-height:1.8;">
      CME日経先物: <strong style="color:var(--text);font-family:var(--mono);">${fmtNum(cme.close)}</strong>
      （大証比 <span style="color:${diff >= 0 ? 'var(--green)' : 'var(--red)'}">${sign}${fmtNum(diff)}円 / ${sign}${diffPct}%</span>）
    </p>`;
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

// === NEW: Sector Rotation ===
function renderSectorRotation(rotation) {
  const el = document.getElementById("rotationContent");
  if (!rotation) { el.innerHTML = "<p style='color:var(--text-muted)'>データなし</p>"; return; }
  const phase = rotation.economic_phase || {};
  let html = `<div class="phase-badge">📊 ${phase.phase || "unknown"}</div>
    <p style="font-size:14px;color:var(--text-secondary);margin-bottom:16px;">${phase.description || ""}</p>`;
  if (phase.favored_sectors && phase.favored_sectors.length) {
    html += `<div style="margin-bottom:16px;"><span style="font-size:12px;color:var(--text-muted);">注目セクター：</span>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">${phase.favored_sectors.map(s => `<span class="method-tag">${s}</span>`).join("")}</div></div>`;
  }
  const signals = rotation.rotation_signals || [];
  if (signals.length) {
    html += `<div style="margin-top:12px;">`;
    signals.forEach(sig => {
      const icon = sig.direction === "inflow" ? "🟢" : "🔴";
      html += `<div class="rotation-signal">${icon} ${sig.comment}</div>`;
    });
    html += `</div>`;
  }
  el.innerHTML = html;
}

// === NEW: Risk Dashboard ===
function renderRiskDashboard(risk) {
  const el = document.getElementById("riskContent");
  if (!risk) { el.innerHTML = "<p style='color:var(--text-muted)'>データなし</p>"; return; }
  const ps = risk.position_sizing || {};
  const pr = risk.portfolio_risk || {};
  const rm = risk.risk_metrics || {};
  let html = `<div class="risk-grid">
    <div class="risk-card"><div class="risk-title">VIXレジーム</div><div class="risk-value">${(ps.regime || "N/A").toUpperCase()}</div><div class="risk-detail">VIX ${risk.vix_level || "N/A"}</div></div>
    <div class="risk-card"><div class="risk-title">推奨ポジション</div><div class="risk-value">¥${(ps.per_pick_amount || 0).toLocaleString()}</div><div class="risk-detail">1銘柄あたり (${ps.per_pick_fraction || 0}%)</div></div>
    <div class="risk-card"><div class="risk-title">最大損失</div><div class="risk-value negative-text">¥${(ps.max_loss_scenario?.max_loss || 0).toLocaleString()}</div><div class="risk-detail">全損切りシナリオ</div></div>
    <div class="risk-card"><div class="risk-title">Kelly比率</div><div class="risk-value">${ps.safe_kelly || 0}%</div><div class="risk-detail">Half Kelly</div></div>
    <div class="risk-card"><div class="risk-title">分散スコア</div><div class="risk-value">${pr.diversification_score || 0}</div><div class="risk-detail">/100</div></div>
    <div class="risk-card"><div class="risk-title">シャープレシオ</div><div class="risk-value">${rm.sharpe_ratio || "N/A"}</div><div class="risk-detail">${rm.trading_days || 0}日間</div></div>
  </div>`;
  if (ps.recommendation) {
    html += `<p style="font-size:13px;color:var(--text-secondary);line-height:1.8;margin-bottom:16px;">${ps.recommendation}</p>`;
  }
  const warnings = pr.warnings || [];
  if (warnings.length) {
    html += `<div style="margin-top:12px;">`;
    warnings.forEach(w => {
      html += `<div style="font-size:13px;color:var(--text-secondary);padding:8px 0;border-top:1px solid var(--border);">${w.message}</div>`;
    });
    html += `</div>`;
  }
  el.innerHTML = html;
}

function renderPicks(containerId, picks, type) {
  const grid = document.getElementById(containerId);
  if (!picks || picks.length === 0) {
    grid.innerHTML = `<p style="color:var(--text-muted);padding:20px;">推奨銘柄なし</p>`;
    return;
  }
  const isMobile = window.innerWidth <= 768;
  grid.innerHTML = picks.map((pick, idx) => {
    const rr = pick.risk_reward_ratio || 0;
    const rrClass = rr >= 2 ? "good" : rr >= 1.5 ? "moderate" : "poor";
    const conf = pick.confidence || "medium";
    const confLabel = conf === "high" ? "高確信" : conf === "medium" ? "中確信" : "低確信";
    // Quick signal tags
    let signalTags = "";
    if (pick.rationale?.quick_signals?.length) {
      signalTags = `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px;">${pick.rationale.quick_signals.map(s => `<span class="method-tag">${s}</span>`).join("")}</div>`;
    }
    // Detailed rationale
    let rationaleHtml = "";
    if (pick.rationale) {
      if (pick.rationale.technical)
        rationaleHtml += `<div style="margin-bottom:10px;"><strong style="color:var(--accent);font-size:12px;">${t("technical")}</strong><p>${pick.rationale.technical}</p></div>`;
      if (pick.rationale.fundamental)
        rationaleHtml += `<div style="margin-bottom:10px;"><strong style="color:var(--accent);font-size:12px;">${t("fundamental")}</strong><p>${pick.rationale.fundamental}</p></div>`;
      if (pick.rationale.volume_analysis)
        rationaleHtml += `<div style="margin-bottom:10px;"><strong style="color:var(--accent);font-size:12px;">${t("volume")}</strong><p>${pick.rationale.volume_analysis}</p></div>`;
      if (pick.rationale.entry_strategy)
        rationaleHtml += `<div style="margin-bottom:10px;"><strong style="color:var(--accent);font-size:12px;">売買戦略</strong><p>${pick.rationale.entry_strategy}</p></div>`;
      if (pick.rationale.mtf_context)
        rationaleHtml += `<div style="margin-bottom:10px;"><strong style="color:var(--accent);font-size:12px;">${t("mtf")}</strong><p>${pick.rationale.mtf_context}</p></div>`;
    }
    let fundHtml = "";
    if (type === "swing" && pick.fundamentals) {
      const f = pick.fundamentals;
      const items = [];
      if (f.per) items.push(`<span class="fund-item"><span class="fund-label">PER</span> <span class="fund-value">${f.per.toFixed(1)}</span></span>`);
      if (f.pbr) items.push(`<span class="fund-item"><span class="fund-label">PBR</span> <span class="fund-value">${f.pbr.toFixed(2)}</span></span>`);
      if (f.roe) items.push(`<span class="fund-item"><span class="fund-label">ROE</span> <span class="fund-value">${f.roe.toFixed(1)}%</span></span>`);
      if (f.ev_ebitda) items.push(`<span class="fund-item"><span class="fund-label">EV/EBITDA</span> <span class="fund-value">${f.ev_ebitda.toFixed(1)}</span></span>`);
      if (f.roic) items.push(`<span class="fund-item"><span class="fund-label">ROIC</span> <span class="fund-value">${f.roic.toFixed(1)}%</span></span>`);
      if (f.dividend_yield && f.dividend_yield < 20) items.push(`<span class="fund-item"><span class="fund-label">配当</span> <span class="fund-value">${f.dividend_yield.toFixed(1)}%</span></span>`);
      if (items.length) fundHtml = `<div class="fundamentals-row">${items.join("")}</div>`;
    }
    let holdingHtml = "";
    if (type === "swing" && pick.holding_period) {
      holdingHtml = `<p style="font-size:12px;color:var(--text-muted);margin-top:8px;">${t("holding")}: ${pick.holding_period}</p>`;
    }
    return `<div class="pick-card">
      <div class="pick-header" onclick="togglePickBody(this)">
        <div class="pick-stock-info">
          <h3><span class="stock-code">${pick.code}</span> ${pick.name}</h3>
          <div class="pick-sector">${pick.sector}</div>
        </div>
        <div class="pick-meta">
          <span class="confidence-badge ${conf}">${confLabel}</span>
          <div class="pick-score">${pick.score}</div>
        </div>
      </div>
      <div class="pick-body${isMobile && idx > 0 ? ' collapsed' : ''}">
        ${signalTags}
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
    html += `<h3 style="color:var(--accent);font-size:15px;margin-bottom:8px;">${t("methodology")}</h3>`;
    html += `<div class="method-list">${method.technical_indicators.map(i => `<span class="method-tag">${i}</span>`).join("")}</div>`;
  }
  if (method.screening_process) {
    html += `<h3 style="color:var(--accent);font-size:15px;margin:20px 0 8px;">${t("screening")}</h3>`;
    html += `<p style="color:var(--text-secondary);font-size:14px;">${method.screening_process}</p>`;
  }
  if (method.risk_management) {
    html += `<h3 style="color:var(--accent);font-size:15px;margin:20px 0 8px;">リスク管理</h3>`;
    html += `<p style="color:var(--text-secondary);font-size:14px;">${method.risk_management}</p>`;
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

// === Performance ===
async function loadPerformance() {
  try {
    const resp = await fetch(`data/performance.json?t=${Date.now()}`);
    if (!resp.ok) return;
    const data = await resp.json();
    renderPerformance(data);
  } catch (e) { /* no performance data yet */ }
}

function renderPerformance(perf) {
  const section = document.getElementById("sectionPerformance");
  const el = document.getElementById("performanceContent");
  if (!perf || perf.total_trades === 0) return;
  section.style.display = "block";

  const total = perf.total_trades;
  const wins = perf.wins;
  const winRate = total > 0 ? (wins / total * 100).toFixed(1) : "0.0";
  const pnl = perf.current_capital - perf.initial_capital;
  const returnPct = (pnl / perf.initial_capital * 100).toFixed(2);
  const pf = perf.total_loss > 0 ? (perf.total_profit / perf.total_loss).toFixed(2) : "-";
  const ddPct = perf.peak_capital > 0 ? (perf.max_drawdown / perf.peak_capital * 100).toFixed(1) : "0";
  const pnlClass = pnl >= 0 ? "positive-text" : "negative-text";

  let html = `<div class="perf-grid">
    <div class="market-card"><div class="card-label">${t("perf_capital")}</div><div class="card-value" style="font-size:18px;">¥${perf.current_capital.toLocaleString()}</div></div>
    <div class="market-card"><div class="card-label">${t("perf_pnl")}</div><div class="card-value ${pnlClass}" style="font-size:18px;">¥${pnl >= 0 ? "+" : ""}${pnl.toLocaleString()}</div></div>
    <div class="market-card"><div class="card-label">${t("perf_return")}</div><div class="card-value ${pnlClass}" style="font-size:18px;">${pnl >= 0 ? "+" : ""}${returnPct}%</div></div>
    <div class="market-card"><div class="card-label">${t("perf_winrate")}</div><div class="card-value" style="font-size:18px;">${winRate}%</div><div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${wins}W / ${perf.losses}L</div></div>
    <div class="market-card"><div class="card-label">${t("perf_pf")}</div><div class="card-value" style="font-size:18px;">${pf}</div></div>
    <div class="market-card"><div class="card-label">${t("perf_dd")}</div><div class="card-value negative-text" style="font-size:18px;">-${ddPct}%</div></div>
  </div>`;

  // Daily P&L bar chart
  const daily = perf.daily_results || [];
  if (daily.length > 0) {
    const maxAbs = Math.max(...daily.map(d => Math.abs(d.day_pnl)), 1);
    html += `<h4 style="font-size:13px;color:var(--text-muted);margin-bottom:12px;">日次損益推移</h4>`;
    html += `<div class="pnl-chart">`;
    daily.forEach(d => {
      const h = Math.max(2, Math.abs(d.day_pnl) / maxAbs * 70);
      const color = d.day_pnl >= 0 ? "var(--green)" : "var(--red)";
      const tooltip = `${d.date}: ¥${d.day_pnl >= 0 ? "+" : ""}${d.day_pnl.toLocaleString()}`;
      html += `<div title="${tooltip}" style="flex:1;background:${color};height:${h}px;border-radius:2px;opacity:0.7;min-width:4px;"></div>`;
    });
    html += `</div>`;

    // Recent trade details
    const latest = daily[daily.length - 1];
    if (latest && latest.trades && latest.trades.length > 0) {
      html += `<h4 style="font-size:13px;color:var(--text-muted);margin:20px 0 8px;">直近の取引結果（${latest.eval_date}）</h4>`;
      html += `<div style="display:grid;gap:6px;">`;
      latest.trades.forEach(tr => {
        const cls = tr.result === "win" ? "positive" : "negative";
        html += `<div class="trade-row">
          <span><strong>${tr.code}</strong> ${tr.name}</span>
          <span style="font-family:var(--mono);">¥${tr.entry.toLocaleString()} → ¥${tr.exit.toLocaleString()}</span>
          <span class="${cls}-text" style="font-family:var(--mono);font-weight:600;">¥${tr.pnl >= 0 ? "+" : ""}${tr.pnl.toLocaleString()} (${tr.pnl_pct >= 0 ? "+" : ""}${tr.pnl_pct}%)</span>
        </div>`;
      });
      html += `</div>`;
    }
  }

  el.innerHTML = html;
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
