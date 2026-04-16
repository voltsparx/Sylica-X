const EasterEgg = (() => {
  let toastTimer = null;
  let overdriveTimer = null;
  let versionPressTimer = null;
  let menuPressTimer = null;
  let brandTapCount = 0;
  let brandTapTimer = null;
  let heroTapCount = 0;
  let heroTapTimer = null;

  const secretQueries = {
    fusioncore: () => activateOverdrive("Fusion lane synchronized"),
    threatconductor: () => showToast("Threat conductor armed", "Priority signal stack elevated."),
    orbitmatrix: () => showToast("Orbit link matrix", "Outbound link constellation projected."),
    ember: () => toggleBlueprintMode(),
    sylica: () => showToast("Legacy alias detected", "Public naming stays Silica-X.")
  };

  function ensureToast() {
    let toast = document.getElementById("egg-toast");
    if (toast) {
      return toast;
    }

    toast = document.createElement("div");
    toast.id = "egg-toast";
    toast.className = "egg-toast";
    toast.setAttribute("aria-live", "polite");
    DocsElements.body.appendChild(toast);
    return toast;
  }

  function showToast(title, copy = "") {
    const toast = ensureToast();
    toast.innerHTML = `<span class="egg-toast-title">${escapeHtml(title)}</span><span class="egg-toast-copy">${escapeHtml(copy)}</span>`;
    toast.classList.add("show");

    if (toastTimer) {
      window.clearTimeout(toastTimer);
    }

    toastTimer = window.setTimeout(() => {
      toast.classList.remove("show");
    }, 2200);
  }

  function pulseLogo(node) {
    if (!node) {
      return;
    }
    node.classList.remove("egg-logo-pulse");
    void node.offsetWidth;
    node.classList.add("egg-logo-pulse");
  }

  function spawnRibbons(count = 18) {
    const layer = document.createElement("div");
    layer.className = "egg-ribbon-layer";
    DocsElements.body.appendChild(layer);

    const palette = ["#ff8a1d", "#ffb259", "#ffd36f", "#73d4ff", "#67d6a8"];
    const total = Math.max(10, Math.min(count, 40));

    for (let index = 0; index < total; index += 1) {
      const ribbon = document.createElement("span");
      ribbon.className = "egg-ribbon";
      ribbon.style.left = `${Math.random() * 100}%`;
      ribbon.style.background = `linear-gradient(180deg, ${palette[index % palette.length]}, rgba(255,255,255,0.12))`;
      ribbon.style.setProperty("--egg-drift", `${(Math.random() * 220) - 110}px`);
      ribbon.style.animationDuration = `${2.8 + (Math.random() * 1.8)}s`;
      ribbon.style.animationDelay = `${Math.random() * 0.25}s`;
      layer.appendChild(ribbon);
    }

    window.setTimeout(() => {
      layer.remove();
    }, 4200);
  }

  function activateOverdrive(message) {
    DocsElements.body.classList.add("egg-overdrive");
    pulseLogo(DocsElements.topbarLogo);
    pulseLogo(DocsElements.homeHeroLogo);
    showToast(message, "Signal intensity boosted for a short burst.");

    if (overdriveTimer) {
      window.clearTimeout(overdriveTimer);
    }

    overdriveTimer = window.setTimeout(() => {
      DocsElements.body.classList.remove("egg-overdrive");
    }, 7000);
  }

  function toggleBlueprintMode() {
    const enabled = DocsElements.body.classList.toggle("egg-blueprint");
    showToast(
      enabled ? "Blueprint grid enabled" : "Blueprint grid disabled",
      enabled ? "Architecture view switched to wireframe emphasis." : "Back to standard operator view."
    );
  }

  function toggleCleanScreen() {
    const enabled = DocsElements.body.classList.toggle("egg-clean-screen");
    showToast(
      enabled ? "Clean screen mode" : "Full signal mode",
      enabled ? "Background circuitry softened." : "Ambient circuitry restored."
    );
  }

  function bindBrandCombo() {
    if (!DocsElements.topbarBrand || !DocsElements.topbarLogo) {
      return;
    }

    DocsElements.topbarBrand.addEventListener("click", (event) => {
      event.preventDefault();
      brandTapCount += 1;
      pulseLogo(DocsElements.topbarLogo);

      if (brandTapTimer) {
        window.clearTimeout(brandTapTimer);
      }

      brandTapTimer = window.setTimeout(() => {
        brandTapCount = 0;
      }, 1900);

      if (brandTapCount >= 7) {
        brandTapCount = 0;
        spawnRibbons(24);
        showToast("Ribbon fall unlocked", "Brand console accepted seven taps.");
      }
    });
  }

  function bindHeroCombo() {
    if (!DocsElements.homeHeroLogo) {
      return;
    }

    DocsElements.homeHeroLogo.addEventListener("click", () => {
      heroTapCount += 1;
      pulseLogo(DocsElements.homeHeroLogo);

      if (heroTapTimer) {
        window.clearTimeout(heroTapTimer);
      }

      heroTapTimer = window.setTimeout(() => {
        heroTapCount = 0;
      }, 1500);

      if (heroTapCount >= 4) {
        heroTapCount = 0;
        showToast("Signal fusion ready", "Homepage mark acknowledged the operator.");
      }
    });
  }

  function bindVersionLongPress() {
    if (!DocsElements.topbarVersion) {
      return;
    }

    const start = () => {
      versionPressTimer = window.setTimeout(() => {
        toggleBlueprintMode();
      }, 720);
    };

    const stop = () => {
      if (versionPressTimer) {
        window.clearTimeout(versionPressTimer);
        versionPressTimer = null;
      }
    };

    DocsElements.topbarVersion.addEventListener("mousedown", start);
    DocsElements.topbarVersion.addEventListener("mouseup", stop);
    DocsElements.topbarVersion.addEventListener("mouseleave", stop);
    DocsElements.topbarVersion.addEventListener("touchstart", start, { passive: true });
    DocsElements.topbarVersion.addEventListener("touchend", stop);
    DocsElements.topbarVersion.addEventListener("touchcancel", stop);
  }

  function bindMenuLongPress() {
    if (!DocsElements.menuToggle) {
      return;
    }

    const start = () => {
      menuPressTimer = window.setTimeout(() => {
        toggleCleanScreen();
      }, 780);
    };

    const stop = () => {
      if (menuPressTimer) {
        window.clearTimeout(menuPressTimer);
        menuPressTimer = null;
      }
    };

    DocsElements.menuToggle.addEventListener("mousedown", start);
    DocsElements.menuToggle.addEventListener("mouseup", stop);
    DocsElements.menuToggle.addEventListener("mouseleave", stop);
    DocsElements.menuToggle.addEventListener("touchstart", start, { passive: true });
    DocsElements.menuToggle.addEventListener("touchend", stop);
    DocsElements.menuToggle.addEventListener("touchcancel", stop);
  }

  function bindSearchSecrets() {
    if (!DocsElements.searchInput) {
      return;
    }

    DocsElements.searchInput.addEventListener("input", () => {
      const query = DocsElements.searchInput.value.trim().toLowerCase().replace(/\s+/g, "");
      const fn = secretQueries[query];
      if (fn) {
        fn();
      }
    });
  }

  function init() {
    bindBrandCombo();
    bindHeroCombo();
    bindVersionLongPress();
    bindMenuLongPress();
    bindSearchSecrets();
  }

  return { init };
})();
