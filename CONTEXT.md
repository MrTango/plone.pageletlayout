# plone.pageletlayout

The pagelet-based page composition machinery for Plone: published pagelets,
their chrome, and the frame they render in. This glossary is the ubiquitous
language; docs, specs, and code prose use these terms and no synonyms.

## Language

### Rendering model

**Pagelet**:
A published browser view that brings only its body; publishing it renders that
body inside the frame.
_Avoid_: page, view (when the pagelet contract is meant)

**Chrome pagelet**:
The same renderable as a pagelet, registered as a named content provider
instead of a traversable page.
_Avoid_: viewlet (that word names the stock Zope mechanism only)

**Frame**:
The shared, site-owned template a published pagelet's body renders inside —
one frame for all pagelets, never declared by a pagelet itself.
_Avoid_: layout, layout template (in prose), shell

**Page region**:
The single provider slot inside the frame where the page's visible composition
renders; every page layout must provide it.
_Avoid_: content area, main slot

### The stock viewlet stack

**Slot**:
A stock viewlet manager the page region renders in a fixed, semantic place —
`plone.portaltop`, `plone.portalheader` and `plone.mainnavigation` in the
header, the content managers in `article#content`, `plone.portalfooter` in the
footer. Order and visibility inside a slot are storage-managed.
_Avoid_: region (that names the frame's provider slot), position

**Element pool**:
`ILayoutManager`, the viewlet manager interface every layout element is
registered for. No manager provides it and nothing renders it directly.
_Avoid_: whole-body manager (the retired flat manager), layout manager

**Layout element** (short form "element"):
A named chrome pagelet, registered for the element pool through a
`PageletViewlet` wrapper, so a slot can render, order and hide it. The body
and the status messages are fixed parts of the frame, not elements. The
content header is an element (first in `plone.abovecontentbody` by default),
except on the main_template bridge, which prints it inline around the classic
title and description slots.
_Avoid_: part, region

**Slot assignment**:
The registry record `plone.pageletlayout.slot_assignments`, mapping each
layout element to the slot it renders in. Changing it takes effect on the
next request, without a restart.
_Avoid_: placement, manager mapping

**Orphan viewlet**:
A viewlet whose manager no slot renders — it disappears from a pagelet page
with no exception and no log line. The set is pinned by the viewlet ratchet
(`tests/orphan_viewlets_allowlist.txt`) and can only shrink.
_Avoid_: missing viewlet, dropped viewlet

**Deprecation signal**:
The log line a compatibility path emits naming what rode it and how to leave
it — one per macro-path consumer. Logging, never `DeprecationWarning`: Zope's
filters swallow those and dedupe per code location.
_Avoid_: deprecation warning (that names the Python mechanism this is not)

### Request-time layout selection

**Page layout** (short form "layout" where unambiguous):
A named, request-selectable presentation of the whole page, defined by its
layout layer and the registrations shadowed on it. Shipped names: `default`,
`fullscreen`, `ajax`.
_Avoid_: mode, display mode, view mode

**Layout name**:
The string key of a page layout — what the request carries, what views read,
what the layout registry maps.
_Avoid_: layout id, mode name

**Layout layer**:
The request-marker interface expressing one page layout on a request.
_Avoid_: request marker (unqualified), browser layer (that names the general
Zope mechanism)

**Layout registry**:
The mapping between layout names, layout layers, and static view markers that
request marking and layout reporting both consult. Realized as `IPageLayout`
named utilities; enumerable via `getUtilitiesFor`.
_Avoid_: layout map, layout vocabulary

**Layout declaration**:
The `plone:pagelayout` ZCML stanza binding a layout name to its layer (and
optional static view marker) as one registry entry, with configuration-time
validation. The reserved name `default` cannot be declared — it names the
absence of a layer.
_Avoid_: layout registration (that describes the variants, not the binding)

**Trigger chain**:
The subscriber's ordered request check — known `pagelet_layout` name, then
the `ajax_load` alias, then the static view marker — applying at most one
layout layer per request. Precedence between layouts is the trigger order;
`?pagelet_layout=default` matches no trigger and forces the default layout.
_Avoid_: precedence rules (unqualified), resolution order

**Static view marker**:
The interface a pagelet registration `provides=` to declare its default page
layout (e.g. `IFullScreenPagelet`). A trigger for the chain only — never a
registration dimension for layout variants.
_Avoid_: view interface (unqualified), fullscreen marker (when the general
concept is meant)

**Ajax layout**:
The bare page layout serving fetch/modal consumers: a full HTML document with
a charset-only head, no toolbar, theming disabled, and a fixed element set
(status messages, then `#content` wrapping content header and body). Selected
by name or via the `ajax_load` alias.
_Avoid_: fragment (its response is a full document by contract), ajax mode

**Fragment contract**:
What the ajax layout's response guarantees its consumers: literal `<body>`
with patterns-settings data attributes, `.portalMessage`, first `h1`,
`#content`/`#content-core`. `#content` is the content article of the default
and ajax layouts; `#content-core` is the body element's wrapper in every
layout.
_Avoid_: ajax API, markup contract (unqualified)

**Layout body class**:
The body class every frame stamps with the resolved layout name — the CSS
twin of `layout_name`, spelled `pagelet-layout-<name>` (e.g.
`pagelet-layout-ajax`); bare `plone-layout` is taken by the grid container.
_Avoid_: mode class
