/* ═══════════════════════════════════════════════════════════════
   Market Insights — Frontend Application
   ───────────────────────────────────────────────────────────────
   Vanilla JS dashboard that calls the FastAPI backend, renders
   quotes / news / analysis / watchlist / recommendations, and
   manages loading states.  API calls are ONLY made when the
   user presses the Refresh button; initial load shows cached data.
   ═══════════════════════════════════════════════════════════════ */

"use strict";

// ── Auth helpers ──────────────────────────────────────────────

/** Return the Authorization header object if credentials are cached. */
function getAuthHeader() {
    const creds = sessionStorage.getItem("mi_auth");
    return creds ? { "Authorization": "Basic " + creds } : {};
}

/** Authenticated fetch wrapper — attaches Basic Auth header automatically. */
function apiFetch(url, options = {}) {
    const opts = { ...options };
    opts.headers = { ...(opts.headers || {}), ...getAuthHeader() };
    return fetch(url, opts);
}

/** Handle login form submission. */
async function submitLogin() {
    const user  = document.getElementById("login-user").value.trim();
    const pass  = document.getElementById("login-pass").value;
    const errEl = document.getElementById("login-error");
    const btn   = document.getElementById("login-btn");
    errEl.classList.add("hidden");

    if (!user || !pass) {
        errEl.textContent = "Please enter username and password.";
        errEl.classList.remove("hidden");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Signing in…";

    const encoded = btoa(unescape(encodeURIComponent(user + ":" + pass)));
    try {
        const resp = await fetch("/api/health", {
            headers: { "Authorization": "Basic " + encoded },
        });
        if (resp.status === 401) {
            errEl.textContent = "Invalid username or password.";
            errEl.classList.remove("hidden");
            return;
        }
        sessionStorage.setItem("mi_auth", encoded);
        document.getElementById("login-overlay").classList.add("hidden");
        loadCached();
        loadWatchlist();
    } catch (err) {
        errEl.textContent = "Connection error. Is the server running?";
        errEl.classList.remove("hidden");
    } finally {
        btn.disabled = false;
        btn.textContent = "Sign In";
    }
}

/** Sign out: clear credentials and show login overlay. */
function logout() {
    sessionStorage.removeItem("mi_auth");
    document.getElementById("login-overlay").classList.remove("hidden");
    document.getElementById("login-user").value = "";
    document.getElementById("login-pass").value = "";
}

// ── DOM references ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const loading      = $("#loading");
const errorBanner  = $("#error-banner");
const refreshBtn   = $("#refresh-btn");
const timestampEl  = $("#timestamp");

// ── Bootstrap: check auth then load cached data + watchlist ──────
document.addEventListener("DOMContentLoaded", () => {
    // Enter key on login fields
    ["login-user", "login-pass"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("keydown", e => { if (e.key === "Enter") submitLogin(); });
    });

    const creds = sessionStorage.getItem("mi_auth");
    if (creds) {
        document.getElementById("login-overlay").classList.add("hidden");
        loadCached();
        loadWatchlist();
    }
    // else: login overlay remains visible; data loads after successful sign-in
});


/* ────────────────────────────────────────────────────────────────
   Load cached data on page open (no live API calls)
   ──────────────────────────────────────────────────────────────── */
async function loadCached() {
    try {
        const resp = await apiFetch("/api/cached");
        const data = await resp.json();
        if (data.empty) {
            showError("No cached data yet — press Refresh to fetch live market data.");
            return;
        }
        renderAll(data);
    } catch (err) {
        showError("Could not load cached data.");
    }
}


/* ────────────────────────────────────────────────────────────────
   Core: Refresh — triggers live API calls via the LangGraph pipeline
   ──────────────────────────────────────────────────────────────── */
async function loadInsights() {
    showLoading();
    hideError();
    refreshBtn.disabled = true;

    try {
        const resp = await apiFetch("/api/insights");
        if (!resp.ok) throw new Error(`Server error ${resp.status}`);
        const data = await resp.json();
        renderAll(data);
    } catch (err) {
        showError(`Failed to load market data — ${err.message}`);
    } finally {
        hideLoading();
        refreshBtn.disabled = false;
    }
}


/* ────────────────────────────────────────────────────────────────
   Master renderer — dispatches to all section renderers
   ──────────────────────────────────────────────────────────────── */
function renderAll(data) {
    renderStocks(data.stocks);
    renderCommodities(data.commodities);
    renderETFs(data.etfs);
    renderAnalysis(data);
    renderNews(data.news);
    renderValidation(data.validation);
    renderWatchlistQuotes(data.watchlist);
    renderRecommendations(data.watchlist);
    updateTimestamp(data.timestamp || data._cached_at);
}


/* ────────────────────────────────────────────────────────────────
   Section Renderers
   ──────────────────────────────────────────────────────────────── */

/** Render major stock + index quote cards */
function renderStocks(stocks) {
    if (!stocks) return;
    renderQuoteGrid("#stocks-grid",  stocks.stock_quotes || []);
    renderQuoteGrid("#indexes-grid", stocks.index_quotes || []);
}

