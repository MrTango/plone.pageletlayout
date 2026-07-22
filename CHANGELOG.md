# Changelog

## 1.0.0a1 (unreleased)

- Initial release.
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
