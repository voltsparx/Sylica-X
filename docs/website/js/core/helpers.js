function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pageLink(page, id = "") {
  return id ? `${page}#${id}` : page;
}

function groupedEntries() {
  const grouped = {};

  for (const group of DocsData.groups) {
    grouped[group] = [];
  }

  for (const entry of DocsData.entries) {
    if (!grouped[entry.group]) {
      grouped[entry.group] = [];
    }
    grouped[entry.group].push(entry);
  }

  return grouped;
}

function firstEntryForGroup(group) {
  return DocsData.entries.find((entry) => entry.group === group) || null;
}

function navigateToEntry(entry) {
  if (!entry) {
    return;
  }

  const destination = pageLink(entry.page, entry.id);
  const current = `${DocsState.currentPage}${window.location.hash || ""}`;

  if (destination === current) {
    const node = document.getElementById(entry.id);
    if (node) {
      DocsState.currentSection = entry.id;
      window.history.replaceState(null, "", destination);
      updateSidebar();
      node.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    return;
  }

  window.location.href = destination;
}

function setNavOpen(nextState) {
  DocsState.navOpen = Boolean(nextState);
  DocsElements.body.classList.toggle("nav-open", DocsState.navOpen);
}

function currentHashId() {
  return window.location.hash ? window.location.hash.slice(1) : "";
}

function activeEntryId() {
  return currentHashId() || DocsState.currentSection || "";
}

function renderSidebarTabs() {
  if (!DocsElements.sidebarTabs) {
    return;
  }

  const filters = ["All", ...DocsData.groups];
  DocsElements.sidebarTabs.innerHTML = filters
    .map((group) => {
      const activeClass = DocsState.navGroupFilter === group ? " is-active" : "";
      return `<button class="sidebar-tab${activeClass}" type="button" data-group="${escapeHtml(group)}">${escapeHtml(group)}</button>`;
    })
    .join("");
}

function renderSidebarNav() {
  if (!DocsElements.sidebarNav) {
    return;
  }

  const groups = groupedEntries();
  const currentSectionId = activeEntryId();
  const filter = DocsState.navGroupFilter;
  const selectedGroups = filter === "All" ? Object.keys(groups) : [filter];

  DocsElements.sidebarNav.innerHTML = selectedGroups
    .filter((group) => groups[group] && groups[group].length)
    .map((group) => {
      const links = groups[group]
        .map((entry) => {
          const currentPageMatch = DocsState.currentPage === entry.page;
          const currentIdMatch = currentSectionId === entry.id;
          const activeClass = currentPageMatch && currentIdMatch ? " is-current" : "";
          const pageShort = DocsData.pages[entry.page]?.short || entry.page.replace(".html", "");
          return `
            <a class="sidebar-link${activeClass}" href="${pageLink(entry.page, entry.id)}">
              <span class="sidebar-link-title">${escapeHtml(entry.title)}</span>
              <span class="sidebar-link-hint">${escapeHtml(entry.hint)}</span>
              <span class="sidebar-link-page">${escapeHtml(pageShort)}</span>
            </a>
          `;
        })
        .join("");

      return `
        <section class="sidebar-group">
          <div class="sidebar-group-title">${escapeHtml(group)}</div>
          ${links}
        </section>
      `;
    })
    .join("");
}

function updateSidebar() {
  renderSidebarTabs();
  renderSidebarNav();
}

function githubApi(path = "") {
  return `https://api.github.com/repos/${DocsData.github.owner}/${DocsData.github.repo}${path}`;
}

function githubRaw(path = "") {
  if (!path) {
    return DocsData.github.rawBase;
  }
  return `${DocsData.github.rawBase}/${path.replace(/^\/+/, "")}`;
}

function githubBlob(path = "") {
  return `${DocsData.github.repoUrl}/blob/${DocsData.github.branch}/${path.replace(/^\/+/, "")}`;
}

function compactNumber(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(number);
}

function formatDate(value) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function formatRelativeTime(value) {
  if (!value) {
    return "n/a";
  }

  const diffMs = new Date(value).getTime() - Date.now();
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const minutes = Math.round(diffMs / 60000);
  if (Math.abs(minutes) < 60) {
    return rtf.format(minutes, "minute");
  }
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 48) {
    return rtf.format(hours, "hour");
  }
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 30) {
    return rtf.format(days, "day");
  }
  const months = Math.round(days / 30);
  if (Math.abs(months) < 12) {
    return rtf.format(months, "month");
  }
  const years = Math.round(months / 12);
  return rtf.format(years, "year");
}

function initContactPopover() {
  if (!DocsElements.contactToggle || !DocsElements.contactPopover) {
    return;
  }

  const close = () => {
    DocsElements.contactToggle.setAttribute("aria-expanded", "false");
    DocsElements.contactPopover.hidden = true;
  };

  const open = () => {
    DocsElements.contactToggle.setAttribute("aria-expanded", "true");
    DocsElements.contactPopover.hidden = false;
  };

  DocsElements.contactToggle.addEventListener("click", () => {
    const isOpen = DocsElements.contactToggle.getAttribute("aria-expanded") === "true";
    if (isOpen) {
      close();
      return;
    }
    open();
  });

  document.addEventListener("click", (event) => {
    if (!DocsElements.contactPopover.contains(event.target) && !DocsElements.contactToggle.contains(event.target)) {
      close();
    }
  });
}
