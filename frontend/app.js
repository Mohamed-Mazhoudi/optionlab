// OptionLab — frontend (JavaScript sans framework + Plotly)
const API = window.OPTIONLAB_API || "";   // même origine par défaut

const $ = (id) => document.getElementById(id);
const fmt = (x, d = 2) => (x === null || x === undefined) ? "Illimité" : Number(x).toFixed(d);
const pct = (x) => (x * 100).toFixed(2) + " %";
const signClass = (x) => (x === null ? "" : x >= 0 ? "pos" : "neg");

let presets = {};
let legs = [];
let activeTab = "strategy";

// ---------- appels API ----------
async function post(path, body) {
  const res = await fetch(API + path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}

function market() {
  return { S: +$("S").value, T: +$("T").value, r: +$("r").value, sigma: +$("sigma").value, q: +$("q").value };
}

function debounce(fn, ms = 120) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

// ---------- thème des graphiques ----------
const layoutBase = {
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: "#e6e9f0", size: 12 }, margin: { l: 55, r: 20, t: 40, b: 90 },
  xaxis: { gridcolor: "#263049", zerolinecolor: "#3a4766" },
  yaxis: { gridcolor: "#263049", zerolinecolor: "#8b95ab", zerolinewidth: 1 },
  legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.22 }, hovermode: "x unified",
};
const plotConfig = { responsive: true, displaylogo: false };

function stat(k, v, cls = "") {
  return `<div class="stat"><div class="k">${k}</div><div class="v ${cls}">${v}</div></div>`;
}

// ---------- panneau marché ----------
function updateOutputs() {
  $("o-S").textContent = (+$("S").value).toFixed(1);
  $("o-sigma").textContent = pct(+$("sigma").value);
  $("o-T").textContent = (+$("T").value).toFixed(2) + " an";
  $("o-r").textContent = pct(+$("r").value);
  $("o-q").textContent = pct(+$("q").value);
}

// ---------- stratégies ----------
function renderLegs() {
  $("legs").innerHTML = legs.map((l, i) => `
    <tr>
      <td><select data-i="${i}" data-f="side">
        <option value="long" ${l.side === "long" ? "selected" : ""}>Achat</option>
        <option value="short" ${l.side === "short" ? "selected" : ""}>Vente</option></select></td>
      <td><select data-i="${i}" data-f="kind">
        <option value="call" ${l.kind === "call" ? "selected" : ""}>Call</option>
        <option value="put" ${l.kind === "put" ? "selected" : ""}>Put</option>
        <option value="stock" ${l.kind === "stock" ? "selected" : ""}>Action</option></select></td>
      <td><input type="number" step="0.5" min="0.01" data-i="${i}" data-f="strike"
           value="${l.strike ?? ""}" ${l.kind === "stock" ? "disabled" : ""}></td>
      <td><input type="number" step="1" min="1" data-i="${i}" data-f="quantity" value="${l.quantity}"></td>
      <td class="premium" id="prem-${i}">–</td>
      <td><button class="icon" data-del="${i}" title="Supprimer">✕</button></td>
    </tr>`).join("");
}

$("legs").addEventListener("change", (e) => {
  const { i, f } = e.target.dataset;
  if (i === undefined) return;
  const leg = legs[+i];
  if (f === "strike" || f === "quantity") leg[f] = +e.target.value;
  else leg[f] = e.target.value;
  if (leg.kind === "stock") leg.strike = null;
  else if (!leg.strike) leg.strike = Math.round(market().S);
  renderLegs(); refreshStrategy();
});
$("legs").addEventListener("click", (e) => {
  if (e.target.dataset.del === undefined) return;
  legs.splice(+e.target.dataset.del, 1);
  renderLegs(); refreshStrategy();
});
$("add-leg").onclick = () => {
  if (legs.length >= 8) return;
  legs.push({ kind: "call", side: "long", strike: Math.round(market().S), quantity: 1 });
  renderLegs(); refreshStrategy();
};

async function loadPreset() {
  const key = $("preset").value;
  const p = presets[key];
  $("preset-desc").innerHTML = `<b>${p.view}</b> — ${p.description}`;
  const st = await post(`/api/presets/${key}`, market());
  legs = st.legs.map(({ premium, ...l }) => l);
  renderLegs(); refreshStrategy();
}

