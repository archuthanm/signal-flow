const statusEl = document.getElementById("status");
const articleListEl = document.getElementById("article-list");
const articleCountEl = document.getElementById("article-count");
const digestEl = document.getElementById("digest-content");
const windowTabsEl = document.getElementById("window-tabs");

let activeWindow = "24h";

const WINDOW_LABELS = {
  "24h": "Last 24 Hours",
  "3d": "Last 3 Days",
  "7d": "Last Week",
};

function setStatus(message) {
  statusEl.textContent = message;
}

function formatDate(value) {
  if (!value) return "Unknown time";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderArticles(articles) {
  articleCountEl.textContent = `${articles.length} records`;
  articleListEl.innerHTML = "";

  if (!articles.length) {
    articleListEl.innerHTML = `<div class="empty-state compact">No qualifying stories for ${WINDOW_LABELS[activeWindow].toLowerCase()}.</div>`;
    return;
  }

  for (const article of articles) {
    const el = document.createElement("article");
    el.className = "feed-card";
    const tags = article.tags ? article.tags.split(",").map((tag) => tag.trim()).filter(Boolean) : [];
    const preview = article.summary || article.description || article.title;
    const whyItMatters = article.why_it_matters || "Worth monitoring as broader market context.";

    el.innerHTML = `
      <h3><a href="${article.url}" target="_blank" rel="noreferrer">${article.title}</a></h3>
      <div class="feed-meta">
        <span style="color: var(--ink-main); font-weight: 600;">${article.source}</span>
        <span class="dot">•</span>
        <span>${formatDate(article.published_at)}</span>
        <span class="dot">•</span>
        <span style="color: var(--accent); font-weight: 600;">Score: ${article.relevance_score.toFixed(1)}</span>
        ${article.sector ? `<span class="dot">•</span><span>${article.sector}</span>` : ""}
      </div>
      <p>${preview}</p>
      <div class="feed-takeaway"><strong>System Takeaway:</strong> ${whyItMatters}</div>
      <div class="tags">
        ${tags.map((tag) => `<span class="tag-pill">${tag}</span>`).join("")}
      </div>
    `;
    articleListEl.appendChild(el);
  }
}

async function refreshArticles() {
  setStatus(`Querying ${WINDOW_LABELS[activeWindow].toLowerCase()}...`);
  const response = await fetch(`/api/articles?window=${activeWindow}`);
  const articles = await response.json();
  renderArticles(articles);
  setStatus(`${WINDOW_LABELS[activeWindow]} feed synced.`);
}

function renderDigestStory(article) {
  const tags = article.tags ? article.tags.split(",").map((tag) => tag.trim()).filter(Boolean) : [];
  const preview = article.summary || article.description || article.title;
  return `
    <article class="story-item">
      <h4><a href="${article.url}" target="_blank" rel="noreferrer">${article.title}</a></h4>
      <span class="story-meta">${article.source} <span class="dot">|</span> ${formatDate(article.published_at)} <span class="dot">|</span> <span style="color: var(--accent);">Score: ${article.relevance_score.toFixed(1)}</span></span>
      <p>${preview}</p>
      ${article.why_it_matters ? `<div class="feed-takeaway"><strong>Why it matters:</strong> ${article.why_it_matters}</div>` : ""}
      ${tags.length ? `<div class="tags">${tags.map((tag) => `<span class="tag-pill">${tag}</span>`).join("")}</div>` : ""}
    </article>
  `;
}

function renderDigest(digest) {
  if (!digest) {
    digestEl.innerHTML = `<div class="empty-state"><p>No digest generated yet for this window.</p></div>`;
    return;
  }

  const sectorCountPills = Object.entries(digest.sectors)
    .map(([key, sector]) => `<span class="tag-pill">${sector.label}: ${digest.sector_counts[key] || 0}</span>`)
    .join("");

  const sectorSections = Object.entries(digest.sectors)
    .map(([key, sector]) => `
      <div class="report-section">
        <div class="report-header">
          <h3>${sector.label}</h3>
          <span class="count">${digest.sector_counts[key] || 0}</span>
        </div>
        ${sector.articles.length ? sector.articles.map(renderDigestStory).join("") : "<div class='empty-state solid'>No qualifying stories.</div>"}
      </div>
    `)
    .join("");

  digestEl.innerHTML = `
    <div class="digest-grid">
      <div class="metric-card">
        <span>Report Window</span>
        <strong class="metric-label">${WINDOW_LABELS[digest.window] || digest.window}</strong>
      </div>
      <div class="metric-card">
        <span>Generation Time</span>
        <strong class="metric-date">${digest.date}</strong>
      </div>
      <div class="metric-card">
        <span>Key Stories</span>
        <strong>${digest.top_stories.length}</strong>
      </div>
    </div>

    <div class="report-section">
      <div class="report-header report-header-accent">
        <h3>Executive Summary: Top Stories</h3>
        <span class="count count-accent">${digest.top_stories.length}</span>
      </div>
      ${digest.top_stories.length ? digest.top_stories.map(renderDigestStory).join("") : "<div class='empty-state'>No high-relevance stories available.</div>"}
    </div>

    <div class="report-section">
      <div class="report-header">
        <h3>Sector Distribution</h3>
      </div>
      <div class="tags digest-sectors">${sectorCountPills}</div>
    </div>

    <div class="report-section">
      <div class="report-header">
        <h3>Identified Themes</h3>
      </div>
      ${digest.themes.length ? `<div class="tags digest-themes">${digest.themes.map((theme) => `<span class="tag-pill">${theme}</span>`).join("")}</div>` : "<div class='empty-state'>No recurring themes identified.</div>"}
    </div>

    ${sectorSections}
  `;
}

async function refreshDigest() {
  setStatus(`Loading ${WINDOW_LABELS[activeWindow].toLowerCase()} report...`);
  const response = await fetch(`/api/digest?window=${activeWindow}`);
  const payload = await response.json();
  renderDigest(payload.digest);
  setStatus(`${WINDOW_LABELS[activeWindow]} report ready.`);
}

async function runPipeline() {
  setStatus("Pipeline running...");
  const response = await fetch("/api/run", { method: "POST" });
  const payload = await response.json();
  setStatus(`Pipeline complete. Inserted ${payload.inserted}; retained ${payload.relevant}.`);
  await Promise.all([refreshArticles(), refreshDigest()]);
}

function setActiveWindow(windowKey) {
  activeWindow = windowKey;
  for (const button of windowTabsEl.querySelectorAll(".tab-button")) {
    button.classList.toggle("active", button.dataset.window === windowKey);
  }
  refreshArticles();
  refreshDigest();
}

document.getElementById("refresh-button").addEventListener("click", refreshArticles);
document.getElementById("digest-button").addEventListener("click", refreshDigest);
document.getElementById("run-button").addEventListener("click", runPipeline);
windowTabsEl.addEventListener("click", (event) => {
  const button = event.target.closest(".tab-button");
  if (!button) return;
  setActiveWindow(button.dataset.window);
});

refreshArticles();
refreshDigest();
