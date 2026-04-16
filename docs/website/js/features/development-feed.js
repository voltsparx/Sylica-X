async function initDevelopmentFeed() {
  const repoHealth = document.getElementById("repo-health");
  const commitFeed = document.getElementById("commit-feed");
  const releaseFeed = document.getElementById("release-feed");
  const tagFeed = document.getElementById("tag-feed");
  const chartNode = document.getElementById("dev-commit-chart");
  const rawViewerGrid = document.getElementById("raw-viewer-grid");

  if (!repoHealth && !commitFeed && !releaseFeed && !tagFeed && !chartNode && !rawViewerGrid) {
    return;
  }

  RawPopup?.bind?.();

  const base = githubApi("");

  try {
    const [repoResponse, commitsResponse, releasesResponse, tagsResponse] = await Promise.all([
      fetch(base),
      fetch(`${base}/commits?per_page=12`),
      fetch(`${base}/releases?per_page=3`),
      fetch(`${base}/tags?per_page=5`)
    ]);

    if (!repoResponse.ok || !commitsResponse.ok || !releasesResponse.ok || !tagsResponse.ok) {
      throw new Error("GitHub API request failed");
    }

    const repo = await repoResponse.json();
    const commits = await commitsResponse.json();
    const releases = await releasesResponse.json();
    const tags = await tagsResponse.json();

    if (repoHealth) {
      repoHealth.innerHTML = `
        <div class="dev-status-grid">
          <div class="dev-status-item"><span class="dev-status-label">Default Branch</span><span class="dev-status-value">${escapeHtml(repo.default_branch || "main")}</span></div>
          <div class="dev-status-item"><span class="dev-status-label">Open Issues</span><span class="dev-status-value">${escapeHtml(String(repo.open_issues_count ?? "n/a"))}</span></div>
          <div class="dev-status-item"><span class="dev-status-label">Stars</span><span class="dev-status-value">${escapeHtml(String(repo.stargazers_count ?? "n/a"))}</span></div>
          <div class="dev-status-item"><span class="dev-status-label">Watchers</span><span class="dev-status-value">${escapeHtml(String(repo.subscribers_count ?? "n/a"))}</span></div>
        </div>
      `;
    }

    if (commitFeed) {
      commitFeed.innerHTML = `
        <div class="feed-list">
          ${commits.map((commit) => {
            const message = (commit.commit?.message || "Commit").split("\n")[0];
            const author = commit.commit?.author?.name || "unknown";
            const date = commit.commit?.author?.date;
            return `
              <article class="feed-item">
                <a href="${escapeHtml(commit.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(message)}</a>
                <div class="feed-meta">${escapeHtml(author)} · ${escapeHtml(formatDate(date))} · ${escapeHtml(formatRelativeTime(date))}</div>
              </article>
            `;
          }).join("")}
        </div>
      `;
    }

    if (chartNode) {
      const chartSeries = buildCommitSeries(commits, 7);
      chartNode.innerHTML = renderCommitChart(chartSeries, commits);
    }

    if (releaseFeed) {
      releaseFeed.innerHTML = releases.length
        ? `<div class="feed-list">${releases.map((release) => `
            <article class="feed-item">
              <a href="${escapeHtml(release.html_url)}" target="_blank" rel="noreferrer">${escapeHtml(release.name || release.tag_name || "Release")}</a>
              <div class="feed-meta">${escapeHtml(release.tag_name || "untagged")} · ${escapeHtml(release.published_at ? formatDate(release.published_at) : "draft")}</div>
            </article>
          `).join("")}</div>`
        : '<div class="empty-state">No published GitHub releases yet. The project currently signals release state through repository docs and tags.</div>';
    }

    if (tagFeed) {
      tagFeed.innerHTML = Array.isArray(tags) && tags.length
        ? `<div class="feed-list">${tags.map((tag) => `
            <article class="feed-item">
              <a href="${escapeHtml(`${DocsData.github.repoUrl}/tree/${tag.name}`)}" target="_blank" rel="noreferrer">${escapeHtml(tag.name)}</a>
              <div class="feed-meta">Repository tag signal</div>
            </article>
          `).join("")}</div>`
        : '<div class="empty-state">No tag data available right now.</div>';
    }

    if (rawViewerGrid) {
      const files = [
        { title: "README", path: "README.md", copy: "Current release statement, command tables, and audit snapshot." },
        { title: "Security Policy", path: "SECURITY.md", copy: "Repository security and responsible handling guidance." },
        { title: "Release Notes", path: "docs/release-notes-v9.3.0-lattice.md", copy: "Detailed v9.3.0 changes and release framing." },
        { title: "Capability Scan", path: "docs/silica-capability-scan.md", copy: "Project self-assessment and capability reporting signal." },
        { title: "Runtime Inventory", path: "intel/runtime-inventory.json", copy: "Machine-readable plugin, filter, platform, and module snapshot." },
        { title: "Package Metadata", path: "pyproject.toml", copy: "Project metadata, dependencies, and packaging entrypoints." }
      ];

      rawViewerGrid.innerHTML = `
        <div class="raw-link-grid">
          ${files.map((file) => `
            <a
              class="raw-link-card"
              data-raw-viewer
              data-raw-title="${escapeHtml(file.title)}"
              data-raw-path="${escapeHtml(file.path)}"
              data-repo-href="${escapeHtml(githubBlob(file.path))}"
              href="${escapeHtml(githubRaw(file.path))}"
              target="_blank"
              rel="noreferrer"
            >
              <span class="raw-link-title">${escapeHtml(file.title)}</span>
              <span class="raw-link-path">${escapeHtml(file.path)}</span>
              <span class="raw-link-copy">${escapeHtml(file.copy)}</span>
            </a>
          `).join("")}
        </div>
      `;
    }
  } catch (error) {
    const fallback = '<div class="empty-state">Live GitHub data could not be loaded right now. Use the repository links on this page for raw signals.</div>';
    repoHealth && (repoHealth.innerHTML = fallback);
    commitFeed && (commitFeed.innerHTML = fallback);
    releaseFeed && (releaseFeed.innerHTML = fallback);
    tagFeed && (tagFeed.innerHTML = fallback);
    chartNode && (chartNode.innerHTML = fallback);
    rawViewerGrid && (rawViewerGrid.innerHTML = fallback);
  }
}