let strategySeq = 0;
async function refreshStrategy() {
  const seq = ++strategySeq;
  if (!legs.length) {
    $("strategy-stats").innerHTML = stat("Position", "Aucune jambe");
    Plotly.purge("chart-strategy"); return;
  }
  try {
    const d = await post("/api/strategy", { market: market(), legs, name: $("preset").selectedOptions[0]?.text });
    if (seq !== strategySeq) return;  // une requête plus récente est partie entre-temps
    d.premiums.forEach((p, i) => { const c = $("prem-" + i); if (c) c.textContent = p.toFixed(2); });

    const cost = d.net_cost;
    $("strategy-stats").innerHTML =
      stat(cost >= 0 ? "Coût net (débit)" : "Crédit net encaissé", fmt(Math.abs(cost)), cost >= 0 ? "neg" : "pos") +
      stat("Gain max", fmt(d.max_profit), "pos") +
      stat("Perte max", fmt(d.max_loss), "neg") +
      stat("Points morts", d.breakevens.length ? d.breakevens.map((b) => b.toFixed(2)).join(" / ") : "Aucun") +
      stat("Delta", fmt(d.greeks.delta, 3)) + stat("Gamma", fmt(d.greeks.gamma, 4)) +
      stat("Vega (1 %)", fmt(d.greeks.vega, 3)) + stat("Theta (jour)", fmt(d.greeks.theta, 3));

    const S = market().S;
    const traces = [
      { x: d.spots, y: d.pnl_expiry, name: "À l'échéance", line: { color: "#4f8cff", width: 3 } },
      { x: d.spots, y: d.pnl_half, name: "À mi-parcours", line: { color: "#f2b84b", dash: "dot" } },
      { x: d.spots, y: d.pnl_today, name: "Aujourd'hui", line: { color: "#2fbf71", dash: "dash" } },
    ];
    const shapes = [{ type: "line", x0: S, x1: S, yref: "paper", y0: 0, y1: 1, line: { color: "#8b95ab", dash: "dot" } }];
    d.breakevens.forEach((b) => shapes.push({ type: "line", x0: b, x1: b, yref: "paper", y0: 0, y1: 1,
      line: { color: "#ef5b5b", width: 1, dash: "dash" } }));
    Plotly.react("chart-strategy", traces, {
      ...layoutBase, shapes, title: { text: "Profit / perte selon le cours du sous-jacent", font: { size: 14 } },
      xaxis: { ...layoutBase.xaxis, title: "Cours du sous-jacent" },
      yaxis: { ...layoutBase.yaxis, title: "P&L" },
    }, plotConfig);
  } catch (err) {
    $("strategy-stats").innerHTML = `<div class="stat error">${err.message}</div>`;
  }
}

// ---------- pricer ----------
let pricerSeq = 0;
async function refreshPricer() {
  const seq = ++pricerSeq;
  const body = { ...market(), K: +$("K").value, option: $("option").value };
  try {
    const [p, c] = await Promise.all([post("/api/price", body), post("/api/greeks-curve", body)]);
    if (seq !== pricerSeq) return;
    const g = p.greeks;
    $("pricer-stats").innerHTML =
      stat("Black-Scholes", fmt(p.black_scholes, 4)) +
      (p.binomial !== undefined ? stat("Arbre binomial (300 pas)", fmt(p.binomial, 4)) +
        stat("Américaine (binomial)", fmt(p.binomial_american, 4)) +
        stat("Monte-Carlo", `${fmt(p.monte_carlo.price, 3)} <span class="muted small">± ${fmt(1.96 * p.monte_carlo.std_error, 3)}</span>`) : "") +
      stat("Delta", fmt(g.delta, 4)) + stat("Gamma", fmt(g.gamma, 4)) +
      stat("Vega (1 %)", fmt(g.vega, 4)) + stat("Theta (jour)", fmt(g.theta, 4)) + stat("Rho (1 %)", fmt(g.rho, 4));

    const key = $("curve").value;
    const label = $("curve").selectedOptions[0].text;
    const S = market().S;
    Plotly.react("chart-pricer", [{ x: c.spots, y: c[key], name: label, line: { color: "#4f8cff", width: 3 } }], {
      ...layoutBase, showlegend: false,
      title: { text: `${label} du ${body.option} selon le spot (K = ${body.K})`, font: { size: 14 } },
      shapes: [{ type: "line", x0: S, x1: S, yref: "paper", y0: 0, y1: 1, line: { color: "#8b95ab", dash: "dot" } }],
      xaxis: { ...layoutBase.xaxis, title: "Spot" }, yaxis: { ...layoutBase.yaxis, title: label },
    }, plotConfig);
  } catch (err) {
    $("pricer-stats").innerHTML = `<div class="stat error">${err.message}</div>`;
  }
}

