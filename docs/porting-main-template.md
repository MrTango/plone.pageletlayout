# Porting a main_template page to a pagelet

You are probably here because of a log line like:

```
.../browser/templates/my_page.pt renders through the deprecated
main_template macro path, kept working by the plone.pageletlayout
compatibility bridge. Build new pages with plone:pagelet and port this
one — see docs/porting-main-template.md in plone.pageletlayout.
```

When `plone.pageletlayout`'s layer is active, the classic `main_template`
view is shadowed by a **compatibility bridge**: its `master` (and nested
`content`) macro renders the pagelet frame, so an unported page keeps
working and already gets pagelet chrome — the same elements a pagelet page
renders, in the order and visibility `IViewletSettingsStorage` holds, the
contentheader excepted (the classic contract emits title and description
inside the content article through slots a consumer may fill, so the frame
keeps that one inline and hiding or reordering it changes nothing on a
bridged page). The bridge is permanent — nothing breaks, ever — but the
METAL macro path it preserves is a dead end: it is not documented, new
features (named layouts, the ajax fragment contract) target pagelets, and in
development mode every macro-path render logs the warning above. Porting is
one registration and one template edit.

## The model, in one paragraph

A **pagelet** brings only its *body*: the content template. The frame
around it — `<head>` plumbing, toolbar, logo, navigation, footer — is the
site's **layout template**, looked up and rendered for you when the
pagelet is published. So where a classic page *pulls the frame in* (binds
the master macro and fills its slots), a pagelet only ships the markup it
used to put *into* the slots. The full grammar is
[directives.md](directives.md).

## Before

```xml
<browser:page
    name="my-report"
    for="*"
    class=".report.ReportView"
    template="report.pt"
    permission="zope2.View"
    />
```

```xml
<html metal:use-macro="context/@@main_template/macros/master">
  <body>
    <metal:block fill-slot="content-core">
      <ul>
        <li tal:repeat="row view/rows" tal:content="row" />
      </ul>
    </metal:block>
  </body>
</html>
```

## After

```xml
<plone:pagelet
    name="my-report"
    for="*"
    class=".report.ReportPagelet"
    template="report.pt"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    permission="zope2.View"
    />
```

```xml
<ul xmlns:tal="http://xml.zope.org/namespaces/tal">
  <li tal:repeat="row view/rows" tal:content="row" />
</ul>
```

The template keeps **only what stood inside the slots** — the macro
wrapper, the `fill-slot` scaffolding, and everything the frame provides
disappear. The class gains a layout frame by subclassing one of the
shipped `Layout*` pagelets (adapter registrations for a class cover its
subclasses):

```python
from plone.pageletlayout.pagelets.layout import LayoutDocumentPagelet


class ReportPagelet(LayoutDocumentPagelet):
    @property
    def rows(self):
        ...
```

— or, if you want your own frame, register one for your class with a
standalone `plone:layout` stanza (see
[directives.md](directives.md#plonetemplate-and-plonelayout)).

## Where each slot goes

| Classic slot | Pagelet equivalent |
|---|---|
| `main`, `body`, `content` | your content template *is* the body — no slot to fill |
| `content-core` | the content template's markup |
| `content-title`, `content-description` | render your own `<h1>`/lead inside the template (the shipped content pages use the `context/@@title` / `context/@@description` pattern) |
| `global_statusmessage` | nothing to do — the frame's status-message chrome renders them |
| `top_slot` request tweaks (`disable_border`, column switches) | obsolete — the pagelet frame has no columns or border to disable |
| `style_slot`, `javascript_head_slot` | page-specific resources belong in a resource-registry bundle, enabled per request with `Products.CMFPlone.resources.add_bundle_on_request` from your `update()` |
| `head_slot` *(non-resource markup)* | a `<link rel=…>` or `<meta>` is chrome, not a resource: shadow a head element on your view — see below |

### Head markup for one page

Everything in the frame's `<head>` is a chrome pagelet, so a page that needs
its own head markup adds it the same way the frame's own elements are
composed: register a subclass of the head element you are extending for
your view, so it wins by adapter specificity for that page only.

```python
@implementer(IMyReportPage)          # a marker your pagelet implements
class ReportPagelet(...):
    ...


class ReportHeadLinks(HeadLinksChromePagelet):
    def render(self):
        return super().render() + '<link rel="alternate" href="…" />'
```

```xml
<plone:chromepagelet
    name="plone.pageletlayout.headlinks"
    class=".report.ReportHeadLinks"
    view=".interfaces.IMyReportPage"
    layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
    />
```

The shipped worked example is `@@search` (`pagelets/search.py`), whose
classic `head_slot` advertised the feed for the current query. Note the
ajax layout renders no head providers at all, so a fragment response stays
charset-only for free.

## Modal consumers

If your page is opened by `pat-plone-modal` — a CMF action with a `modal`
property, or a menu entry with `class="pat-plone-modal"` — note that the
modal is **not** an ajax consumer. It fetches the link's plain `href` (of
the shipped patterns only search and manageportlets append `ajax_load`)
and then, out of that ordinary full-page response:

| Modal option | What it takes |
|---|---|
| `content: "#content"` | the modal body |
| `titleSelector: "h1:first"` | the modal title — and **removes** it from the body |
| `prependContent: ".portalMessage"` | lifted above the body |
| `buttons: ".formControls > input[type=submit], .formControls > button"` | cloned into the button bar |

So a converted page keeps its modal working by keeping its `<h1>` and its
`.formControls` in the body template. `#content` you get for free: the
framed body element emits it in every layout (`pagelets/framed.py`).
Nothing here requires a fragment — the ajax layout is for `fetch`-style
consumers, and asking for it is a *different* URL, not what a modal link
produces.

An **unported** modal page is fine too: the bridge frame emits the same
`<article id="content">`, so a page still on the macro path keeps its modal
working (of CMFPlone's five modal actions — contact, delete, rename, login,
join — `join`/`@@register` is the one still riding the bridge). The gap is
narrower than the bridge: a **wrapped** z3c.form (the seam below) renders
its form body without an `#content` wrapper, so an add-on that opens a
`wrap_form` page in a modal is the one case that needs
`FormBodyChromePagelet` (`pagelets/forms.py`) to grow the id — no shipped
action does.

## Porting a viewlet

The same log, a different line:

```
Viewlet acme.banner (acme.theme.viewlets.BannerViewlet) renders through the
stock viewlet manager plone.abovecontentbody, bridged into the whole-body
pagelet layout by plone.pageletlayout. Register it into
plone.pageletlayout.pagelets.layout.ILayoutManager instead, so it becomes a
layout element an integrator can order and hide — see
docs/porting-main-template.md in plone.pageletlayout.
```

Plone's stock viewlet managers — `IPortalHeader`, `IAboveContentBody`,
`IBelowContentBody`, `IPortalFooter`, … — are **bridged** into the layout
(`pagelets/managers.py`): each is rendered by one layout element, so a
viewlet registered into any of them still reaches the page, in its classic
position. Nothing breaks, and there is no hurry.

But a bridged viewlet is a passenger. The layout's own elements live in one
ordered manager whose order and visibility an integrator edits in
`@@manage-layout-viewlets` — a bridged viewlet is invisible there: it can
only be moved *within* its stock manager, and the whole bridge is hidden or
shown as one block. Promoting it is one line, because
`plone.pageletlayout.layout` is a stock `OrderedViewletManager` and
`PageletViewlet` is only the wrapper *we* use for our own chrome pagelets —
any plain viewlet registers into it directly:

```xml
<browser:viewlet
    name="acme.banner"
    class=".viewlets.BannerViewlet"
    manager="plone.pageletlayout.pagelets.layout.ILayoutManager"
    layer="acme.theme.interfaces.IAcmeThemeLayer"
    permission="zope2.View"
    />
```

The signal is not only about your code. It fires for **every** viewlet on a
bridge, Plone's own included (`plone.lockinfo`, `plone.relateditems`,
`plone.footer`, …) — those you cannot port and are not expected to; read past
them to the lines naming your own package. Production logs one line per
viewlet per process; development mode logs every render.

