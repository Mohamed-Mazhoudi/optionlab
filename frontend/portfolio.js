// OptionLab — onglet Portefeuille : comptes, ordres, positions, classement.
// Utilise les utilitaires de app.js : $, post, stat, pct, API.
(function () {
  const nf = (x, d = 2) => Number(x).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const money = (x) => nf(x, 2);
  const cls = (x) => (x > 0.005 ? "pos" : x < -0.005 ? "neg" : "");
  const signed = (x, d = 2) => (x > 0 ? "+" : "") + nf(x, d);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const KIND = { call: "Call", put: "Put" };
  const ACTION = { open: "Ouverture", close: "Clôture", expiry: "Échéance" };

  let me = null;          // utilisateur connecté
  let lastQuote = null;   // dernière cotation affichée (pour activer « Passer l'ordre »)

  async function get(path) {
    const res = await fetch(API + path, { credentials: "same-origin" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { const e = new Error(data.detail || "Erreur"); e.status = res.status; throw e; }
    return data;
  }

  // ---------- affichage connecté / non connecté ----------
  async function show() {
    try { me = (await get("/api/auth/me")).user; } catch { me = null; }
    $("pf-auth").classList.toggle("hidden", !!me);
    $("pf-app").classList.toggle("hidden", !me);
    if (me) {
      $("pf-user").textContent = me.username;
      if (!$("o-ticker").value && $("ticker").value) $("o-ticker").value = $("ticker").value.toUpperCase();
      await refresh();
    }
  }

  async function refresh() {
    await Promise.all([loadPortfolio(), loadHistory(), loadBoard()]);
  }

  // ---------- connexion / inscription ----------
  function bindForm(id, path) {
    const form = $(id);
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = form.querySelector(".form-msg");
      const btn = form.querySelector("button");
      msg.textContent = ""; btn.disabled = true;
      try {
        await post(path, Object.fromEntries(new FormData(form)));
        form.reset();
        await show();
      } catch (err) {
        msg.textContent = err.message;
      } finally { btn.disabled = false; }
    });
  }
  bindForm("login-form", "/api/auth/login");
  bindForm("register-form", "/api/auth/register");

  $("pf-logout").onclick = async () => { await post("/api/auth/logout", {}); me = null; show(); };
  $("pf-refresh").onclick = refresh;

  // ---------- portefeuille ----------
  async function loadPortfolio() {
    try {
      const p = await get("/api/portfolio");
      $("pf-stats").innerHTML =
        stat("Valeur totale", money(p.equity)) +
        stat("Performance", signed(p.return_pct, 2) + " %", cls(p.return_pct)) +
        stat("Trésorerie", money(p.cash)) +
        stat("P&L latent", signed(p.unrealized_pnl), cls(p.unrealized_pnl)) +
        stat("P&L réalisé", signed(p.realized_pnl), cls(p.realized_pnl)) +
        stat("Marge utilisée", money(p.margin_used)) +
        stat("Delta (en actions)", nf(p.greeks.delta, 1)) +
        stat("Theta (par jour)", signed(p.greeks.theta), cls(p.greeks.theta));
      const notes = [];
      if (p.settled_now) notes.push(`${p.settled_now} option(s) arrivée(s) à échéance viennent d'être réglée(s).`);
      if (p.stale_tickers.length) notes.push(`Cours indisponible pour ${p.stale_tickers.join(", ")} : dernier cours connu utilisé.`);
      $("pf-notice").textContent = notes.join(" ");
      renderPositions(p.positions);
    } catch (err) {
      if (err.status === 401) { me = null; return show(); }
      $("pf-stats").innerHTML = `<div class="stat error">${esc(err.message)}</div>`;
    }
  }

  function renderPositions(rows) {
    const head = `<tr><th>Titre</th><th>Option</th><th>Sens</th><th>Contrats</th><th>Prix d'entrée</th>
      <th>Prix actuel</th><th>Cours</th><th>Jours</th><th>P&amp;L latent</th><th>Delta</th><th></th></tr>`;
    if (!rows.length) {
      $("pf-positions").innerHTML = head + `<tr><td colspan="11" class="empty">Aucune position. Passe ton premier ordre ci-dessus.</td></tr>`;
      return;
    }
    $("pf-positions").innerHTML = head + rows.map((r) => `
      <tr>
        <td title="${esc(r.name)}"><b>${esc(r.ticker)}</b></td>
        <td>${KIND[r.kind]} ${nf(r.strike, r.strike % 1 ? 2 : 0)} · ${r.expiry}</td>
        <td>${r.side === "long" ? "Achat" : "Vente"}</td>
        <td>${r.quantity}</td>
        <td>${nf(r.entry_price)}</td>
        <td>${nf(r.mid)}</td>
        <td>${nf(r.spot)}</td>
        <td>${r.days_left}</td>
        <td class="${cls(r.unrealized_pnl)}">${signed(r.unrealized_pnl)}</td>
        <td>${nf(r.greeks.delta, 1)}</td>
        <td><button class="secondary small-btn" data-close="${r.id}">Clôturer</button></td>
      </tr>`).join("");
  }

  $("pf-positions").addEventListener("click", async (e) => {
    const id = e.target.dataset.close;
    if (!id) return;
    const row = e.target.closest("tr");
    if (!confirmInline(e.target, "Confirmer ?")) return;
    e.target.disabled = true;
    try {
      const r = await post(`/api/portfolio/positions/${id}/close`, {});
      await refresh();
      $("pf-notice").innerHTML = `Position clôturée au prix de ${nf(r.price)} : P&amp;L réalisé <span class="${cls(r.realized_pnl)}">${signed(r.realized_pnl)}</span>.`;
    } catch (err) {
      $("pf-notice").innerHTML = `<span class="error">${esc(err.message)}</span>`;
      if (row) e.target.disabled = false;
    }
  });

  // Double clic de confirmation sans boîte de dialogue : 1er clic arme le bouton, 2e clic exécute.
  function confirmInline(btn, label) {
    if (btn.dataset.armed) return true;
    const old = btn.textContent;
    btn.dataset.armed = "1"; btn.textContent = label;
    setTimeout(() => { delete btn.dataset.armed; btn.textContent = old; }, 3000);
    return false;
  }

  async function loadHistory() {
    try {
      const rows = await get("/api/portfolio/history");
      const head = `<tr><th>Date</th><th>Opération</th><th>Flux</th></tr>`;
      $("pf-history").innerHTML = head + (rows.length ? rows.slice(0, 30).map((h) => `
        <tr><td>${new Date(h.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</td>
          <td title="${esc(h.description)}">${ACTION[h.action] || h.action} · ${esc(h.description.replace(/^(Clôture|Échéance[^:]*) : /, ""))}</td>
          <td class="${cls(h.cash_flow)}">${signed(h.cash_flow)}</td></tr>`).join("")
        : `<tr><td colspan="3" class="empty">Aucune opération pour l'instant.</td></tr>`);
    } catch { /* déjà signalé par loadPortfolio */ }
  }

  async function loadBoard() {
    try {
      const rows = await get("/api/leaderboard");
      const head = `<tr><th>#</th><th>Joueur</th><th>Valeur</th><th>Perf.</th></tr>`;
      $("pf-board").innerHTML = head + rows.map((r) => `
        <tr class="${me && r.username === me.username ? "me" : ""}"><td>${r.rank}</td><td>${esc(r.username)}</td>
          <td>${money(r.equity)}</td><td class="${cls(r.return_pct)}">${signed(r.return_pct)} %</td></tr>`).join("");
    } catch (err) {
      $("pf-board").innerHTML = `<tr><td class="empty">${esc(err.message)}</td></tr>`;
    }
  }

  // ---------- ticket d'ordre ----------
  function order() {
    return {
      ticker: $("o-ticker").value.trim().toUpperCase(), kind: $("o-kind").value, side: $("o-side").value,
      strike: +$("o-strike").value, maturity: $("o-maturity").value, quantity: parseInt($("o-qty").value, 10),
    };
  }

  function invalidate() { lastQuote = null; $("o-send").disabled = true; }
  ["o-ticker", "o-kind", "o-side", "o-strike", "o-maturity", "o-qty"].forEach((id) => $(id).addEventListener("input", invalidate));
  $("o-ticker").addEventListener("change", () => { $("o-strike").value = ""; });

  $("o-quote").onclick = async () => {
    const box = $("o-result");
    const o = order();
    if (!o.ticker) { box.innerHTML = `<span class="error">Indique un titre (ex. AAPL).</span>`; return; }
    box.textContent = "Cotation…";
    try {
      if (!o.strike) {   // strike par défaut : le cours actuel, arrondi
        const m = await get("/api/market/" + encodeURIComponent(o.ticker));
        o.strike = m.price > 50 ? Math.round(m.price) : Math.round(m.price * 100) / 100;
        $("o-strike").value = o.strike;
      }
      const q = await post("/api/portfolio/quote", o);
      lastQuote = q;
      $("o-send").disabled = false;
      const verb = q.side === "long" ? "Tu paies" : "Tu encaisses";
      box.innerHTML =
        `<b>${esc(q.name)}</b> (${esc(q.ticker)}) · cours ${nf(q.spot)} · vol ${pct(q.vol)} · échéance ${q.expiry}<br>` +
        `${KIND[q.kind]} ${nf(q.strike)} : bid <b>${nf(q.bid)}</b> / ask <b>${nf(q.ask)}</b> (milieu ${nf(q.mid)})<br>` +
        `${verb} <b>${money(Math.abs(q.cash_flow))}</b> pour ${q.quantity} contrat(s) au prix de ${nf(q.price)}` +
        (q.margin ? ` · marge immobilisée <b>${money(q.margin)}</b>` : "") +
        ` · delta de la position ${nf(q.greeks.delta, 1)} actions`;
    } catch (err) {
      box.innerHTML = `<span class="error">${esc(err.message)}</span>`;
    }
  };

  $("o-send").onclick = async () => {
    if (!lastQuote) return;
    const box = $("o-result");
    $("o-send").disabled = true;
    try {
      const r = await post("/api/portfolio/orders", order());
      box.innerHTML = `<span class="pos">Ordre exécuté</span> : ${r.side === "long" ? "achat" : "vente"} de ${r.quantity} ` +
        `${KIND[r.kind].toLowerCase()}(s) ${esc(r.ticker)} ${nf(r.strike)} au prix de ${nf(r.price)}. ` +
        `Trésorerie : ${money(r.cash)}.`;
      lastQuote = null;
      await refresh();
    } catch (err) {
      box.innerHTML = `<span class="error">${esc(err.message)}</span>`;
      $("o-send").disabled = false;
    }
  };

  window.onPortfolioTab = show;
})();
