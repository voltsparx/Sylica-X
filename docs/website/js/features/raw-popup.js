const RawPopup = (() => {
  let backdrop = null;
  let titleNode = null;
  let metaNode = null;
  let bodyNode = null;
  let rawLinkNode = null;
  let repoLinkNode = null;
  let bound = false;

  function ensureViewer() {
    if (backdrop) {
      return;
    }

    backdrop = document.createElement("div");
    backdrop.className = "raw-viewer-backdrop";
    backdrop.hidden = true;
    backdrop.innerHTML = `
      <div class="raw-viewer-window" role="dialog" aria-modal="true" aria-label="Repository file preview">
        <div class="raw-viewer-head">
          <div>
            <div class="raw-viewer-title">Repository File</div>
            <div class="raw-viewer-meta"></div>
          </div>
          <button class="raw-viewer-close" type="button" aria-label="Close repository file preview">Close</button>
        </div>
        <div class="raw-viewer-actions">
          <a class="raw-viewer-link" data-role="raw" href="#" target="_blank" rel="noreferrer">Open Raw</a>
          <a class="raw-viewer-link" data-role="repo" href="#" target="_blank" rel="noreferrer">View On GitHub</a>
        </div>
        <pre class="raw-viewer-body">Loading...</pre>
      </div>
    `;

    document.body.appendChild(backdrop);
    titleNode = backdrop.querySelector(".raw-viewer-title");
    metaNode = backdrop.querySelector(".raw-viewer-meta");
    bodyNode = backdrop.querySelector(".raw-viewer-body");
    rawLinkNode = backdrop.querySelector('[data-role="raw"]');
    repoLinkNode = backdrop.querySelector('[data-role="repo"]');

    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) {
        close();
      }
    });
    backdrop.querySelector(".raw-viewer-close")?.addEventListener("click", close);
  }

  function close() {
    if (!backdrop) {
      return;
    }
    backdrop.hidden = true;
  }

  async function open(link) {
    ensureViewer();

    const rawHref = link.getAttribute("href") || "";
    const repoHref = link.dataset.repoHref || rawHref;
    const title = link.dataset.rawTitle || "Repository File";
    const pathLabel = link.dataset.rawPath || rawHref;

    titleNode.textContent = title;
    metaNode.textContent = `${pathLabel} | fetching raw file`;
    bodyNode.textContent = "Loading file preview...";
    rawLinkNode.href = rawHref;
    repoLinkNode.href = repoHref;
    backdrop.hidden = false;

    try {
      const response = await fetch(rawHref);
      if (!response.ok) {
        throw new Error(`GitHub returned ${response.status}`);
      }
      const text = await response.text();
      metaNode.textContent = `${pathLabel} | inline preview`;
      bodyNode.textContent = text.trimEnd();
    } catch (error) {
      metaNode.textContent = `${pathLabel} | preview unavailable`;
      bodyNode.textContent = `Unable to load this file preview.\n\n${error.message || "Unknown error."}`;
    }
  }

  function bind() {
    if (bound) {
      return;
    }

    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[data-raw-viewer]");
      if (!link) {
        return;
      }

      event.preventDefault();
      void open(link);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        close();
      }
    });

    bound = true;
  }

  return { bind, close };
})();