// ---------- vol implicite ----------
async function runIV() {
  const body = { ...market(), K: +$("iv-K").value, option: $("iv-option").value, price: +$("iv-price").value };
  try {
    const { implied_vol } = await post("/api/implied-vol", body);
    $("iv-stats").innerHTML = stat("Volatilité implicite", pct(implied_vol), "pos") +
      stat("Vol du panneau Marché", pct(body.sigma)) +
      stat("Écart", ((implied_vol - body.sigma) * 100).toFixed(2) + " pts");
  } catch (err) {
    $("iv-stats").innerHTML = `<div class="stat error">${err.message}</div>`;
  }
}

// ---------- données réelles ----------
async function loadTicker() {
  const t = $("ticker").value.trim();
  if (!t) return;
  $("ticker-info").innerHTML = "Chargement…";
  $("load-ticker").disabled = true;
  try {
    const res = await fetch(API + "/api/market/" + encodeURIComponent(t));
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || "Erreur");
    const S = $("S");
    S.min = Math.max(0.01, +(d.price * 0.3).toFixed(2));
    S.max = +(d.price * 2).toFixed(2);
    S.step = 0.01;
    S.value = d.price;
    $("sigma").value = Math.min(1.2, Math.max(0.01, d.vol_1y)).toFixed(4);
    $("q").value = Math.min(0.08, d.dividend_yield).toFixed(4);
    // strikes des autres onglets alignés sur le cours
    const k = d.price > 50 ? Math.round(d.price) : +d.price.toFixed(2);
    ["K", "iv-K", "h-K"].forEach((id) => { $(id).value = k; });
    $("ticker-info").innerHTML =
      `<b>${d.name}</b> (${d.ticker})<br>Cours : <b>${d.price.toFixed(2)} ${d.currency}</b> au ${d.date}<br>` +
      `Vol. historique 1 an : <b>${pct(d.vol_1y)}</b> · 3 mois : ${pct(d.vol_3m)}<br>` +
      `Dividende : ${pct(d.dividend_yield)}`;
    $("ticker-chart").classList.remove("hidden");
    Plotly.react("ticker-chart", [{ x: d.history.dates, y: d.history.close, line: { color: "#4f8cff", width: 1.5 } }], {
      ...layoutBase, showlegend: false, margin: { l: 35, r: 5, t: 5, b: 25 },
      xaxis: { ...layoutBase.xaxis, showgrid: false, tickformat: "%b %y", nticks: 4, tickangle: 0 },
      yaxis: { ...layoutBase.yaxis, nticks: 4 },
    }, { ...plotConfig, displayModeBar: false });
    updateOutputs();
    if (activeTab === "strategy") await loadPreset(); else refreshActive();
  } catch (err) {
    $("ticker-info").innerHTML = `<span class="error">${err.message}</span>`;
  } finally {
    $("load-ticker").disabled = false;
  }
}
$("load-ticker").onclick = loadTicker;
$("ticker").addEventListener("keydown", (e) => { if (e.key === "Enter") loadTicker(); });

// ---------- couverture (delta hedging) ----------
let hedgeSeed = 7;
function updateHedgeOutputs() {
  $("o-hvol").textContent = pct(+$("h-vol").value);
  $("o-hmu").textContent = pct(+$("h-mu").value);
  $("o-hcost").textContent = (+$("h-cost").value * 100).toFixed(2) + " %";
}

