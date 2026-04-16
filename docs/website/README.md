# Silica-X Website

This folder contains the static documentation website for Silica-X.

## Purpose

The site is intentionally plain HTML, CSS, and JavaScript so it can be:

- served by GitHub Pages
- edited without a build step
- kept close to the repository docs and release state

## Structure

### Pages

- `index.html` is the landing and project overview page
- `getting-started.html` covers installation, prerequisites, and first runs
- `download.html` links to Docker runner scripts and installation paths
- `workflow.html` explains the four main workflows and layered runtime design
- `cli-reference.html` documents commands, aliases, and common flags
- `modes.html` describes prompt, wizard, live, and source-study runtime modes
- `reporting.html` explains output formats, storage, history, and testing
- `development.html` shows repository health and GitHub activity signals
- `project.html` covers project context, author, legal use, and roadmap signals

### CSS

- `css/core/` holds shared tokens and baseline styles
- `css/layout/` holds top bar, sidebar, content, and responsive layout rules
- `css/components/` holds component-specific styling

### JavaScript

- `js/core/` holds shared docs data and helper utilities
- `js/features/` holds isolated interactive features
- `js/bootstrap/` wires the site together

### Assets

- `web_assets/media/` holds the Silica-X website image and favicon
- `web_assets/installers/` is reserved for downloadable installer assets if the site later ships mirrored copies

## Load Order

Load CSS in this order:

1. `css/core/base.css`
2. `css/layout/topbar.css`
3. `css/layout/sidebar.css`
4. `css/layout/content.css`
5. `css/components/workflow.css`
6. `css/components/modules.css`
7. `css/components/development.css`
8. `css/layout/responsive.css`

Load JavaScript in this order:

1. `js/core/site-data.js`
2. `js/core/helpers.js`
3. `js/features/sidebar.js`
4. `js/features/search.js`
5. `js/features/workflow-visual.js`
6. `js/features/easter-eggs.js`
7. `js/features/development-feed.js`
8. `js/bootstrap/app.js`

## Maintenance Rules

- Keep the site fully static.
- Keep asset paths relative so GitHub Pages works cleanly.
- Put shared tokens and reusable components in the shared CSS modules.
- Keep page-specific behavior out of HTML where possible.
- Favor repository-accurate wording over marketing claims that the codebase does not support yet.

## Verification

Local JavaScript parse checks:

```powershell
node --check docs/website/js/core/site-data.js
node --check docs/website/js/core/helpers.js
node --check docs/website/js/features/sidebar.js
node --check docs/website/js/features/search.js
node --check docs/website/js/features/workflow-visual.js
node --check docs/website/js/features/easter-eggs.js
node --check docs/website/js/features/development-feed.js
node --check docs/website/js/bootstrap/app.js
```