/** Render commodity quote cards */
function renderCommodities(commodities) {
    if (!commodities) return;
    renderQuoteGrid("#commodities-grid", commodities.quotes || []);
}

/** Render ETF quote cards */
function renderETFs(etfs) {
    if (!etfs) return;
    renderQuoteGrid("#etfs-grid", etfs.quotes || []);
}

/** Render combined AI analysis from all agents */
function renderAnalysis(data) {
    const parts = [];
    if (data.stocks?.analysis)      parts.push(`<strong>Stocks & Indexes</strong>\n${data.stocks.analysis}`);
    if (data.commodities?.analysis)  parts.push(`<strong>Commodities</strong>\n${data.commodities.analysis}`);
    if (data.etfs?.analysis)         parts.push(`<strong>ETFs</strong>\n${data.etfs.analysis}`);
    $("#analysis-content").innerHTML = parts.join("\n\n") || "No analysis available.";
}

/** Render news summary + article cards */
function renderNews(news) {
    if (!news) return;

    const summaryEl = $("#news-summary");
    summaryEl.innerHTML = news.summary
        ? `<strong>Research Summary</strong>\n${news.summary}`
        : "No news summary available.";

    const container = $("#news-articles");
    const articles = news.articles || [];
    if (!articles.length) { container.innerHTML = "<p>No articles found.</p>"; return; }

    container.innerHTML = articles
        .filter(a => a.title)
        .map(a => `
            <div class="article-card">
                <div class="article-title"><a href="${escHtml(a.url)}" target="_blank" rel="noopener">${escHtml(a.title)}</a></div>
                <div class="article-meta">${escHtml(a.source)}${a.published ? " · " + formatDate(a.published) : ""}</div>
                <div class="article-snippet">${escHtml(a.snippet)}</div>
            </div>`)
        .join("");
}

/** Render the validation report card */
function renderValidation(validation) {
    if (!validation) return;

    const card    = $("#section-validation");
    const badge   = $("#validation-badge");
    const content = $("#validation-content");

    const status = (validation.status || "PENDING").toUpperCase();
    badge.textContent = status;

    badge.className = "badge";
    card.className  = "card card-validation full-width";
    if (status === "HIGH")        { badge.classList.add("badge-green");  }
    else if (status === "MEDIUM") { badge.classList.add("badge-gold");   card.classList.add("status-medium"); }
    else if (status === "LOW")    { badge.classList.add("badge-red");    card.classList.add("status-low"); }
    else                          { badge.classList.add("badge-blue"); }

    content.innerHTML = `<strong>Validated at ${escHtml(validation.system_time || "")}</strong>\n\n${escHtml(validation.report || "")}`;
}

/** Render watchlist live quote cards */
function renderWatchlistQuotes(watchlist) {
    if (!watchlist || !watchlist.quotes || !watchlist.quotes.length) return;
    renderQuoteGrid("#watchlist-grid", watchlist.quotes);
}

/** Render buy/sell/hold recommendation cards with grounding links */
function renderRecommendations(watchlist) {
    const container = $("#recommendations-content");
    const recs = watchlist?.recommendations || [];

    if (!recs.length) {
        container.innerHTML = '<div class="empty-state">Add symbols to your watchlist and press Refresh to get AI-powered recommendations.</div>';
        return;
    }

    container.innerHTML = recs.map(r => {
        const signal   = (r.signal || "HOLD").toUpperCase();
        const sigClass = `signal-${signal.toLowerCase()}`;
        const sources  = r.sources || [];

        return `
            <div class="rec-card ${sigClass}">
                <div class="rec-header">
                    <span class="rec-symbol">${escHtml(r.symbol)}</span>
                    <span class="rec-signal ${sigClass}">${signal}</span>
                </div>
                <div class="rec-price">${formatPrice(r.price)}</div>
                <div class="rec-confidence">Confidence: <strong>${escHtml(r.confidence || "MEDIUM")}</strong></div>
                <div class="rec-reasoning">${escHtml(r.reasoning)}</div>
                <div class="rec-sources">
                    ${sources.map(s => `<a class="rec-source-link" href="${escHtml(s.url)}" target="_blank" rel="noopener">${escHtml(s.title)}</a>`).join("")}
                </div>
            </div>`;
    }).join("");
}


/* ────────────────────────────────────────────────────────────────
   Watchlist Management — CRUD operations
   ──────────────────────────────────────────────────────────────── */

/** Load the current watchlist from the backend and render symbol pills */
async function loadWatchlist() {
    try {
        const resp = await apiFetch("/api/watchlist");
        const data = await resp.json();
        renderWatchlistPills(data.watchlist || []);
    } catch (err) {
        console.error("Failed to load watchlist", err);
    }
}

/** Add a symbol to the watchlist */
async function addToWatchlist() {
    const input = $("#watchlist-input");
    const symbol = input.value.trim().toUpperCase();
    if (!symbol) return;

    try {
        await apiFetch("/api/watchlist", {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol }),
        });
        input.value = "";
        loadWatchlist();
    } catch (err) {
        showError("Failed to add symbol to watchlist.");
    }
}