async function runHedge() {
  const m = market();
  const body = {
    S0: m.S, K: +$("h-K").value, T: Math.min(m.T, 3), r: m.r, q: m.q,
    implied_vol: m.sigma, realized_vol: +$("h-vol").value, mu: +$("h-mu").value,
    option: $("h-option").value, side: $("h-side").value, rebalance: +$("h-freq").value,
    n_paths: +$("h-paths").value, cost_rate: +$("h-cost").value, seed: hedgeSeed,
  };
  $("h-run").disabled = true;
  $("hedge-stats").innerHTML = stat("Simulation", "En cours…");
  try {
    const d = await post("/api/hedging", body);
    const s = d.stats;
    const who = body.side === "short" ? "Le vendeur" : "L'acheteur";
    $("hedge-stats").innerHTML =
      stat("Prime de l'option", fmt(d.premium, 3)) +
      stat("P&L moyen", fmt(s.mean, 3), signClass(s.mean)) +
      stat("Écart-type du P&L", fmt(s.std, 3)) +
      stat("Proba. de perte", (s.prob_loss * 100).toFixed(1) + " %") +
      stat("Pire 5 %", fmt(s.p5, 3), signClass(s.p5)) +
      stat("Meilleur 5 %", fmt(s.p95, 3), signClass(s.p95)) +
      stat("Rebalancements", d.n_steps) +
      (body.cost_rate > 0 ? stat("Frais moyens", fmt(s.avg_costs, 3), "neg") : "");

    const p = d.path;
    Plotly.react("chart-hedge-path", [
      { x: p.t, y: p.S, name: "Cours du sous-jacent", line: { color: "#4f8cff", width: 2 } },
      { x: p.t, y: p.delta, name: "Delta détenu", yaxis: "y2", line: { color: "#f2b84b", shape: "hv" } },
      { x: p.t, y: p.pnl, name: "P&L couvert cumulé", yaxis: "y3", line: { color: "#2fbf71", width: 2 } },
    ], {
      ...layoutBase,
      title: { text: "Une trajectoire : le cours bouge, la banque ajuste son delta", font: { size: 14 } },
      xaxis: { ...layoutBase.xaxis, title: "Temps (années)", domain: [0, 1] },
      yaxis: { ...layoutBase.yaxis, title: "Cours", domain: [0.42, 1] },
      yaxis2: { overlaying: "y", side: "right", title: "Delta", showgrid: false, range: [-1.05, 1.05] },
      yaxis3: { ...layoutBase.yaxis, title: "P&L", domain: [0, 0.32] },
      margin: { l: 55, r: 55, t: 40, b: 90 },
    }, plotConfig);

    const e = d.histogram.edges;
    const centers = d.histogram.counts.map((_, i) => (e[i] + e[i + 1]) / 2);
    Plotly.react("chart-hedge-hist", [{
      type: "bar", x: centers, y: d.histogram.counts,
      marker: { color: centers.map((c) => (c >= 0 ? "#2fbf71" : "#ef5b5b")) }, name: "Trajectoires",
    }], {
      ...layoutBase, showlegend: false, bargap: 0.05,
      title: { text: `Distribution du P&L final (${body.n_paths} trajectoires)`, font: { size: 14 } },
      xaxis: { ...layoutBase.xaxis, title: "P&L actualisé" }, yaxis: { ...layoutBase.yaxis, title: "Nombre" },
      margin: { l: 55, r: 20, t: 40, b: 50 },
    }, plotConfig);

    Plotly.react("chart-hedge-conv", [{
      type: "bar", x: d.convergence.map((c) => c.label), y: d.convergence.map((c) => c.std),
      marker: { color: "#4f8cff" }, text: d.convergence.map((c) => c.std.toFixed(3)), textposition: "outside",
    }], {
      ...layoutBase, showlegend: false,
      title: { text: "Risque résiduel selon la fréquence", font: { size: 14 } },
      yaxis: { ...layoutBase.yaxis, title: "Écart-type du P&L" }, margin: { l: 55, r: 20, t: 40, b: 50 },
    }, plotConfig);

    const gap = body.realized_vol - body.implied_vol;
    let msg;
    if (Math.abs(gap) < 0.005) {
      msg = `Vol réalisée = vol implicite : la couverture « fonctionne », le P&L moyen est proche de 0 et il ne reste qu'un bruit dû au rebalancement discret. Passe en rebalancement quotidien pour le voir diminuer (environ en 1/√N).`;
    } else {
      const winner = (gap > 0) === (body.side === "long");
      msg = `La vol réalisée (${pct(body.realized_vol)}) est ${gap > 0 ? "supérieure" : "inférieure"} à la vol implicite (${pct(body.implied_vol)}). ` +
        `${who} couvert est ${body.side === "short" ? "short" : "long"} gamma : il ${winner ? "gagne" : "perd"} en moyenne. ` +
        `Approximation vega × écart de vol : ${fmt(s.expected_vol_pnl, 3)} (simulation : ${fmt(s.mean, 3)}). ` +
        `C'est pour ça qu'un trader d'options parie en réalité sur la volatilité, pas sur la direction.`;
    }
    $("hedge-explain").innerHTML = msg + (body.cost_rate > 0 ? ` Les frais de transaction coûtent ici ${fmt(s.avg_costs, 3)} en moyenne : plus on rebalance, plus ça coûte.` : "");
  } catch (err) {
    $("hedge-stats").innerHTML = `<div class="stat error">${err.message}</div>`;
  } finally {
    $("h-run").disabled = false;
  }
}
["h-vol", "h-mu", "h-cost"].forEach((id) => $(id).addEventListener("input", updateHedgeOutputs));
$("h-run").onclick = runHedge;
$("h-reseed").onclick = () => { hedgeSeed = Math.floor(Math.random() * 1e6); runHedge(); };

