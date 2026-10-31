/* Oil Desk public page: renders data/oildesk.json (exported after every agent run). */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const fmtUsd = (n, d = 0) => "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const fmtNum = (n, d = 1) => Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ago = (iso) => {
    const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 90) return "just now";
    if (s < 5400) return Math.round(s / 60) + " min ago";
    if (s < 172800) return Math.round(s / 3600) + " h ago";
    return Math.round(s / 86400) + " days ago";
  };
  const short = (h) => (h ? h.slice(0, 8) + "…" + h.slice(-6) : "");
  const SIGNAL_NAMES = { volume: "Volume", cot: "COT positioning", inventories: "EIA inventories", crack: "Crack spread", dxy: "US dollar", curve: "Brent-WTI curve" };

  function callLabel(r) { return r.blocked ? "BLOCKED" : r.action; }
  function sizeText(r) {
    if (r.blocked || r.action === "HOLD") return "–";
    return r.action === "BUY" ? `${fmtUsd(r.amount_in)} → ${fmtNum(r.amount_out)} bbl` : `${fmtNum(r.amount_in)} bbl → ${fmtUsd(r.amount_out)}`;
  }
  function stripModel(reason) { return String(reason || "").replace(/^\[[^\]]*\]\s*/, ""); }
  function modelOf(reason) { const m = String(reason || "").match(/^\[([^\]]*)\]/); return m ? m[1] : ""; }

  function render(d) {
    $("sample").hidden = !d.sample;
    $("nav-repo").href = d.repo;
    if (d.streamlit) { $("nav-workbench").href = d.streamlit; $("nav-workbench").hidden = false; }
    const rec = (h) => `${d.repo}/blob/main/records/${String(h).replace(/^0x/, "")}.json`;
    const txUrl = (t) => `${d.explorer}/tx/${t}`;

    const rows = d.decisions || [];
    const last = rows[rows.length - 1];
    const netName = d.network === "hashkey" ? "HashKey Chain mainnet" : d.network === "hashkeyTestnet" ? "HashKey Chain testnet" : "local test chain";
    if (last) {
      $("status").textContent = d.sample ? `Sample replay on a ${netName} · ${rows.length} calls` : `Live on ${netName} · last call ${ago(last.time)}`;
      $("live-dot").classList.add("on");
      const lab = callLabel(last);
      $("l-action").textContent = last.blocked ? `BLOCKED ${last.action}` : lab;
      $("l-action").className = "pill " + lab;
      $("l-when").textContent = new Date(last.time).toUTCString().replace(" GMT", " UTC");
      $("l-reason").textContent = stripModel(last.reason) + (last.blocked ? ` (Mandate: ${last.blocked})` : "");
      $("l-price").textContent = fmtUsd(last.wti, 2);
      $("l-conf").textContent = last.confidence + "%";
      const model = modelOf(last.reason);
      $("l-proof").innerHTML = `<a href="${txUrl(last.tx)}" target="_blank" rel="noopener">Transaction ↗</a>` +
        (d.sample ? "" : `<a href="${rec(last.hash)}" target="_blank" rel="noopener">Full record ↗</a>`) +
        `<code title="keccak256 of the full decision record">${short(last.hash)}</code>` + (model ? `<span class="muted">model: ${esc(model)}</span>` : "");
    } else {
      $("status").textContent = d.vault ? `Deployed on ${netName} · waiting for the first call` : "Vault not deployed yet";
      $("l-action").hidden = true;
      $("l-reason").textContent = d.vault ? "The first call lands with the next agent run (every 3 hours)." : "The first call lands once the vault is live on HashKey Chain mainnet. Until then, the market view below is live.";
      $("l-price").textContent = d.now && d.now.view ? fmtUsd(d.now.view.wti_price, 2) : "–";
    }

    const s = d.stats;
    if (s) {
      $("k-hit").textContent = s.hit_rate == null ? "too early" : Math.round(s.hit_rate * 100) + "%";
      $("k-hit-sub").textContent = s.judged ? `${s.hits} of ${s.judged} trades right after 3 trading days` : "needs 3 trading days after the first trade";
      $("k-calls").textContent = s.calls;
      $("k-calls-sub").textContent = `${s.trades} trades · ${s.calls - s.trades - s.blocked} holds`;
      $("k-blocked").textContent = s.blocked;
    }
    if (d.book) {
      const pnl = d.book.value / d.book.start - 1;
      $("k-value").innerHTML = fmtUsd(d.book.value);
      $("k-value-sub").innerHTML = `<span class="${pnl >= 0 ? "up" : "down"}">${pnl >= 0 ? "+" : ""}${(pnl * 100).toFixed(1)}%</span> vs ${fmtUsd(d.book.start)} start · ${fmtNum(d.book.barrels)} bbl + ${fmtUsd(d.book.usd)}`;
    }

    // Signals now
    const v = d.now && d.now.view;
    if (v) {
      $("conf-total").textContent = (v.confluence_total > 0 ? "+" : "") + v.confluence_total + " / 6";
      $("conf-dir").textContent = v.confluence_direction;
      $("signals").innerHTML = Object.entries(v.signals || {}).map(([k, val]) =>
        `<li><span>${esc(SIGNAL_NAMES[k] || k)}</span><b class="v${val}">${val > 0 ? "+1" : val < 0 ? "−1" : "0"}</b></li>`).join("");
      const hr = v.audit_hit_rate;
      $("audit-line").textContent = `WTI ${fmtUsd(v.wti_price, 2)} (${v.asof})` +
        (hr != null ? ` · engine's own historical hit rate ${Math.round(hr * 100)}% over ${v.audit_signals} strong signals` : "") +
        (v.oil_volatility_ovx ? ` · oil volatility (OVX) ${fmtNum(v.oil_volatility_ovx)}` : "");
    }
    const crowd = (d.now && d.now.crowd) || [];
    $("crowd").innerHTML = crowd.length ? crowd.map((c) => {
      const yes = c.odds.Yes ?? Object.values(c.odds)[0];
      const pct = Math.round(yes * 100);
      return `<li><p class="q">${esc(c.question)}</p><div class="bar"><i style="width:${pct}%"></i></div>
        <div class="odds"><span>Yes ${pct}%</span><span>${c.volume_usd ? fmtUsd(c.volume_usd) + " traded" : ""}</span></div></li>`;
    }).join("") : `<li class="muted">No open oil markets right now.</li>`;

    // Mandate
    const m = d.mandate;
    $("mandate").innerHTML = m ? `<p class="label">Mandate enforced by the vault contract${m.paused ? " · PAUSED" : ""}</p>
      <div>Max buy <b>${fmtUsd(m.max_buy_usd)}</b></div><div>Max sell <b>${fmtNum(m.max_sell_bbl, 0)} bbl</b></div>
      <div>Daily cap <b>${fmtUsd(m.daily_usd)}</b> / <b>${fmtNum(m.daily_bbl, 0)} bbl</b></div><div>Max slippage <b>${m.slippage_pct}%</b></div>
      <div>Vault <a href="${d.explorer}/address/${d.vault}" target="_blank" rel="noopener"><code>${short(d.vault)}</code> ↗</a></div>` : `<p class="label">Mandate</p><div class="muted">Appears once the vault is deployed.</div>`;

    // Table: newest 10, with a button for the rest
    const SHOW = 10;
    const tableRows = (all) => (all ? rows : rows.slice(-SHOW)).slice().reverse();
    const drawRows = (all) => { $("rows").innerHTML = rowsHtml(tableRows(all)); };
    const rowsHtml = (list) => list.length ? list.map((r) => {
      const lab = callLabel(r);
      const res = r.right === true ? `<span class="res yes">✓ right</span>` : r.right === false ? `<span class="res no">✗ wrong</span>` : `<span class="res na">–</span>`;
      return `<tr><td class="num">${r.id}</td><td class="when">${esc(r.time.slice(0, 10))}<br>${esc(r.time.slice(11, 16))}</td>
        <td><span class="pill ${lab}">${r.blocked ? "BLOCKED " + r.action : lab}</span></td>
        <td class="num">${sizeText(r)}</td><td class="num">${fmtUsd(r.wti, 2)}</td><td class="num">${r.confidence}%</td><td>${res}</td>
        <td class="reason">${esc(stripModel(r.reason))}${r.blocked ? `<span class="why">Mandate: ${esc(r.blocked)}</span>` : ""}</td>
        <td class="proofcell"><a href="${txUrl(r.tx)}" target="_blank" rel="noopener">tx ↗</a>${d.sample ? "" : ` · <a href="${rec(r.hash)}" target="_blank" rel="noopener">record ↗</a>`}</td></tr>`;
    }).join("") : `<tr><td colspan="9" class="muted">No calls yet.</td></tr>`;
    drawRows(false);
    if (rows.length > SHOW) {
      const btn = $("more");
      btn.hidden = false;
      btn.textContent = `Show all ${rows.length} calls`;
      btn.onclick = () => { drawRows(true); btn.hidden = true; };
    }

    // Chart
    const prices = d.wti || [];
    const labels = prices.map((p) => p.d);
    const idx = Object.fromEntries(labels.map((l, i) => [l, i]));
    const series = { BUY: [], SELL: [], HOLD: [], BLOCKED: [] };
    for (const k in series) series[k] = labels.map(() => null);
    const meta = {};
    rows.forEach((r) => {
      const day = r.time.slice(0, 10);
      if (!(day in idx)) return;
      const k = callLabel(r);
      series[k][idx[day]] = r.wti;
      meta[k + day] = r;
    });
    $("chart-sub").textContent = labels.length ? `${labels[0]} to ${labels[labels.length - 1]} · daily close${d.sample ? " (sample)" : ""}` : "";
    if (window.Chart && labels.length) {
      const css = getComputedStyle(document.documentElement);
      const c = (n) => css.getPropertyValue(n).trim();
      const pts = (k, color, style, size) => ({
        type: "line", label: k, data: series[k], showLine: false, pointStyle: style, pointRadius: size, pointHoverRadius: size + 2,
        pointBackgroundColor: color, pointBorderColor: color, rotation: k === "SELL" ? 180 : 0,
      });
      new Chart($("chart"), {
        type: "line",
        data: {
          labels,
          datasets: [
            { label: "WTI", data: prices.map((p) => p.c), borderColor: c("--amber"), borderWidth: 2, pointRadius: 0, tension: 0.25, fill: { target: "origin", above: "rgba(245,165,36,0.06)" } },
            pts("BUY", c("--buy"), "triangle", 7), pts("SELL", c("--sell"), "triangle", 7),
            pts("HOLD", c("--hold"), "circle", 3.5), pts("BLOCKED", c("--blocked"), "crossRot", 7),
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false,
          interaction: { mode: "nearest", intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#151b23", borderColor: "#2a3440", borderWidth: 1, padding: 10, displayColors: false,
              callbacks: {
                title: (items) => items[0].label,
                label: (it) => {
                  if (it.datasetIndex === 0) return `WTI ${fmtUsd(it.parsed.y, 2)}`;
                  const r = meta[it.dataset.label + it.label];
                  return r ? [`${r.blocked ? "BLOCKED " + r.action : r.action} · ${r.confidence}%`, stripModel(r.reason).slice(0, 90)] : it.dataset.label;
                },
              },
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: c("--muted"), maxTicksLimit: window.innerWidth < 640 ? 4 : 8, maxRotation: 0,
              callback(v) { return new Date(this.getLabelForValue(v) + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }); } } },
            y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: c("--muted"), callback: (v) => "$" + v } },
          },
        },
      });
    }
    $("foot-updated").textContent = `Data updated ${ago(d.generated_at)} · ${new Date(d.generated_at).toUTCString().replace(" GMT", " UTC")}`;
  }

  // Live data by default. ?sample shows a replayed sample track record, which is
  // also the fallback when the live export is missing (e.g. before the mainnet deploy).
  const get = (f) => fetch("data/" + f, { cache: "no-store" }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
  const wantSample = new URLSearchParams(location.search).has("sample");
  const sample = () => get("sample.json").then((d) => { d.sample = true; render(d); $("to-live").hidden = !wantSample; });
  (wantSample ? sample() : get("oildesk.json").then((d) => {
    render(d);
    if (!d.vault) $("preview").hidden = false;
  }, sample)).catch((e) => { $("status").textContent = "Couldn't load data (" + e.message + ")"; });
})();
