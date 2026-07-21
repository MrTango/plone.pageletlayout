# The directive grammar

`plone.pageletlayout` ships five ZCML directives — the vocabulary a developer
uses to register pagelet-based pages and their chrome:

| Directive | Registers | Traversed? |
|---|---|---|
| `plone:pagelet` | a published page (class and/or template), plus its content template in one stroke | yes — this is the URL-visible view |
| `plone:chromepagelet` | a named `IContentProvider` (a chrome element), plus its content template in one stroke | no — rendered via `provider:<name>` |
| `plone:template` | a standalone `IContentTemplate` adapter | — |
| `plone:layout` | a standalone `ILayoutTemplate` adapter | — |
| `plone:pagelayout` | a layout-registry entry (`IPageLayout` named utility) binding a layout name to its layout layer | no — selected via `?pagelet_layout=<name>` |

All examples in this document are lifted from the package's own ZCML
(`pagelets/layout.zcml`, `pagelets/chrome.zcml`) — the package is registered
entirely through its own grammar.

## The model

A **pagelet** is a browser view that brings only its *body*: `update()`
computes, and `render()` fills the **content template** — the
`IContentTemplate` adapter registered for the class. Calling the pagelet
(`__call__`, i.e. publishing it) additionally looks up the **layout
template** — the `ILayoutTemplate` adapter — and renders the body inside that
frame. The frame is shared and owned by the site; the body travels with the
pagelet. That asymmetry is deliberate and shows up in the grammar: a pagelet
stanza may declare its content template inline (`template=`), but never its
layout — see [rule 3](#3-inline-template-registers-the-content-template-only).

A **chrome pagelet** is the same renderable — `update()` plus content
template — registered as a *named content provider* instead of a traversable
page: a multi-adapter on `(context, request, view)` that layout and body
templates pull in with `provider:<name>`. It has no layout lookup of its own
(chrome inside chrome can never recurse into frame-in-frame) and no
permission (see [rule 4](#4-permission-appears-on-plonepagelet-only-and-is-required-there)).

## Namespace

The directives live in the shared Plone namespace,
`http://namespaces.plone.org/plone` (`xmlns:plone`). Sharing that URI across
packages is the ecosystem convention — `plone:behavior` (plone.behavior),
`plone:static` (plone.resource), `plone:service` (plone.rest),
`plone:portlet` (plone.app.portlets) all do the same; no Plone package ships
its own namespace URI. ZCML collisions are per directive *name*, and none of
the five names is taken. The namespace names the project; the directive name
carries the domain.

## `plone:pagelet`

Register a published, layouted page.

```xml
<plone:pagelet
    name="pagelet_view"
    class=".layout.LayoutDocumentPagelet"
    template="templates/document.pt"
    for="plone.app.contenttypes.interfaces.IDocument"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    permission="zope2.View"
    />
```

| Attribute | Type | Required | Meaning |
|---|---|---|---|
| `name` | TextLine | yes | the view name the pagelet is traversed under |
| `class` | GlobalObject | no¹ | pagelet class; mixed with `PageletPage` on registration |
| `template` | Path | no¹ | content template, registered for the class in the same stroke |
| `permission` | Permission | **yes** | traversal permission, enforced by AccessControl like `browser:page` |
| `for` | Tokens | no | one or more context interfaces/classes (default: `Interface`) |
| `layer` | GlobalInterface | no | browser layer (exactly one) |
| `provides` | GlobalInterface | no | interface the view provides; must inherit `IPagelet` |
| *(anything else)* | — | no | arbitrary keyword arguments become attributes on the registered class (z3c.pagelet's contract, kept) |

¹ At least one of `class` / `template`; both allowed. With `template=` and no
class the directive synthesizes the class (**template-only pagelet**) on
`PageletPage` — never on plain `object`, so the page contract (response
headers, the post-render Diazo bypass) still applies:

```xml
<plone:chromepagelet
    name="plone.pageletlayout.colophon"
    template="templates/colophon.pt"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    />
```

(That one is a chrome pagelet, synthesized on `ChromePagelet`;
`plone:pagelet` synthesizes the same way on `PageletPage`.)

The security story is the reason this directive exists at all: z3c.pagelet's
own `z3c:pagelet` wires its `permission` with zope.security checkers, which
the Zope 2 publisher never consults — in Plone the permission is **silently
ignored**. `plone:pagelet` keeps z3c.pagelet's registration semantics but
applies AccessControl the way `browser:page` does (`protectClass` +
`protectName` + `InitializeClass`).

## `plone:chromepagelet`

Register one chrome element — a named `IContentProvider` on
`(context, request, view)` — and its content template, in one stroke.

```xml
<plone:chromepagelet
    name="plone.pageletlayout.searchbox"
    class=".header.SearchboxChromePagelet"
    template="templates/searchbox.pt"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    />
```

| Attribute | Type | Required | Meaning |
|---|---|---|---|
| `name` | TextLine | yes | the name the `provider:` expression looks up |
| `class` | GlobalObject | no¹ | chrome pagelet class; mixed with `ChromePagelet` if it does not already subclass it |
| `template` | Path | no¹ | content template, registered for the class in the same stroke |
| `for` | Tokens | no | one or more context interfaces/classes |
| `layer` | GlobalInterface | no | browser layer (exactly one) |
| `view` | GlobalInterface | no | which *published views* this part is available on (exactly one; default `IBrowserView` = all) |

¹ At least one of `class` / `template`, both allowed — same rule as
`plone:pagelet`.

There is deliberately **no `permission` attribute**: a provider adapter is
never traversed by ZPublisher, so nothing would enforce one — accepting and
ignoring it would recreate z3c:pagelet's silent security hole as API.
Conditional visibility belongs in `update()`/`render()` (return `""`), or in
the `view` dimension (below).

**What `view=` means — and what it does not.** `for`/`layer`/`view` name the
three positions of the provider's adapter tuple: content object, request
layer, *hosting view*. On a published pagelet page the hosting view is the
published pagelet itself — the TAL variable `view` inside the layout template
is that pagelet (the layout template is *bound to* it, and is itself never an
adapter dimension). So `view=ISomeMarker` means "this part is available on
published views providing `ISomeMarker`" — it restricts **where the part
appears**. It does **not** mean "which layout template the part renders in";
no attribute anywhere in the grammar selects a layout from a pagelet or
chrome stanza. See [the full-screen recipe](#recipe-a-full-screen-view) for
the `view=` dimension doing real work.

## `plone:template` and `plone:layout`

Standalone template registration: an `IContentTemplate` (`plone:template`) or
`ILayoutTemplate` (`plone:layout`) adapter on `(for, layer)`. These are
deliberate cognates of `z3c:template`/`z3c:layout` — same schema semantics,
so knowledge transfers one-to-one — with two differences: the factory renders
through Zope's own (Five/Chameleon) template engine, so `provider:` and
friends work; and `for` takes Tokens like the rest of the grammar.

Inline `template=` on the pagelet directives covers the common case, but the
standalone forms stay public because three cases still need them: **layout
templates** (there is no inline `layout=` — rule 3), **per-layer overrides**
of a template that belongs to an existing class, and **templates shared
across classes**. The package's own shell is the canonical example — one
`plone:layout` stanza serving all eleven published pagelet classes:

```xml
<plone:layout
    template="templates/layout.pt"
    for=".layout.LayoutDocumentPagelet
         .layout.LayoutNewsItemPagelet
         .layout.LayoutEventPagelet
         .layout.LayoutFilePagelet
         .layout.LayoutImagePagelet
         .layout.LayoutLinkPagelet
         .layout.LayoutListingPagelet
         .layout.LayoutSummaryPagelet
         .layout.LayoutTabularPagelet
         .layout.LayoutFullPagelet
         .layout.LayoutAlbumPagelet"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    />
```

| Attribute | Type | Required | Meaning |
|---|---|---|---|
| `template` | Path | yes | the page template file |
| `for` | Tokens | no | what the adapter is registered for — usually a *view class* (a registration for a class covers its subclasses) |
| `name` | TextLine | no | named template |
| `layer` | GlobalInterface | no | browser layer (exactly one) |
| `contentType` | TextLine | no | default `text/html` |
| `macro` | TextLine | no | render one macro of the template |
| `context` | GlobalObject | no | additionally discriminate on the context |

Note the `for` caveat: on these two directives `for` is usually a **view
class**, not a context interface — the template is an adapter on
`(view, request)`. The doc-wide rule "one or more interfaces or classes the
adapter is registered for" reads correctly for all four adapter directives;
"context interface" would not.

## `plone:pagelayout`

Declare a named page layout: one layout-registry entry — an `IPageLayout`
named utility, utility name = layout name. The directive *binds* a
hand-written layout layer, it never mints one; the full model (trigger
chain, shipped layouts, caching) is
[request-layouts.md](request-layouts.md).

```xml
<plone:pagelayout
    name="fullscreen"
    layer="plone.pageletlayout.interfaces.IFullscreenLayoutLayer"
    view_marker="plone.pageletlayout.interfaces.IFullScreenPagelet"
    />
```

(The shipped `fullscreen` declaration per the locked spec; it lands
together with the trigger chain.)

| Attribute | Type | Required | Meaning |
|---|---|---|---|
| `name` | TextLine | yes | the layout name — registry key, `pagelet_layout` param value, `layout_name` value, body-class suffix |
| `layer` | GlobalInterface | yes | the layout layer the trigger chain applies |
| `view_marker` | GlobalInterface | no | static view marker that triggers this layout as a view's default |

Mistakes surface at ZCML load, never at request time: the reserved name
`default` (the default layout is the absence of a layout layer), a `layer`
not extending `IPlonePageletlayoutLayer`, and a `view_marker` not
extending `IPagelet` are each configuration errors; two stanzas claiming
the same layout name conflict at startup.

One asymmetry to note: this is the grammar's only non-adapter directive,
so its `layer=` is not a lookup dimension ([rule
5](#5-for--layer--view-name-adapter-dimensions)) but the registered datum
itself — the request marker the trigger chain applies.

## The attribute grammar

Five rules, no exceptions among the adapter-registering directives
(`plone:pagelayout` registers a named utility and carries no adapter
dimensions — see its section). Every future directive addition conforms
to them.

### 1. `for` is one-or-many everywhere; `view` and `layer` are exactly-one

`for` accepts whitespace-separated interfaces (ZCML Tokens) in **every**
directive. One stanza, N registrations:

```xml
<plone:pagelet
    name="listing_view"
    class=".layout.LayoutListingPagelet"
    template="templates/listing.pt"
    for="plone.app.contenttypes.interfaces.IFolder
         plone.app.contenttypes.behaviors.collection.ISyndicatableCollection
         plone.base.interfaces.IPloneSiteRoot"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    permission="zope2.View"
    />
```

Two things this **is not**:

- It is not a multi-adapter of arity N+1. The stanza expands to N
  *independent* registrations — the pagelet above is looked up as an ordinary
  `(context, request)` adapter on Folders, on Collections, and on the site
  root separately. (gocept.pagelet's original action registered one adapter
  with the whole tuple as required, which made multi-`for` stanzas
  unlookupable as a page; ours re-derives the idea, not the bug.)
- It is not exempt from conflict detection. Each interface gets its own
  configuration-action discriminator, so a second stanza claiming the same
  name for *one* of the interfaces on the same layer **conflicts** at startup
  instead of silently overriding. Conversely, the `browser:page` rule is
  kept: the same name registered for *disjoint* interfaces coexists.

`view` and `layer` stay singular, per `browser:viewlet` precedent — widening
them later is compatible; narrowing would not be.

### 2. `class` is optional wherever `template` can stand in

At least one of the two, both allowed. Template-only registrations
synthesize the class on the directive's base (`PageletPage` /
`ChromePagelet`) — never plain `object` — so the rendering contract holds.

When do you need a class? The package's own registrations answer it
empirically — of its thirty pagelet-family stanzas exactly two are
template-only (the content header and the Powered-by-Plone colophon, both
static markup). **A class earns its place by computing, gating, or
composing; a template alone earns it by being static.**

- *compute*: `update()` prepares data the template renders (logo, searchbox,
  breadcrumbs, copyright…)
- *gate*: `render()` decides visibility (anontools, siteactions, byline)
- *compose*: the class mixes behavior or parameterizes a wrapped renderer
  (the `Layout*` pagelets, the head-plumbing wrappers) — such classes are
  never "empty shells" even when their bodies are

### 3. Inline `template=` registers the content template only

Both pagelet directives accept `template=`; the file is registered as the
class's `IContentTemplate` adapter through exactly the same machinery as a
standalone `plone:template` stanza. Two consequences worth knowing:

- The template binds to the **user's class** when one is given, so any
  further subclass — including a second registration of the same class under
  another name — inherits it.
- There is **no inline `layout=`** on either directive, deliberately. The
  layout is not the pagelet's to declare: it is one shared frame, owned by
  the site or theme, registered standalone with `plone:layout`. The
  asymmetry teaches the model — pagelets bring their body; the frame is
  provided for them. The inline attribute is named `template`, never
  `layout`.

### 4. `permission` appears on `plone:pagelet` only — and is required there

`plone:pagelet` registers the only ZPublisher-traversed thing in the
grammar, so it is the only place enforcement exists (the AccessControl
bridge), and there the attribute is mandatory. The other four directives
**refuse** the attribute rather than accept-and-ignore it — z3c:pagelet's
silently-ignored permission is the cautionary tale.

### 5. `for` / `layer` / `view` name adapter dimensions

Context, browser layer, hosting view — nothing else. In particular `view=`
restricts which published views a chrome part is available on
([see above](#plonechromepagelet)); no attribute selects a layout template.

## Composing pages

Two sanctioned patterns cover pages assembled from parts. (There is
deliberately no third — see the prior-art note below.)

**Explicit composition** — when the page owns its parts. A template-only (or
ordinary) pagelet whose template pulls each part in with a `provider:`
expression, every part a `plone:chromepagelet`. This is how the package's
own shell works: `templates/layout.pt` renders
`provider:plone.pageletlayout.pagelayout` (and the head-plumbing providers)
— one stanza per part, explicit order, plain markup between parts.

**Pluggable composition** — when a page must accept parts from packages that
don't own it. Use the stock viewlet machinery: a `browser:viewletManager`
plus `browser:viewlet` stanzas whose class is `PageletViewlet`
(`plone.pageletlayout.pagelets.layout`), the logic-free wrapper that mounts
any named chrome pagelet into any manager via a `pagelet="..."` attribute:

```xml
<browser:viewlet
    name="plone.pageletlayout.logo"
    pagelet="plone.pageletlayout.logo"
    class="plone.pageletlayout.pagelets.layout.PageletViewlet"
    manager="plone.pageletlayout.pagelets.layout.ILayoutManager"
    permission="zope2.View"
    />
```

You keep the full viewlet-manager toolbox — storage-managed order and
visibility (`IViewletSettingsStorage`, `viewlets.xml`,
`@@manage-layout-viewlets`) — without the package shipping a second assembly
mechanism. The package's whole-body layout is thirteen such stanzas over one
stock `OrderedViewletManager`.

**A trap when writing chrome templates:** a `provider:` expression inside a
*chrome pagelet's own* template hands the nested provider the chrome pagelet
as its hosting view — not the published pagelet. Compose from the published
pagelet's templates (content or layout), or look nested providers up in code
with `self.view`, the way `ManagedLayoutRegionChromePagelet` does.

**Why there is no `viewletpage` directive.** gocept.pagelet ships a complex
directive that registers a pagelet whose body is a viewlet manager, viewlets
declared as inline subdirectives. Considered and rejected here: it fixes the
composition in ZCML at startup (no storage-managed order/visibility — a step
*backwards* from the requirement it resembles), its one global manager
interface lets viewlets bleed across pages, and its ceremony-saving is
superseded by this grammar's own features — with template-only pagelets and
inline `template=`, an explicit composed page is one stanza and one `.pt`.

## Recipe: a full-screen view

Some views want the content region to themselves — `folder_contents` is the
motivating case: a pattern-driven management UI that needs the site's
`<head>` plumbing and the toolbar, but no logo, navigation, breadcrumbs or
footer. The `view=` dimension does this with two stanzas and no changes to
the shipped layout.

**The package now ships this recipe**: `folder_contents` itself is published
as a full-screen pagelet (`FolderContentsPagelet` in `pagelets/content.py`,
`LayoutFolderContentsPagelet` + `BodyOnlyRegion` in `pagelets/layout.py`,
wired in `pagelets/layout.zcml`). Because the marker
(`plone.pageletlayout.interfaces.IFullScreenPagelet`) and the body-only
region shadow are registered once, in-package, a consumer needs only the
*first* stanza below — a `plone:pagelet` with
`provides="plone.pageletlayout.interfaces.IFullScreenPagelet"` — to get a
full-screen page. The walkthrough keeps both stanzas to show the whole
mechanism (and how to build a different region variant of your own).

The shipped page region is a single provider point: `layout.pt` renders
`provider:plone.pageletlayout.pagelayout`, registered for `view=IBrowserView`
(all published views). The recipe: mark your full-screen pagelet with a
marker interface via `provides=`, then shadow the region provider for
exactly that marker.

```python
from plone.pageletlayout.chrome import ChromePagelet
from z3c.pagelet.interfaces import IPagelet
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider


class IFullScreenPagelet(IPagelet):
    """Published views that take the page region for themselves."""


class BodyOnlyRegion(ChromePagelet):
    """The page region on full-screen views: just the body element."""

    def render(self):
        provider = getMultiAdapter(
            (self.context, self.request, self.view),
            IContentProvider,
            name="plone.pageletlayout.body",
        )
        provider.update()
        return provider.render()
```

```xml
<!-- An ordinary pagelet that additionally provides the marker. -->
<plone:pagelet
    name="folder_contents"
    class=".contents.FolderContentsPagelet"
    template="templates/folder_contents.pt"
    provides=".interfaces.IFullScreenPagelet"
    for="plone.app.contenttypes.interfaces.IFolder"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    permission="cmf.ListFolderContents"
    />

<!-- On views providing the marker, the page region is body-only. -->
<plone:chromepagelet
    name="plone.pageletlayout.pagelayout"
    class=".contents.BodyOnlyRegion"
    view=".interfaces.IFullScreenPagelet"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    />
```

Why this works, mechanically:

- `provides=` puts the marker on the *published view* — the third position
  of every chrome lookup on that page.
- Registering the **same provider name** with `view=IFullScreenPagelet`
  doesn't conflict with the shipped stanza (the `view` dimension is part of
  the registration's identity) and doesn't remove anything: adapter
  specificity picks the marker registration on full-screen views and the
  shipped one everywhere else.
- Because the name always resolves, `layout.pt` needs **no guard** — this
  matters, since a `provider:` expression whose lookup fails raises
  `ContentProviderLookupError` at render time. Shadow the provider; never
  try to make its registration disappear.
- `BodyOnlyRegion` is a class, not a template, because of the nested-view
  trap above: it must look the body provider up with `self.view` (the
  published pagelet), exactly as the shipped
  `ManagedLayoutRegionChromePagelet` looks up the managed manager.

The mechanics are pinned by
`tests/test_directives.py::TestChromePageletViewDimension`.

(Your pagelet class still needs a layout frame like any other: subclass one
of the shipped `Layout*` pagelets — adapter registrations for a class cover
its subclasses — or register the shell for your class with `plone:layout`.)

## Prior art

The `plone:pagelet` ergonomics — optional `class`, inline `template=`,
multi-interface `for` — are modeled on **gocept.pagelet** (gocept / Zeit
Online), which pioneered `browser:page`-like ergonomics for z3c.pagelet
registration. The ideas were re-derived for this package, not ported:
gocept's handler builds on zope.security checkers, exactly the machinery
these directives exist to replace with AccessControl, and its multi-`for`
registration and `viewletpage` directive were re-examined rather than
copied (see above). No code was taken and the package does not depend on
gocept.pagelet; the debt is conceptual, and gladly acknowledged.
