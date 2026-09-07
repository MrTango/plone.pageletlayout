# Changelog

## 1.0.0a1 (unreleased)

- Initial release.
- The 1003 viewlets re-import no longer evicts other add-ons' elements.
  `profiles/default/viewlets.xml` states the layout order in full, and
  GenericSetup applies a restated order by *removing each name and appending
  it* — so on a site where an add-on had anchored an element into the sequence
  (`plonetheme.clara.subnav` below the body,
  `collective.blicca.footerblocks.footerblocks` above the footer rows) all
  twenty-one of our names moved past it and the add-on's element ended up
  first on the page: the site's footer rendered above its logo. Anchoring our
  own entries would not have fixed it — an anchor is evaluated against the
  order as it stands mid-import, so a foreign element sitting on one is
  stepped over and drifts a little further with every re-import. What the
  foreign entries mean is "keep me next to *this* neighbour", so
  `upgrades/viewlet_order.py` preserves exactly that: snapshot the order, let
  the import restate ours, put every name that is not ours back behind the
  neighbour it had. A site already upgraded by the previous step is repaired
  by re-running the add-on's own `viewlets` step, whose
  `insert-after`/`insert-before` anchors stay authoritative.
- Plone's stock viewlet managers are bridged into the layout. The layout
  rendered exactly one manager — its own — so every viewlet an add-on
  registers into `IAboveContentBody`, `IPortalFooter`, `IBelowContentBody`, …
  vanished from a pagelet page with no exception and no log line. Stock Plone
  alone lost lock info, the table of contents, contributors, keywords,
  related items, rights, the document actions and the footer portlets. Eight
  managers now render as ordinary layout elements (portaltop, portalheader,
  mainnavigation, abovecontent, abovecontentbody, belowcontentbody,
  belowcontent, portalfooter — storage-managed, so hideable and reorderable
  like every other element), and the three that are positions *inside* a
  title block (abovecontenttitle, belowcontenttitle, belowcontentdescription)
  render inside the content header. One generic class parameterized per
  registration, the way `PageletViewlet` already was; the manager is looked
  up in code against `self.view`, so viewlets bound to a form
  (`view=IDexterityEditForm`) still bind.
- The nine stock viewlets this package reimplements are hidden in
  `profiles/default/viewlets.xml` — bridging without hiding would render
  logo, breadcrumbs, byline, colophon and site actions twice. Configuration,
  not a code-level exemption: unhide any of them and hide the corresponding
  element instead. One duplication the profile cannot resolve is documented
  in docs/porting-main-template.md: `plone.footer` renders the footer
  *portlet* manager, whose default assignments repeat the colophon and the
  site actions.
- Every viewlet that renders through a bridge logs a deprecation signal
  naming itself, the class its add-on wrote, the stock manager and the fix
  (register into `ILayoutManager`) — the two-tier rate limit the
  main_template bridge already uses. And because that signal can only speak
  for viewlets that *do* render, `tests/test_viewlet_ratchet.py` meters the
  rest: every reachable viewlet whose manager nothing renders is pinned in a
  checked-in allowlist that can only shrink.
- `plone:chromepagelet` accepts arbitrary keyword arguments and sets them as
  class attributes, the contract `plone:pagelet` and stock `browser:viewlet`
  already had. That is what lets one class serve many registrations.
- The status-messages element renders the stock `plone.globalstatusmessage`
  viewlet *manager* instead of re-implementing its message loop. The loop is
  only the manager's first entry: plone.app.dexterity registers the
  default-page warning next to it ("You are editing the default view of a
  container", bound to `view=IDexterityEditForm`) and plone.volto its backend
  warning, so the old element dropped every sibling viewlet — editing a
  folder's default page showed no warning at all. The manager is looked up in
  code against `self.view`, the published view: a Dexterity edit form's
  wrapper is what provides `IDexterityEditForm`, and a `provider:` expression
  in the pagelet's own template would hand the manager the pagelet instead
  (the BodyChromePagelet lesson). The pagelet keeps only the themed `aside`
  shell; `MTYPES_DISPLAY` and the copied message loop are gone, which also
  drops a duplicated literal `alert` class from the rendered markup.
- The main_template bridge's chrome is storage-managed. The frame called a
  template-fixed list of provider names, so a bridged page rendered only the
  elements this package happens to ship in that list: an element a theme adds
  to `plone.pageletlayout.layout` (viewlets.xml) appeared on pagelet pages and
  never on a classic one, and reordering or hiding in
  `@@manage-layout-viewlets` had no effect there either — the byline and the
  social tags were missing from every bridged page for the same reason. It now
  renders the manager, split around the inline body region at
  `plone.pageletlayout.body`; only the content's position stays fixed, because
  METAL slots must sit inline and a provider's render is opaque to slot
  filling. The contentheader stays inline too — the classic contract emits
  title and description inside the content article, through slots a consumer
  may fill, and rendering the element as well would print both.
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