/** Remove a symbol from the watchlist */
async function removeFromWatchlist(symbol) {
    try {
        await apiFetch("/api/watchlist", {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol }),
        });
        loadWatchlist();
    } catch (err) {
        showError("Failed to remove symbol from watchlist.");
    }
}

/** Render the editable watchlist symbol pills */
function renderWatchlistPills(items) {
    const container = $("#watchlist-symbols");
    if (!items.length) {
        container.innerHTML = '<span style="color:var(--text-muted);font-size:0.82rem">No symbols yet — add tickers above.</span>';
        return;
    }
    container.innerHTML = items.map(w => `
        <span class="wl-pill">
            ${escHtml(w.symbol)}
            <button class="wl-remove" onclick="removeFromWatchlist('${escHtml(w.symbol)}')" title="Remove">✕</button>
        </span>`).join("");
}

/** Allow Enter key to add symbol */
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("watchlist-input");
    if (input) input.addEventListener("keydown", e => { if (e.key === "Enter") addToWatchlist(); });
});


/* ────────────────────────────────────────────────────────────────
   Shared: build a grid of quote-cards
   ──────────────────────────────────────────────────────────────── */
function renderQuoteGrid(selector, quotes) {
    const container = document.querySelector(selector);
    if (!container) return;

    if (!quotes.length) { container.innerHTML = "<p style='color:var(--text-muted)'>Awaiting data…</p>"; return; }

    container.innerHTML = quotes.map(q => {
        const change    = parseFloat(q.change)         || 0;
        const changePct = parseFloat(q.change_percent)  || 0;
        const direction = change >= 0 ? "positive" : "negative";
        const arrow     = change >= 0 ? "▲" : "▼";
        const price     = formatPrice(q.price);

        return `
            <div class="quote-card">
                <div class="quote-symbol">${escHtml(q.symbol)}</div>
                <div class="quote-name">${escHtml(q.name || q.symbol)}</div>
                <div class="quote-price">${price}</div>
                <div class="quote-change ${direction}">
                    ${arrow} ${Math.abs(change).toFixed(2)} (${Math.abs(changePct).toFixed(2)}%)
                </div>
            </div>`;
    }).join("");
}


/* ────────────────────────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────────────────────────── */

/** Format number as currency string */
function formatPrice(val) {
    const n = parseFloat(val) || 0;
    return n >= 1000
        ? "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : "$" + n.toFixed(2);
}

/** Format ISO date string for display */
function formatDate(str) {
    if (!str) return "";
    try { return new Date(str).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }); }
    catch { return str; }
}

/** Basic HTML escaping */
function escHtml(text) {
    const d = document.createElement("div");
    d.textContent = text || "";
    return d.innerHTML;
}

/** Show the main timestamp */
function updateTimestamp(ts) {
    if (!timestampEl) return;
    timestampEl.textContent = ts ? new Date(ts).toLocaleString() : new Date().toLocaleString();
}


/* ────────────────────────────────────────────────────────────────
   Loading & error state management
   ──────────────────────────────────────────────────────────────── */

function showLoading() {
    loading.classList.remove("hidden");
    const pills = loading.querySelectorAll(".pill");
    pills.forEach((p, i) => setTimeout(() => p.classList.add("active"), i * 500));
}

function hideLoading() {
    loading.classList.add("hidden");
    loading.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
}

function showError(msg) {
    errorBanner.textContent = msg;
    errorBanner.classList.remove("hidden");
}

function hideError() {
    errorBanner.classList.add("hidden");
    errorBanner.textContent = "";
}


/* ────────────────────────────────────────────────────────────────
   Collapsible cards — tap header to expand/collapse on mobile
   ──────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-collapsible]").forEach(head => {
        head.addEventListener("click", () => {
            const card = head.closest(".card");
            card.classList.toggle("collapsed");
        });
    });
});

/* ────────────────────────────────────────────────────────────────
   Tab bar — smooth-scroll to section + highlight active tab
   ──────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    const tabBar = document.getElementById("tab-bar");
    if (!tabBar) return;

    tabBar.addEventListener("click", (e) => {
        const btn = e.target.closest(".tab");
        if (!btn) return;
        const targetId = btn.dataset.target;
        const section  = document.getElementById(targetId);
        if (!section) return;

        /* Ensure section is expanded before scrolling */
        if (section.classList.contains("collapsed")) {
            section.classList.remove("collapsed");
        }

        /* Scroll into view with offset for sticky header/tabs */
        section.scrollIntoView({ behavior: "smooth", block: "start" });

        /* Update active tab highlight */
        tabBar.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        btn.classList.add("active");
    });

    /* Auto-highlight tab on scroll using IntersectionObserver */
    const sections = tabBar.querySelectorAll(".tab");
    const observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.id;
                    sections.forEach(t => {
                        t.classList.toggle("active", t.dataset.target === id);
                    });
                }
            });
        },
        { rootMargin: "-30% 0px -60% 0px" }
    );

    document.querySelectorAll(".card[id]").forEach(s => observer.observe(s));
});
