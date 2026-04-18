function initSearch() {
  if (!DocsElements.searchInput || !DocsElements.searchResults) {
    return;
  }

  const hideResults = () => {
    DocsElements.searchResults.hidden = true;
    DocsElements.searchResults.innerHTML = "";
  };

  const showResults = (results) => {
    if (!results.length) {
      DocsElements.searchResults.hidden = false;
      DocsElements.searchResults.innerHTML = '<div class="empty-state">No matching section or page.</div>';
      return;
    }

    DocsElements.searchResults.hidden = false;
    DocsElements.searchResults.innerHTML = results
      .map((item) => {
        return `
          <a class="search-result" href="${pageLink(item.page, item.id)}">
            <span class="search-result-title">${escapeHtml(item.title)}</span>
            <span class="search-result-meta">${escapeHtml(item.group)} | ${escapeHtml(DocsData.pages[item.page]?.title || item.page)} | ${escapeHtml(item.hint)}</span>
          </a>
        `;
      })
      .join("");
  };

  DocsElements.searchInput.addEventListener("input", () => {
    const query = DocsElements.searchInput.value.trim().toLowerCase();
    if (!query) {
      hideResults();
      return;
    }

    const results = DocsData.entries
      .filter((entry) => {
        const haystack = `${entry.title} ${entry.hint} ${entry.group} ${entry.page}`.toLowerCase();
        return haystack.includes(query);
      })
      .slice(0, 8);

    showResults(results);
  });

  DocsElements.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideResults();
      DocsElements.searchInput.blur();
    }
  });

  document.addEventListener("click", (event) => {
    if (!DocsElements.searchResults.contains(event.target) && !DocsElements.searchInput.contains(event.target)) {
      hideResults();
    }
  });
}