function buildCommitSeries(commits, days) {
  const byDay = new Map();
  const orderedDays = [];

  for (let index = days - 1; index >= 0; index -= 1) {
    const date = new Date();
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - index);
    const key = date.toISOString().slice(0, 10);
    orderedDays.push(key);
    byDay.set(key, 0);
  }

  for (const commit of commits) {
    const date = commit.commit?.author?.date;
    if (!date) {
      continue;
    }
    const key = new Date(date).toISOString().slice(0, 10);
    if (byDay.has(key)) {
      byDay.set(key, byDay.get(key) + 1);
    }
  }

  return orderedDays.map((key) => {
    const date = new Date(key);
    return {
      key,
      count: byDay.get(key) || 0,
      short: date.toLocaleDateString(undefined, { weekday: "short" }),
      full: date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
    };
  });
}

function renderCommitChart(series, commits) {
  const width = 720;
  const height = 260;
  const padding = { top: 24, right: 20, bottom: 40, left: 34 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxCount = Math.max(...series.map((item) => item.count), 1);
  const stepX = series.length > 1 ? plotWidth / (series.length - 1) : plotWidth;

  const points = series.map((item, index) => ({
    ...item,
    x: Number((padding.left + stepX * index).toFixed(2)),
    y: Number((padding.top + plotHeight - ((item.count / maxCount) * plotHeight)).toFixed(2))
  }));

  const line = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const area = `${line} L ${points[points.length - 1].x} ${padding.top + plotHeight} L ${points[0].x} ${padding.top + plotHeight} Z`;
  const latestCommit = commits[0]?.commit?.author?.date;
  const total = series.reduce((sum, item) => sum + item.count, 0);

  return `
    <div class="dev-chart-shell">
      <div class="dev-chart-summary">
        <div>
          <strong>${compactNumber(total)} commits in the last ${series.length} days</strong>
          <div class="muted">Latest visible commit: ${escapeHtml(latestCommit ? `${formatDate(latestCommit)} (${formatRelativeTime(latestCommit)})` : "n/a")}</div>
        </div>
        <div class="muted">Peak day: ${escapeHtml(series.reduce((best, item) => item.count > best.count ? item : best, series[0]).full)}</div>
      </div>
      <div class="dev-chart">
        <svg class="dev-chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Recent commit trend">
          ${Array.from({ length: Math.min(maxCount, 4) + 1 }, (_, index) => {
            const value = Math.round((maxCount / Math.max(Math.min(maxCount, 4), 1)) * index);
            const y = Number((padding.top + plotHeight - ((value / maxCount) * plotHeight)).toFixed(2));
            return `
              <line class="dev-chart-grid" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"></line>
              <text class="dev-chart-axis" x="${padding.left - 12}" y="${y + 4}" text-anchor="end">${value}</text>
            `;
          }).join("")}
          <path class="dev-chart-area" d="${area}"></path>
          <path class="dev-chart-line" d="${line}"></path>
          ${points.map((point) => `
            <g>
              <circle class="dev-chart-point" cx="${point.x}" cy="${point.y}" r="4.5"></circle>
              <text class="dev-chart-axis" x="${point.x}" y="${height - 12}" text-anchor="middle">${escapeHtml(point.short)}</text>
            </g>
          `).join("")}
        </svg>
        <div class="dev-chart-legend">
          ${series.map((item) => `
            <div class="dev-chart-chip">
              <strong>${escapeHtml(item.full)}</strong>
              <span>${compactNumber(item.count)} commit${item.count === 1 ? "" : "s"}</span>
            </div>
          `).join("")}
        </div>
      </div>
    </div>
  `;
}
