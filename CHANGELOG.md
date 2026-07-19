# Changelog

## 1.0.0a1 (unreleased)

- Initial release.
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
