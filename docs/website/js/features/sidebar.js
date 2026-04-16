function initSidebar() {
  updateSidebar();

  DocsElements.sidebarTabs?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-group]");
    if (!button) {
      return;
    }

    const group = button.dataset.group || "All";
    DocsState.navGroupFilter = group;
    updateSidebar();

    if (group !== "All") {
      navigateToEntry(firstEntryForGroup(group));
    }
  });

  DocsElements.menuToggle?.addEventListener("click", () => {
    setNavOpen(!DocsState.navOpen);
  });

  DocsElements.sidebarBackdrop?.addEventListener("click", () => {
    setNavOpen(false);
  });

  window.addEventListener("hashchange", () => {
    updateSidebar();
  });

  document.addEventListener("click", (event) => {
    const link = event.target.closest(".sidebar-link");
    if (!link) {
      return;
    }
    setNavOpen(false);
  });
}
