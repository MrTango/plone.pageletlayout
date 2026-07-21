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

**Whole-body manager**:
The one ordered viewlet manager holding every visible page element, body
included; order and visibility are storage-managed.
_Avoid_: the layout (unqualified), layout manager

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
`#content`/`#content-core`. `#content` exists only in the ajax layout;
`#content-core` is the body element's wrapper in every layout.
_Avoid_: ajax API, markup contract (unqualified)

**Layout body class**:
The body class every frame stamps with the resolved layout name — the CSS
twin of `layout_name`, spelled `pagelet-layout-<name>` (e.g.
`pagelet-layout-ajax`); bare `plone-layout` is taken by the grid container.
_Avoid_: mode class
