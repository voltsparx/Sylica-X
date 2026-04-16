const DocsData = (() => {
  const pages = {
    "index.html": { title: "Overview", short: "Home" },
    "getting-started.html": { title: "Getting Started", short: "Start" },
    "download.html": { title: "Download", short: "DL" },
    "workflow.html": { title: "Workflow", short: "Flow" },
    "cli-reference.html": { title: "CLI Reference", short: "CLI" },
    "modes.html": { title: "Modes", short: "Modes" },
    "reporting.html": { title: "Reporting", short: "Reports" },
    "development.html": { title: "Development", short: "Dev" },
    "project.html": { title: "Project", short: "Project" }
  };

  const entries = [
    { id: "home", title: "Overview", page: "index.html", hint: "Landing page, project identity, and release snapshot.", group: "Start Here" },
    { id: "core-idea", title: "What Silica-X Is", page: "index.html", hint: "The actual problem the framework is solving.", group: "Start Here" },
    { id: "how-it-works", title: "How It Works", page: "index.html", hint: "Execution flow from commands to outputs.", group: "Start Here" },
    { id: "quickstart-30", title: "Quick Start", page: "index.html", hint: "Five-line path from clone to prompt mode.", group: "Start Here" },
    { id: "fit-check", title: "Use It / Skip It", page: "index.html", hint: "When Silica-X is the right fit and when it is not.", group: "Start Here" },
    { id: "install", title: "Installation", page: "getting-started.html", hint: "Source setup, Python support, and dependencies.", group: "Start Here" },
    { id: "quickstart", title: "First Run", page: "getting-started.html", hint: "Prompt mode, help flow, and common first commands.", group: "Start Here" },
    { id: "prereqs", title: "Prerequisites", page: "getting-started.html", hint: "System requirements, optional dev tooling, and safe-use expectations.", group: "Start Here" },
    { id: "download-home", title: "Download Hub", page: "download.html", hint: "Where Docker runner scripts and runtime helpers live.", group: "Downloads" },
    { id: "download-scripts", title: "Runner Scripts", page: "download.html", hint: "Linux, macOS, Windows, and Termux wrappers.", group: "Downloads" },
    { id: "download-usage", title: "Docker Usage", page: "download.html", hint: "How the runner forwards commands and controls upgrades.", group: "Downloads" },
    { id: "download-paths", title: "Install Paths", page: "download.html", hint: "Where the runtime, compose files, and outputs live.", group: "Downloads" },
    { id: "how", title: "Mental Model", page: "workflow.html", hint: "Four workflow lanes and the operator mental model.", group: "Architecture" },
    { id: "pipeline", title: "Execution Pipeline", page: "workflow.html", hint: "Policy, engine, capability, filter, fusion, and report flow.", group: "Architecture" },
    { id: "modules", title: "Plugin / Filter System", page: "workflow.html", hint: "How extensions, scopes, and catalogs fit together.", group: "Architecture" },
    { id: "commands", title: "Commands", page: "cli-reference.html", hint: "Primary commands, aliases, and what they do.", group: "Operator" },
    { id: "flags", title: "Flags", page: "cli-reference.html", hint: "High-value output, explain, and scope controls.", group: "Operator" },
    { id: "syntax", title: "Syntax Patterns", page: "cli-reference.html", hint: "Prompt, flag, and example command grammar.", group: "Operator" },
    { id: "prompt-mode", title: "Prompt Mode", page: "modes.html", hint: "Interactive mode with help, defaults, and shortcuts.", group: "Runtime" },
    { id: "wizard-mode", title: "Wizard Mode", page: "modes.html", hint: "Guided interactive workflow for multi-step scans.", group: "Runtime" },
    { id: "live-dashboard", title: "Live Dashboard", page: "modes.html", hint: "Local browser dashboard for saved results.", group: "Runtime" },
    { id: "source-study", title: "Source-Study Modes", page: "modes.html", hint: "Frameworks and surface-kit commands for local source translation.", group: "Runtime" },
    { id: "outputs", title: "Output Formats", page: "reporting.html", hint: "CLI, JSON, CSV, HTML, and run logs.", group: "Reports" },
    { id: "storage", title: "Storage Layout", page: "reporting.html", hint: "How output directories and filenames are generated.", group: "Reports" },
    { id: "history", title: "History & Inventory", page: "reporting.html", hint: "History commands, capability packs, and runtime snapshots.", group: "Reports" },
    { id: "testing", title: "Verification", page: "reporting.html", hint: "Unit tests, Ruff, mypy, compile checks, and package smoke.", group: "Reports" },
    { id: "development-home", title: "Development", page: "development.html", hint: "Repository health, architecture slices, and automation posture.", group: "Project" },
    { id: "repo-activity", title: "Repository Activity", page: "development.html", hint: "Live GitHub repository data and recent commits.", group: "Project" },
    { id: "release-radar", title: "Release Radar", page: "development.html", hint: "Release theme, docs, roadmap, and raw signals.", group: "Project" },
    { id: "author", title: "Project Context", page: "project.html", hint: "Maintainer, naming, license, and usage boundaries.", group: "Project" },
    { id: "signals", title: "Roadmap Signals", page: "project.html", hint: "Current strengths, known gaps, and where the project is heading.", group: "Project" }
  ];

  const groups = ["Start Here", "Downloads", "Architecture", "Operator", "Runtime", "Reports", "Project"];

  const github = {
    owner: "voltsparx",
    repo: "Silica-X",
    branch: "main",
    repoUrl: "https://github.com/voltsparx/Silica-X",
    profileUrl: "https://github.com/voltsparx",
    rawBase: "https://raw.githubusercontent.com/voltsparx/Silica-X/main"
  };

  const workflowStages = [
    {
      key: "commands",
      label: "Stage 01",
      title: "Operator Input",
      summary: "Flag mode, prompt mode, and the wizard all end up producing a normalized command intent.",
      detail: "Silica-X starts with a CLI command or an interactive prompt command. The parser layer normalizes aliases like profile/scan/persona, applies prompt defaults, and resolves session output settings before any intelligence work begins.",
      pills: ["flag mode", "prompt mode", "wizard", "keywords"]
    },
    {
      key: "policy",
      label: "Stage 02",
      title: "Execution Policy + Engine",
      summary: "The runtime loads policy, selects an engine, and sets workers, timeout, and recon depth.",
      detail: "Execution policy controls the engine type, enabled capabilities, enabled filters, max workers, timeout, and enrichment depth. The runtime can dispatch through async, thread, process, hybrid, and fusion-style lanes depending on workflow and policy.",
      pills: ["execution policy", "async", "thread", "hybrid"]
    },
    {
      key: "collection",
      label: "Stage 03",
      title: "Capabilities + Adapters",
      summary: "Collectors and adapters gather profile, surface, and source data into domain entities.",
      detail: "Capabilities call adapters rather than exposing raw collector output directly. Profile lookup, domain surface collectors, source-fusion inputs, RDAP, CT, and other lanes are transformed into shared entity structures so later stages reason on a stable contract.",
      pills: ["capabilities", "adapters", "entities", "source fusion"]
    },
    {
      key: "refinement",
      label: "Stage 04",
      title: "Plugins + Filters",
      summary: "Scope-aware plugins enrich signals and filters suppress noise or prioritize risk.",
      detail: "Silica-X auto-discovers plugins and filters, checks scope compatibility, and applies them as part of a policy-driven refinement layer. This is where identity enrichment, transport stability, threat scoring, contact quality, takeover prioritization, and other operator-focused behaviors are applied.",
      pills: ["20 plugins", "17 filters", "scope-aware", "auto discovery"]
    },
    {
      key: "fusion",
      label: "Stage 05",
      title: "Fusion + Intelligence",
      summary: "The fusion engine deduplicates, correlates, scores confidence, and prepares advisory context.",
      detail: "After filtering, the fusion engine builds relationship maps, anomaly signals, confidence distributions, and risk summaries. The intelligence and advisor layers then generate next-step recommendations, priorities, and operator-readable summaries instead of leaving the result as raw scan data.",
      pills: ["correlation", "confidence", "risk summary", "advisor"]
    },
    {
      key: "reporting",
      label: "Stage 06",
      title: "Reporting + Artifacts",
      summary: "Results are rendered to CLI, JSON, CSV, HTML, logs, and capability-pack snapshots.",
      detail: "The reporting layer is presentation-only. It writes artifact files under the configured output root, keeps run logs, supports history listing, and can generate capability-pack intel artifacts so the repo can reason about its own inventory and wiring.",
      pills: ["cli", "json", "csv", "html", "history"]
    }
  ];

  return { pages, entries, groups, github, workflowStages };
})();