Three more things and you are done:

1. **Hide the old registration** in your own profile's `viewlets.xml`, or the
   viewlet renders twice — once through the bridge, once as an element:

   ```xml
   <hidden manager="plone.abovecontentbody" skinname="Plone Default">
     <viewlet name="acme.banner" />
   </hidden>
   ```

2. **Give it a position** in the new manager's order — also `viewlets.xml`,
   in the same file:

   ```xml
   <order manager="plone.pageletlayout.layout" skinname="Plone Default">
     <viewlet name="acme.banner" insert-before="plone.pageletlayout.body" />
   </order>
   ```

   `insert-before` / `insert-after` place one entry without restating the
   whole order, so your add-on does not fight the base profile (or another
   add-on) over the rest of the page.

3. **Add an upgrade step** for those profile changes, as for any GenericSetup
   XML change, so installed sites get them.

No pagelet conversion is required: your viewlet class and template are
unchanged. Converting it to a `plone:chromepagelet` afterwards is an optional
refinement (it buys the pagelet templating story — computation in `update()`,
markup from the `IContentTemplate` adapter — and nothing else).

### Viewlets that are not bridged

Four managers are deliberately *not* bridged, because this package
reimplements them rather than rendering them: `plone.htmlhead`,
`plone.htmlhead.links`, `plone.scripts` and `plone.httpheaders`. The frame's
`<head>` is composed of chrome pagelets that wrap the individual renderers
(`pagelets/head.py`), so a viewlet you register into one of those managers
does *not* appear — and, because it never renders, nothing logs a warning
either. `tests/orphan_viewlets_allowlist.txt` is the checked-in list of every
such viewlet; a new one fails the build rather than disappearing quietly. For
your own head markup, shadow a head element on your view instead — see
[Head markup for one page](#head-markup-for-one-page) above.

### Stock viewlets this package replaces

Nine stock viewlets duplicate elements the layout ships, so
`profiles/default/viewlets.xml` hides them: `plone.logo`, `plone.anontools`,
`plone.searchbox` (`IPortalHeader`), `plone.global_sections`
(`IMainNavigation`), `plone.path_bar` (`IAboveContent`), `plone.socialtags`
(`IAboveContentTitle`), `plone.documentbyline` (`IBelowContentTitle`),
`plone.colophon` and `plone.site_actions` (`IPortalFooter`). It is
configuration, not code: unhide any of them and hide the corresponding
element if you prefer the stock one.

One duplication the profile cannot resolve: `plone.footer` renders the footer
**portlet** manager, and Plone's default assignments there are a colophon and
a site-actions portlet — the same two things the layout's `colophon` and
`siteactions` elements render. Portlet assignments are site data, not
viewlets, so a `viewlets.xml` cannot touch them. Remove the two default
assignments, or hide the two elements; a theme that drives its footer from
blocks or portlets alone will want one or the other.

## What you do not port

**Wrapped z3c.forms** — anything rendered through
`plone.z3cform.layout.FormWrapper` (Dexterity `@@edit`, `++add++`,
`layout.wrap_form(...)`, registry control panels): their outer shell is
resolved by the form-layout machinery, not by your code. Leave them alone;
the machinery is converted centrally. If the deprecation warning names a
generic wrapper template (`layout.pt`, `controlpanel_layout.pt`) rather
than one of your templates, it is reporting that central path — not a page
you need to act on.