// ---------- apprendre (cours + quiz) ----------
let currentLesson = 0;
const store = {
  get() { try { return JSON.parse(localStorage.getItem("optionlab-progress") || "{}"); } catch { return {}; } },
  set(v) { try { localStorage.setItem("optionlab-progress", JSON.stringify(v)); } catch { /* stockage indisponible */ } },
};
let progress = store.get();

function renderLessonList() {
  const total = LESSONS.length;
  const done = LESSONS.filter((l) => progress[l.id]).length;
  $("progress").textContent = `${done} leçon${done > 1 ? "s" : ""} réussie${done > 1 ? "s" : ""} sur ${total}`;
  $("progress-fill").style.width = (100 * done / total) + "%";
  let html = "", lastModule = "";
  LESSONS.forEach((l, i) => {
    if (l.module !== lastModule) { html += `<li class="module">${l.module}</li>`; lastModule = l.module; }
    html += `<li class="${progress[l.id] ? "done" : ""}"><button data-lesson="${i}" class="${i === currentLesson ? "current" : ""}">
      <span class="check">${progress[l.id] ? "✓" : ""}</span>${l.title}</button></li>`;
  });
  $("lessons").innerHTML = html;
}

function renderLesson(i) {
  currentLesson = i;
  const l = LESSONS[i];
  const quiz = l.quiz.map((q, qi) => `
    <div class="question" data-q="${qi}">
      <p>${qi + 1}. ${q.q}</p>
      <div class="choices">${q.choices.map((c, ci) => `<button data-q="${qi}" data-c="${ci}">${c}</button>`).join("")}</div>
      <div class="explain hidden"></div>
    </div>`).join("");
  $("lesson").innerHTML = `
    <div class="meta">${l.module} · ${l.level} · ${l.minutes} min</div>
    <h1>${l.title}</h1>
    ${l.body}
    ${l.try ? `<div class="try"><button data-try="1">${l.try.label}</button></div>` : ""}
    <div class="quiz"><h3>Quiz</h3>${quiz}<div class="score" id="score"></div></div>
    <div class="lesson-nav">
      <button class="secondary" data-nav="-1" ${i === 0 ? "disabled" : ""}>← Précédente</button>
      <button class="secondary" data-nav="1" ${i === LESSONS.length - 1 ? "disabled" : ""}>Suivante →</button>
    </div>`;
  renderLessonList();
  $("lesson").scrollIntoView({ block: "start", behavior: "smooth" });
}

$("lessons").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-lesson]");
  if (b) renderLesson(+b.dataset.lesson);
});