const DocsState = {
  currentPage: document.body.dataset.page || "index.html",
  currentSection: document.body.dataset.defaultSection || "",
  navOpen: false,
  navGroupFilter: "All"
};

const DocsElements = {
  body: document.body,
  topbarBrand: document.getElementById("topbar-brand"),
  topbarLogo: document.querySelector("#topbar-brand img"),
  topbarName: document.getElementById("topbar-name"),
  topbarVersion: document.getElementById("topbar-version"),
  sidebar: document.getElementById("sidebar"),
  sidebarTabs: document.getElementById("sidebar-tabs"),
  sidebarNav: document.getElementById("sidebar-nav"),
  sidebarBackdrop: document.getElementById("sidebar-backdrop"),
  menuToggle: document.getElementById("menu-toggle"),
  searchInput: document.getElementById("docs-search-input"),
  searchResults: document.getElementById("docs-search-results"),
  workflowRail: document.getElementById("workflow-visual-rail"),
  workflowDetail: document.getElementById("workflow-visual-detail"),
  homeWorkflowRail: document.getElementById("home-workflow-rail"),
  homeWorkflowDetail: document.getElementById("home-workflow-detail"),
  homeHeroLogo: document.querySelector(".hero-logo-frame img"),
  contactToggle: document.getElementById("contact-toggle"),
  contactPopover: document.getElementById("contact-popover"),
  repoHealth: document.getElementById("repo-health"),
  commitFeed: document.getElementById("commit-feed"),
  releaseFeed: document.getElementById("release-feed")
};
