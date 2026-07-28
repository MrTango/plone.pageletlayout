# Changelog

## 1.0.0a1 (unreleased)

- Initial release.
- `sitemap` and `contact-info` are pagelets (classic-coverage ticket 10),
  the map's last two conversions — both stock CMFPlone classes reused whole
  on the FramedPage mechanism. `contact-info` turned out **not** to be a
  wrapped form (a bare `AutoExtensibleForm` registered directly), so the S1
  seam never covered it; being a modal action, it relies on the framed
  `#content` extraction point. The sitemap's tree markup is built in Python,
  so `_renderLevel` and the item template are overridden: the dead
  Barceloneta hooks (`navTree*`, `visualNoMarker`) give way to
  `#portal-sitemap` / `.plone-sitemap__level` and `aria-current="page"`,
  while `state-*` and `contenttype-*` — the hooks with rules behind them —
  stay. With these two off `tests/main_template_allowlist.txt` (103 → 101),
  every ticket-marked section of the ratchet allowlist is gone: what remains
  is the steady-state admin long tail on the permanent bridge.
- The verification harness (classic-coverage ticket 04), two meters in the
  test suite. The live-surface walk (`tests/test_live_surface.py`) fetches
  the charting plan's probe corpus — site root, `folder_contents`,
  `@@search`, `sitemap`, `contact-info`, `login`, `edit`,
  `@@overview-controlpanel`, `@@usergroup-userprefs`,
  `@@personal-information`, `@@sharing`, `@@historyview` — through the
  publisher as the site owner and asserts every response carries the
  pagelet frame and zero classic master markup. The static ratchet
  (`tests/test_static_ratchet.py`) walks the component registry (including
  plone.testing's stacked-registry bases) for reachable, unshadowed
  registrations whose template still references `main_template` and
  compares them against `tests/main_template_allowlist.txt` (119 entries,
  grouped by the map ticket that removes them): a new macro consumer
  fails, and a converted/shadowed one fails too until its line is deleted
  — the ratchet clicks down. Registration shadowing is part of the meter:
  a layer-specific override (like ticket 05's `ILayoutTemplate`) drops
  its victim from the collection automatically.
- The main_template compatibility bridge (classic-coverage ticket 01): the
  `main_template` view is shadowed on the pageletlayout layer by a
  pagelet-frame template exposing the compatible `master` and nested
  `content` macros (all classic slot names: head slots,
  `global_statusmessage`, `content`/`body`/`main`/`content-title`/
  `content-description`/`content-core`), so every unconverted classic
  consumer — add-ons included — renders pagelet chrome untouched. Chrome
  elements render template-fixed in the canonical `layout.ELEMENTS` order
  (bridge pages are not storage-managed — accepted tradeoff), classic
  slots land inside the `element-body` region, `X-Theme-Disabled` is set
  post-styles like `PageletPage.__call__`, and the pagelet `htmltitle`
  owns the single head `<title>`. A permanent, undocumented shim: macros
  keep working but everything new is built on `plone:pagelet`.
- The macro-path deprecation signal (classic-coverage ticket 02): whenever
  a page renders through the bridged `master` macro, the bridge logs which
  template bound the macro (the TAL `template` at macro-render time — the
  same object classic main_template passes to `bodyClass`) and points at
  the new add-on-author how-to `docs/porting-main-template.md`. WARNING on
  every render in development mode (`getConfiguration().debug_mode`), INFO
  once per consumer per process in production. Converted pagelet pages
  never touch the macro path and stay silent.
- The `ajax` layout & the fragment contract (docs/request-layouts.md §6):
  `?pagelet_layout=ajax` — and stock `ajax_load=1`, whose alias trigger is
  now live — returns the fragment-contract document stock Mockup patterns
  extract from: a full document with a charset-only head, the
  fully-attributed `<body>` (bodyClass + `pagelet-layout-ajax`, `dir`,
  patterns-settings data attributes), then `.portalMessage` status messages
  and `<article id="content">` wrapping the first-`h1` content header and
  the `#content-core` body. No toolbar, no chrome. The element set is fixed
  by construction (`AjaxRegion`, a dedicated `ajax.pt` frame on
  `IAjaxLayoutLayer`), and every ajax response carries `X-Theme-Disabled: 1`
  and `X-Robots-Tag: noindex` on both param spellings. `#content` stays
  ajax-only; `layout_name` reports `ajax` alias-free.
- Request-time layout selection: the trigger chain
  (docs/request-layouts.md §4–§6). One `IPubAfterTraversal` subscriber
  applies at most one layout layer per request — `?pagelet_layout=<name>`
  beats the `ajax_load` alias beats a registry entry's static view marker;
  `?pagelet_layout=default` is the escape hatch; unknown names log one
  warning on `plone.pageletlayout.layouts` and fall through. `fullscreen`
  is the first registered layout (`IFullscreenLayoutLayer`,
  `view_marker=IFullScreenPagelet`): the `BodyOnlyRegion` shadow moved
  from the `view=` to the `layer=` dimension, so any pagelet page can be
  requested fullscreen while `folder_contents` keeps it as its unchanged
  static default. Templates read the resolved name via `view/layout_name`
  (lazy, alias-free, `"default"` when nothing fired), and the shared frame
  stamps `pagelet-layout-<name>` on `<body>` alongside bodyClass.
- `plone:pagelayout` directive + the layout registry
  (docs/request-layouts.md §1–§3): one validated stanza binds a layout name
  to a hand-written layout layer (plus an optional static view marker) as
  an `IPageLayout` named utility, enumerable via
  `getUtilitiesFor(IPageLayout)`. Config-time rejections: the reserved name
  `default`, a layer not extending `IPlonePageletlayoutLayer`, a
  `view_marker` not extending `IPagelet`. Nothing consumes the registry
  yet — the trigger chain (ticket 08) is next.
- `folder_contents` is a pagelet: the pat-structure management UI publishes
  through the whole-body layout as the first FULL-SCREEN view (the
  docs/directives.md recipe, shipped) — `IFullScreenPagelet` on the
  published view flips the page region to `BodyOnlyRegion` (body element
  only; `<head>` plumbing and toolbar stay, logo/nav/breadcrumbs/footer
  go). Options JSON delegates to the stock `FolderContentsView`. Consumers
  get a full-screen page with a single `plone:pagelet` stanza carrying
  `provides="plone.pageletlayout.interfaces.IFullScreenPagelet"`.
- `globalnav.pt` ships a nav-level disclosure (`#portal-globalnav-opener`
  checkbox + `.globalnav-toggle` label), the same native pure-CSS `.opener`
  idiom as the per-section toggles. Themes collapse the bar on narrow
  viewports from CSS alone; a theme that never collapses keeps both
  `display: none`.
- `plone:pagelet` / `plone:chromepagelet` ergonomics: optional `class`
  (template-only registrations), inline `template=`, and multi-interface
  `for=` on all four directives — modeled on gocept.pagelet (prior art,
  re-derived; no code copied, no dependency). Grammar reference:
  `docs/directives.md`.