$("lesson").addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.nav) return renderLesson(currentLesson + +b.dataset.nav);
  if (b.dataset.try) return tryInLab(LESSONS[currentLesson].try);
  if (b.dataset.c === undefined) return;
  const l = LESSONS[currentLesson];
  const qi = +b.dataset.q, ci = +b.dataset.c, q = l.quiz[qi];
  const box = b.closest(".question");
  box.querySelectorAll("button").forEach((btn, k) => {
    btn.disabled = true;
    if (k === q.answer) btn.classList.add("right");
    else if (k === ci) btn.classList.add("wrong");
  });
  box.dataset.ok = ci === q.answer ? "1" : "0";
  const ex = box.querySelector(".explain");
  ex.innerHTML = (ci === q.answer ? "✓ Bonne réponse. " : "✗ Raté. ") + q.explain;
  ex.classList.remove("hidden");

  const answered = $("lesson").querySelectorAll(".question[data-ok]");
  if (answered.length === l.quiz.length) {
    const good = [...answered].filter((x) => x.dataset.ok === "1").length;
    const passed = good >= Math.ceil(l.quiz.length * 2 / 3);
    $("score").innerHTML = `Score : ${good}/${l.quiz.length} — ` +
      (passed ? `<span class="pos">leçon validée !</span>` : `<span class="neg">relis la leçon et réessaie (2/3 requis).</span> <button class="secondary" data-retry="1">Recommencer le quiz</button>`);
    if (passed) { progress[l.id] = true; store.set(progress); renderLessonList(); }
  }
});
$("lesson").addEventListener("click", (e) => { if (e.target.dataset.retry) renderLesson(currentLesson); });

function setSlider(id, v) { if (v !== undefined) { $(id).value = v; } }
async function tryInLab(t) {
  if (t.S !== undefined && (t.S < +$("S").min || t.S > +$("S").max)) {
    Object.assign($("S"), { min: 20, max: 300, step: 0.5 });
    $("ticker-info").innerHTML = ""; $("ticker-chart").classList.add("hidden");
  }
  setSlider("S", t.S); setSlider("sigma", t.sigma); setSlider("T", t.T);
  if (t.S !== undefined) { setSlider("r", t.r ?? 0.03); setSlider("q", t.q ?? 0); }
  updateOutputs();
  if (t.preset) { $("preset").value = t.preset; await loadPreset(); }
  if (t.realized !== undefined) { $("h-vol").value = t.realized; updateHedgeOutputs(); }
  if (t.freq) $("h-freq").value = t.freq;
  if (t.curve) $("curve").value = t.curve;
  if (t.option) { $("option").value = t.option; $("h-option").value = t.option; }
  if (t.K) { $("K").value = t.K; $("h-K").value = t.K; }
  switchTab(t.tab);
  if (t.tab === "hedge") runHedge();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ---------- navigation et initialisation ----------
function refreshActive() {
  if (activeTab === "strategy") refreshStrategy();
  else if (activeTab === "pricer") refreshPricer();
}
const refreshDebounced = debounce(refreshActive);

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("hidden", p.id !== "tab-" + tab));
  $("main").classList.toggle("learn-mode", tab === "learn" || tab === "portfolio");
  if (tab === "portfolio" && window.onPortfolioTab) window.onPortfolioTab();
  if (tab === "learn" && !$("lesson").innerHTML) renderLesson(0);
  if (tab === "hedge" && !$("hedge-stats").innerHTML) {
    $("h-vol").value = $("sigma").value; updateHedgeOutputs(); runHedge();
  }
  refreshActive();
  window.dispatchEvent(new Event("resize"));
}
document.querySelectorAll(".tab").forEach((btn) => btn.onclick = () => switchTab(btn.dataset.tab));

["S", "sigma", "T", "r", "q"].forEach((id) => $(id).addEventListener("input", () => { updateOutputs(); refreshDebounced(); }));
["K", "option", "curve"].forEach((id) => $(id).addEventListener("change", refreshPricer));
$("preset").onchange = loadPreset;
$("rebuild").onclick = loadPreset;
$("iv-run").onclick = runIV;

(async function init() {
  updateOutputs();
  updateHedgeOutputs();
  try {
    presets = await (await fetch(API + "/api/presets")).json();
    $("preset").innerHTML = Object.entries(presets)
      .map(([k, p]) => `<option value="${k}">${p.label}</option>`).join("");
    $("preset").value = "long_straddle";
    await loadPreset();
  } catch (err) {
    $("strategy-stats").innerHTML = `<div class="stat error">API injoignable : lance le backend (voir README).</div>`;
  }
})();
