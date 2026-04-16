function buildWorkflowRail(railElement) {
  if (!railElement) {
    return;
  }

  const render = () => {
    railElement.innerHTML = DocsData.workflowStages
      .map((stage, index) => {
        const pills = stage.pills.map((pill) => `<span class="pill">${escapeHtml(pill)}</span>`).join("");
        const expanded = index === 0 ? "true" : "false";
        const activeClass = index === 0 ? " is-active" : "";
        return `
          <article class="workflow-stage${activeClass}" data-key="${escapeHtml(stage.key)}">
            <button class="workflow-stage-trigger" type="button" aria-expanded="${expanded}">
              <div class="workflow-stage-top">
                <span class="workflow-stage-index">${escapeHtml(stage.label)}</span>
                <span class="pill">${escapeHtml(stage.title)}</span>
              </div>
              <div class="workflow-stage-summary">${escapeHtml(stage.summary)}</div>
            </button>
            <div class="workflow-stage-body">
              <div class="stage-detail">
                <h3>${escapeHtml(stage.title)}</h3>
                <p>${escapeHtml(stage.detail)}</p>
                <div class="stage-detail-meta">${pills}</div>
              </div>
            </div>
          </article>
        `;
      })
      .join("");
  };

  const activate = (article) => {
    for (const node of railElement.querySelectorAll(".workflow-stage")) {
      const trigger = node.querySelector(".workflow-stage-trigger");
      const isActive = node === article;
      node.classList.toggle("is-active", isActive);
      trigger?.setAttribute("aria-expanded", isActive ? "true" : "false");
    }
  };

  render();

  railElement.addEventListener("click", (event) => {
    const trigger = event.target.closest(".workflow-stage-trigger");
    if (!trigger) {
      return;
    }

    const article = trigger.closest(".workflow-stage");
    if (!article) {
      return;
    }

    const alreadyOpen = article.classList.contains("is-active");
    if (alreadyOpen) {
      article.classList.remove("is-active");
      trigger.setAttribute("aria-expanded", "false");
      return;
    }

    activate(article);
  });
}

function initWorkflowVisuals() {
  buildWorkflowRail(DocsElements.workflowRail);
  buildWorkflowRail(DocsElements.homeWorkflowRail);
}
