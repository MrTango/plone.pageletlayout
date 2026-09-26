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
slot layout's content article, in the default layout and on the bridge frame
alike, wrapped z3c.forms included. Nothing here requires a fragment — the
ajax layout is for `fetch`-style consumers, and asking for it is a
*different* URL, not what a modal link produces.

## Porting a viewlet

Nothing to port. The frame renders Plone's stock viewlet managers —
`IPortalHeader`, `IAboveContentBody`, `IBelowContentBody`, `IPortalFooter`, …
— in their classic places (`pagelets/templates/pagelayout.pt`), so a viewlet
registered into any of them renders exactly where it does on stock Plone.
Order and hide it per manager in `viewlets.xml` or
`@@manage-layout-viewlets`.

Register it as a **layout element** instead when an integrator should be able
to move it to another manager. Register it for the element pool, then assign
it a slot and a place in that slot's order:

```xml
<browser:viewlet
    name="acme.banner"
    class=".viewlets.BannerViewlet"
    manager="plone.pageletlayout.pagelets.layout.ILayoutManager"
    layer="acme.theme.interfaces.IAcmeThemeLayer"
    permission="zope2.View"
    />
```

```xml
<!-- registry.xml -->
<record name="plone.pageletlayout.slot_assignments">
  <value purge="false">
    <element key="acme.banner">plone.abovecontentbody</element>
  </value>
</record>

<!-- viewlets.xml -->
<order manager="plone.abovecontentbody" skinname="Plone Default">
  <viewlet name="acme.banner" insert-before="*" />
</order>
```

`purge="false"` adds your entry without replacing the others. Add an upgrade
step for those profile changes, as for any GenericSetup XML change.

### Dual registration

An add-on that must keep working without this package keeps its stock
registration and adds the `ILayoutManager` one under the **same name**. When
both land in the same manager, the stock registration wins and the viewlet
renders once (plone.app.viewletmanager's `IAdditionalViewlets` rule). The two
registrations may wrap different classes; only the name has to match.

### Viewlets that do not render

Four managers are deliberately *not* slots, because this package
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
