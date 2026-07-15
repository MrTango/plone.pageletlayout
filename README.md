# Plonetheme Pagelet Base

The rendering base for pagelet-based Plone Blicca (Classic UI) themes. It owns
the **machinery** and the **markup contract**; a theme (e.g. `plonetheme.clara`)
supplies the look through CSS tokens.

## What it ships

- **The pagelet layout stack** — the Five-compatible `plone:pagelet` /
  `plone:chromepagelet` / `plone:template` / `plone:layout` ZCML directives, and
  a single whole-body `OrderedViewletManager` (`plone.pageletlayout.layout`)
  holding a flat list of ~13 element pagelets (logo, nav, breadcrumbs,
  contentheader, body, footer, …). Order and visibility come from
  `IViewletSettingsStorage`.
- **Two published views per type** — `pagelet_view` (managed: reorder/hide via
  the storage) and `pagelet_view_flat` (fixed code order), sharing one shell.
  The FTI default flips to `pagelet_view`.
- **Management screens** — `@@manage-layout-viewlets` (reorder + hide/show) and
  `@@manage-layout-viewlets-flat` (inspection-only).
- **The markup contract + layout primitives** — semantic templates with stable
  `.element-*` / `.plone-*` hooks, cascade layers, layout primitives (Stack,
  Cluster, Sidebar, Switcher, Grid, Center), default `--plone-*` tokens, and the
  Bootstrap `--bs-*` → `--plone-*` bridge. See
  [Clara's theming architecture](../plonetheme.clara/docs/clara-theming-architecture.md)
  for the full contract — this base implements it.

Chrome computation is **reused, not forked**: the global sections, breadcrumbs,
byline, status messages and head plumbing wrap the stock `plone.app.layout`
viewlets/helpers, so upstream fixes still arrive.

## Features

- Compatible with Plone 6.2+
- Un-themed, single-column, whole-body layout (no Diazo, no Barceloneta skeleton)

## Installation

Add `plone.pageletlayout` to your project's dependencies:

```python
# In your pyproject.toml
dependencies = [
    "plone.pageletlayout",
    # ...
]
```

Then activate the addon in your Plone site's control panel or via GenericSetup.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/collective/plone.pageletlayout.git
cd plone.pageletlayout

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[test]"
```

### Running Tests

```bash
pytest
```

### Running Tests with Coverage

```bash
pytest --cov=plone.pageletlayout --cov-report=html
```

## License

GPL-2.0-or-later

## Author

Maik Derstappen <md@derico.de>
