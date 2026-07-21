# Request-time page layouts

Status: **locked** (signed off by Maik, 2026-07-21 — wayfinder effort
`request-layouts`). This spec is the complete input to the implementation
effort: building it should require no new decisions.

`plone.pageletlayout` gains **named page layouts**: a request selects among
registered whole-page presentations via `?pagelet_layout=<name>`, with stock
Plone's `ajax_load=1` honored as an alias. Three layouts ship — `default`,
`fullscreen`, `ajax` — and the fullscreen/ajax special cases dissolve into
one general mechanism that future layouts (print, embed, …) join without new
machinery. Static per-view defaults (today's `IFullScreenPagelet`
`provides=` recipe, [directives.md](directives.md#recipe-a-full-screen-view))
survive unchanged and resolve through the same machinery; the query param
overrides them.

Terminology throughout is the locked glossary in
[CONTEXT.md](../CONTEXT.md) — *page layout*, *layout name*, *layout layer*,
*layout registry*, *layout declaration*, *trigger chain*, *static view
marker*, *ajax layout*, *fragment contract*, *layout body class*.

## 1. The model: the layer is the layout

A **page layout** is expressed by a **layout layer** — a request-marker
interface. One post-traversal subscriber applies **at most one** layout
layer per request (section 3). Everything a layout changes is then ordinary
ZCML: registrations shadowing shipped providers with `layer=` that marker —
the same two-stanza shape as today's fullscreen recipe, moved from the
`view=` dimension to the `layer=` dimension.

What a layout's layer may shadow:

- **The page region** (`plone.pageletlayout.pagelayout`) — the **required
  minimum**. Every layout must keep the provider name resolvable (the
  no-guard guarantee: `layout.pt` renders `provider:` unguarded; a failed
  lookup raises at render time). Shadow the provider, never unregister it.
- **Head providers** (`plone.pageletlayout.htmltitle`, `.headmeta`,
  `.headlinks`, `.styles`, `.scripts`) — optional.
- **The frame** itself (`plone:layout` with `layer=`) — optional; template
  adapters carry the layer dimension (verified in metaconfigure). The ajax
  layout is the shipped example.

The **toolbar** (`provider:plone.toolbar`) is a foreign, self-gating
subsystem the mechanism never touches. Its absence in the ajax layout comes
from the ajax frame simply not rendering it — not from gating.

**`default` is the absence of a layer.** The default layout formally *is*
the shipped registrations on the package browser layer
(`IPlonePageletlayoutLayer`); no layout layer, no registry entry, and the
`plone:pagelayout` directive rejects the name. A theme changing the site
default is the existing shadow-on-your-theme-layer move — no new concept.

**The layout registry** maps names to layers (and optional static view
markers). Its concrete form: `IPageLayout` **named utilities** — utility
name = layout name; fields `name`, `layer`, `view_marker` (may be `None`).
`getUtilitiesFor(IPageLayout)` enumerates all registered layouts — this
feeds the unknown-name rule, tests, and any future UI.

## 2. Vocabulary (locked)

| Thing | Spelling |
|---|---|
| Query param | `pagelet_layout` |
| Alias param (stock compatibility) | `ajax_load` (truthy per `plone.base.utils.is_truthy`) |
| Canonical layout names | `default` (reserved) · `fullscreen` · `ajax` |
| View property | `layout_name` (templates: `view/layout_name`; chrome/code: `self.view.layout_name`) |
| Layout body class | `pagelet-layout-<name>` (e.g. `pagelet-layout-ajax`) |
| Layer interfaces | `plone.pageletlayout.interfaces.IFullscreenLayoutLayer`, `…IAjaxLayoutLayer` |
| Registry utility interface | `plone.pageletlayout.interfaces.IPageLayout` |
| Declaration directive | `plone:pagelayout` |
| Ajax response headers | `X-Theme-Disabled: 1` + `X-Robots-Tag: noindex` (always, both spellings) |

## 3. Declaring a layout: `plone:pagelayout`

A new directive in the existing grammar
([directives.md](directives.md#namespace) namespace rules apply) registers
one registry entry:

```xml
<plone:pagelayout
    name="fullscreen"
    layer="plone.pageletlayout.interfaces.IFullscreenLayoutLayer"
    view_marker="plone.pageletlayout.interfaces.IFullScreenPagelet"
    />
```

| Attribute | Type | Required | Meaning |
|---|---|---|---|
| `name` | TextLine | yes | the layout name — registry key, param value, `layout_name` value, body-class suffix |
| `layer` | GlobalInterface | yes | the layout layer the subscriber applies |
| `view_marker` | GlobalInterface | no | static view marker that triggers this layout as a view's default (ajax has none) |

Layer interfaces are **hand-written Python** — variant stanzas reference
them by dotted path, so the directive *binds* an existing interface, never
mints one. Config-time validation (conflicts surface at startup, matching
the grammar's rule-1 discipline):

- `name` is not the reserved `default`;
- `layer` extends `IPlonePageletlayoutLayer` — the **specificity-dominance
  convention**: a layout layer more specific than the package browser layer
  guarantees its shadows beat every shipped registration (leftward adapter
  positions dominate; verified empirically);
- `view_marker` (when given) extends `IPagelet`.

A plain `<utility>` stanza was rejected: no validation, two artifacts per
layout, reads as plumbing.

**Static defaults stay `provides=`.** A pagelet declares its default layout
exactly as today — `provides="…IFullScreenPagelet"` on its `plone:pagelet`
stanza; the marker is a **trigger only** (section 4), never a registration
dimension for layout variants. `IFullScreenPagelet` survives as-is; the
shipped `folder_contents` stanza does not change. `layout="fullscreen"`
sugar on `plone:pagelet` was consciously rejected — it drags ZCML
action-ordering into the design for a one-attribute convenience, and can be
added compatibly later.

### The extension recipe (third party or later core)

Fully expressible with existing directives plus `plone:pagelayout`:

1. Write a layer: `class IPrintLayoutLayer(IPlonePageletlayoutLayer): …`
2. One `plone:pagelayout` stanza binding `name="print"` to it.
3. Shadow the page region on that layer (required minimum):
   `<plone:chromepagelet name="plone.pageletlayout.pagelayout" class="…" layer="…IPrintLayoutLayer" />`
4. Optionally shadow the frame (`plone:layout layer=`) and head providers.

The shipped ajax layout is exactly this recipe (frame shadow + region
shadow); no layout needs syntax beyond it.

## 4. Selecting a layout: the trigger chain

One post-traversal subscriber (`IPubAfterTraversal`; Plone precedent for
post-traversal request marking: `plone.app.theming`) applies **at most one**
layout layer via `alsoProvides(request, layer)`. `IPubAfterTraversal` is
effectively forced: the third trigger reads `request['PUBLISHED']`, which
exists only after traversal. Consequence, by design: the layout layer is
applied *after* view lookup, so a layout can never influence **which
pagelet class is published** — only the adapters resolved during rendering
(region, frame, head providers). A layout re-dresses the page; it never
swaps the view. Triggers, in order — the
first that fires wins, and trigger order *is* the layout precedence
(param > alias > static view marker > default):

1. **`pagelet_layout` param.**
   - Names a registered layout → apply its layer; **stop**.
   - Is the literal `default` → apply **no** layer; **stop**. This is the
     **escape hatch**: the default layout renders even on a
     statically-marked view (e.g. `folder_contents?pagelet_layout=default`).
   - Unknown name → log one **warning** on the dedicated logger
     `plone.pageletlayout.layouts` (the param is attacker-controlled, so an
     operator being spammed can silence exactly that logger), then **fall
     through** as if the param were absent (lenient:
     `?pagelet_layout=typo&ajax_load=1` still honors the ajax intent). No
     404, no error page: fall-back keeps the no-guard guarantee and
     collapses unknown values onto the default cache variant.
2. **`ajax_load` alias** — value truthy per `plone.base.utils.is_truthy`
   (`1`/`yes`/`on`/`true`…) → apply the ajax layer; **stop**. Explicit falsy
   (`ajax_load=0`) applies nothing and forces nothing — there is no
   auto-detection to override (section 8). Consulted only when
   `pagelet_layout` did not resolve; downstream code never sees `ajax_load`.
3. **Static view marker** — `request['PUBLISHED']` provides a registry
   entry's `view_marker` → apply that entry's layer; **stop**.
4. Nothing fired → no layer; the default layout renders.

Because static markers route through the layer too, **every layout variant
registers exactly once, on the layer** — "the layer is the layout" is
literally true. The empirically-verified specificity fact (in a
`(context, request, view)` lookup, a more-specific *layer* beats a
more-specific *view* marker) survives as a **backstop** for old-style
view-dimension shadows, not as the precedence mechanism.

## 5. Reading the resolved layout

**`layout_name`** — a lazy property on `PageletPage`: the applied layout
layer's registry name, else `"default"`. Pagelet templates use
`view/layout_name`; chrome pagelets and code use `self.view.layout_name`
(reachable everywhere by the composition rule). The alias vanishes at the
subscriber: an `ajax_load=1` request reports `ajax`. Consumers condition on
the layout name, never on raw params — this replaces classic's `ajax_load`
TAL variable (e.g. sharing.pt's back-link gate).

**The layout body class** — every frame stamps `pagelet-layout-<name>`
(resolved name, so the shared frame stamps `pagelet-layout-fullscreen` when
the fullscreen layer is applied) onto `<body>` alongside
`plone_layout.bodyClass(...)`. The CSS twin of `layout_name`; bare
`plone-layout` is taken by the grid container. Classic's literal
`ajax_load` body class is **not** mirrored (no identified consumer).

## 6. The shipped layouts

### `default`

The absence of a layer: shared frame (`templates/layout.pt` — full head,
toolbar, `.plone-layout` grid), whole-body managed region
(`ManagedLayoutRegionChromePagelet`). No registry entry.

### `fullscreen`

A full standalone page without chrome — the site's `<head>` plumbing and
toolbar, the page region body-only. Declaration:

```xml
<plone:pagelayout
    name="fullscreen"
    layer="plone.pageletlayout.interfaces.IFullscreenLayoutLayer"
    view_marker="plone.pageletlayout.interfaces.IFullScreenPagelet"
    />
```

Variant: the existing `BodyOnlyRegion` shadow of
`plone.pageletlayout.pagelayout`, **re-registered** from
`view="…IFullScreenPagelet"` to `layer="…IFullscreenLayoutLayer"` (the one
migration in this spec — section 10). Shared frame, untouched head. Any
view can request it (`?pagelet_layout=fullscreen`); `folder_contents` gets
it by default via its unchanged `provides=`.

### `ajax`

The bare layout serving fetch/modal consumers — what `ajax_load=1`
delivers. Declaration has no `view_marker` (no view defaults to ajax):

```xml
<plone:pagelayout
    name="ajax"
    layer="plone.pageletlayout.interfaces.IAjaxLayoutLayer"
    />
```

Two shadows on `IAjaxLayoutLayer`:

- **Frame shadow** — a dedicated `ajax.pt` registered via `plone:layout
  layer=` for the same view classes as the shipped shell (classic
  precedent: `ajax_main_template.pt` is a sibling template). Not six
  empty-provider overrides: the shared frame's literal viewport/generator
  lines could never be shadowed away, and the whole shape should read in
  one file.
- **Region shadow** — `AjaxRegion` (mold of `BodyOnlyRegion`) rendering a
  **fixed** element set: `statusmessages`, then `<article id="content">`
  wrapping `contentheader` + `body`. Fixed by construction — the element
  set is a consumer contract, not a site-configurable layout;
  `viewlets.xml` cannot reorder or hide it. No byline, no toolbar.

#### The fragment contract

The response is a **full HTML document** — never a true fragment — because
mockup's `parseBodyTag` hard-requires a literal `<body>…</body>` (throws
otherwise). Shape:

```html
<!DOCTYPE html>
<html lang="…">
<head><meta charset="utf-8" /></head>
<body class="… pagelet-layout-ajax" dir="…"
      data-base-url="…" data-view-url="…" …patterns-settings…>
  (statusmessages → .portalMessage)
  <article id="content">
    (contentheader → h1.documentFirstHeading + description)
    (body → <div id="content-core" class="element-body">view content</div>)
  </article>
</body>
</html>
```

Guarantees to consumers (what stock patterns extract):

- literal `<body>` with full attributes — bodyClass, `dir`, the
  `@@plone_patterns_settings` data attributes; the
  `data-base-url`/`data-view-url` pair is functionally required by
  pat-plone-modal's redirect detection;
- `.portalMessage` (statusmessages, outside `#content` so modals can
  prepend them);
- first `h1` = `h1.documentFirstHeading` (modal `titleSelector`);
- `#content` wrapping content header + body;
- `#content-core` — `BodyChromePagelet`'s wrapper, present in **every**
  layout (`pagelets/content.py`).

**`#content` is ajax-only.** Universal adoption was rejected: faithful
Barceloneta nesting would force a content-group element and break the flat
one-manager concept. Other layouts use per-view content ids
(`#content-listing`, …); only the ajax response guarantees `#content`.

**Head: charset only, ever.** No title, no head providers — fragments must
never re-trigger resource loading (the Clara single-bundle story). There is
no head-inflating variant (section 8).

**Response headers, always, on both spellings:** `X-Theme-Disabled: 1`
(the contract must not depend on theme cooperation — Barceloneta's
`notheme` rules key on the `ajax_load` spelling only, and `_UnthemedMixin`
is per-view opt-in) and `X-Robots-Tag: noindex` (section 9). Seat: set in
`AjaxRegion.update()` — layer-bound code that every ajax response renders,
mirroring `_UnthemedMixin`'s header precedent.

## 7. Caching and purging

**The URL (path + query) is the sole cache key; no `Vary`.** Verified in
`plone.app.caching`: the RAM page-cache key is
`SERVER_URL + PATH_INFO + "?" + QUERY_STRING` (+ ETag), so
`?pagelet_layout=` partitions the RAM cache and every URL-keyed proxy
naturally. No request header participates in layout selection (the
rejection of XHR auto-detection keeps this true), so the spec carries no
`Vary` language. `X-Theme-Disabled` is a *response* header (read by the
theming policy pre-transform) — inert for proxy cache keys.

**The alias's duplicate entry is accepted.** `?ajax_load=1` and
`?pagelet_layout=ajax` cache as two identical entries — bounded and
self-consistent; canonicalizing them (redirect or key rewrite) would break
the pure-subscriber-rewrite design.

**Ruleset mapping is unaffected**: `plone.app.caching` selects operations
by published view, so all layouts of a view share its ruleset
automatically.

**Purging — deployment note, no new machinery.** `plone.cachepurging`
sends PURGE for exact query-less URLs, so proxy-cached layout variants
survive a purge of the bare URL — stock Plone's existing query-variant
story (`?b_start=` has the same gap). Deployments that proxy-cache layout
variants need ban-by-path purge rules (ignore query string) or short
`s-maxage`. A registry-driven `IPurgePaths` adapter was rejected: precise
only for canonical spellings, blind to `ajax_load=1` on arbitrary query
strings — partial coverage bought with real machinery.

## 8. Access rules

**Layout selection is not a security boundary.** Any client may request
any registered layout of any page it can already view: the publishing
permission gates the page before layout resolution, and every pagelet
self-gates. Corollary: a view whose static default is fullscreen for UX
reasons (`folder_contents`) may be requested with
`?pagelet_layout=default` — possibly ugly, by definition safe.
Permission-guarded layouts were rejected (they would turn silent fallback
into a security mechanism).

**Normative rule for layout authors**: a layout may remove, replace, or
rearrange chrome, but must never disclose content the default layout would
not render for the same principal. Authorization lives in views and
pagelets, never in layout selection.

## 9. Robots / SEO

- **Full-head layouts** (`fullscreen`, future ones): the head pagelet
  already wraps `plone.app.layout`'s `CanonicalURL` viewlet (query-free
  `absolute_url`), so layout-variant URLs dedupe onto the bare URL for
  free. Canonical is the signal; `noindex` deliberately not applied.
- **Ajax**: charset-only head has no canonical link, so the noindex rides
  as the `X-Robots-Tag: noindex` response header — covering both the
  canonical spelling and the alias.

## 10. Handoff to implementation

### Migration notes (existing registrations)

- `folder_contents`' `provides="…IFullScreenPagelet"` — **unchanged**.
- The `BodyOnlyRegion` shadow of `plone.pageletlayout.pagelayout` moves
  from `view="…IFullScreenPagelet"` to `layer="…IFullscreenLayoutLayer"`.
- Everything else is **additive**: two layer interfaces, the `IPageLayout`
  interface + directive (meta.zcml), the subscriber, two `plone:pagelayout`
  stanzas, `ajax.pt` + its `plone:layout` stanza, `AjaxRegion` + its
  stanza, `layout_name` on `PageletPage`, the body-class stamp in frames.
- Third-party view-dimension shadows keep working (specificity backstop);
  the layer dimension is the documented form.

### Upgrade steps

**None.** No persistent state changes: the registry is ZCML utilities,
layers are request markers, the ajax region is fixed by construction (no
`viewlets.xml` entries), and no GenericSetup profile content changes.

### Test-plan sketch

- **Trigger chain**: param beats alias beats static marker beats default;
  `?pagelet_layout=default` escape hatch on `folder_contents`;
  unknown name falls through to alias then static marker (logged warning);
  `ajax_load=0` applies nothing; both params present → `pagelet_layout`
  wins; unknown `pagelet_layout` + `ajax_load=1` → ajax.
- **At most one layer** per request; `layout_name` reports the resolved
  name (`ajax` for alias requests, `default` when nothing fired).
- **Registry**: `getUtilitiesFor(IPageLayout)` enumerates `fullscreen` +
  `ajax`; directive validation rejects `name="default"`, a layer not
  extending `IPlonePageletlayoutLayer`, a `view_marker` not extending
  `IPagelet`.
- **Fragment contract** (functional, rendered output): doctype + `<html
  lang>`; charset-only head; body data attributes present; element order
  statusmessages → `#content` → (`h1.documentFirstHeading`,
  `#content-core`); no toolbar markup; both response headers on both
  spellings; `pagelet-layout-ajax` body class.
- **Fullscreen**: region body-only, full head intact, toolbar present;
  works via param on an unmarked view and via marker on
  `folder_contents`.
- **Backstop**: a view-dimension region shadow still wins over the shipped
  base registration (existing
  `test_directives.py::TestChromePageletViewDimension` keeps passing).

### Consciously diverged from classic Plone

| Classic | Here | Why |
|---|---|---|
| `ajax_include_head=1` re-inflates the head | **dropped** | no stock sender; one fixed ajax shape (cache purity); the need it served *is* `?pagelet_layout=fullscreen` |
| optional `X-Requested-With` auto-detection | **not reproduced** | off by default in stock, unreliable per upstream; pat-search proves the param suffices; keeps URL-only cache keys true |
| literal `ajax_load` body class | **not mirrored** | no identified consumer; `pagelet-layout-<name>` is the generic hook |
| `ajax_load` TAL variable | `view/layout_name` | one flag for all layouts, alias-free |
| Diazo `notheme` cooperation | `X-Theme-Disabled: 1` unconditional | contract must not depend on theme cooperation |

## Provenance

Decided across the wayfinder effort `request-layouts`
(`.scratch/request-layouts/map.md`, tickets 01–05): the stock `ajax_load`
contract research, the resolution mechanism, the declaration grammar, the
ajax fragment contract, and caching/access — grilled with Maik between
2026-07-19 and 2026-07-21.
