# Modules Catalog

Generated index for module-like capabilities discovered under `intel-sources/`.

- `index.json`: full catalog with capability tags, scoring, and scope hints
- `plugin-modules.json`: plugin-like subset
- `filter-modules.json`: filter-like subset

Refresh from CLI:
- `python silica-x.py modules --sync`

Advanced query examples:
- `python silica-x.py modules --search dns --sort-by power_score --descending`
- `python silica-x.py modules --kind plugin --tag identity --min-score 55`
