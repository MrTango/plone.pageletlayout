"""Publishable pagelet page base (wayfinder ticket 07, per ticket 04).

Two jobs main_template used to own move into the published object itself:

* the response headers the ``plone.httpheaders`` provider set (that viewlet
  renders no markup — it's not chrome, so it gets no provider entrypoint),
* the Diazo bypass: the pagelet layout reproduces the *themed* Barceloneta
  markup directly, so the theme transform must not run over it again.
"""

from functools import cached_property

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.pagelet.browser import BrowserPagelet
from z3c.template.interfaces import ILayoutTemplate
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.interface import implementer

from plone.pageletlayout.interfaces import IFramedPage
from plone.pageletlayout.interfaces import IPageLayout
from plone.registry.interfaces import IRegistry


def resolve_layout_name(request):
    """The applied layout layer's registry name, else ``"default"``.

    The request-side half of ``PageletPage.layout_name``, callable without
    a pagelet — the main_template bridge stamps the same body class for
    classic consumers, whose views know nothing of layouts.
    """
    for name, entry in sorted(getUtilitiesFor(IPageLayout)):
        if entry.layer.providedBy(request):
            return name
    return "default"


class PageletPage(BrowserPagelet):
    """Base for every published (layouted) pagelet.

    ``plone:pagelet`` mixes this in for each registration, the way
    ``z3c:pagelet`` mixes in BrowserPagelet — pagelet classes don't need
    to subclass it themselves.
    """

    @cached_property
    def layout_name(self):
        """The applied layout layer's registry name, else ``"default"``.

        Templates: ``view/layout_name``; chrome pagelets and code:
        ``self.view.layout_name`` (reachable everywhere by the composition
        rule). Alias-free: an ``ajax_load=1`` request reports ``ajax`` —
        consumers condition on the layout name, never on raw params
        (docs/request-layouts.md, section 5).
        """
        return resolve_layout_name(self.request)

    def __call__(self):
        self._set_http_headers()
        result = super().__call__()
        # Disable Diazo strictly AFTER update()/render(): the theme must
        # still count as enabled while StylesView renders, or Barceloneta's
        # production-css (not a registry bundle!) drops out of the head —
        # isThemeEnabled() checks this very response header. The transform
        # itself only consults the header after the body is produced.
        self.request.response.setHeader("X-Theme-Disabled", "1")
        return result

    def _set_http_headers(self):
        # HTTPCachingHeaders' three headers, reimplemented (trivial).
        lang = getattr(self.context, "Language", None)
        if callable(lang):
            lang = lang()
        if not lang:
            registry = getUtility(IRegistry)
            lang = registry.get("plone.default_language", "en")
        setHeader = self.request.response.setHeader
        setHeader("Content-Type", "text/html;charset=utf-8")
        setHeader("Expires", "Sat, 1 Jan 2000 00:00:00 GMT")
        setHeader("Content-Language", lang)


class BoundFramedTemplate:
    """What a ``FramedTemplate`` resolves to on a view instance.

    Callable *and* still a template, mirroring Five's ``BoundPageTemplate``
    — which is exactly what the stock attribute resolved to before the swap.
    Calling it renders the whole framed page (the mechanism's point);
    ``macros`` are the *body* template's, never the frame's, because a stock
    view that reaches into ``self.<template>.macros`` is building a fragment
    out of part of its own page. ``@@sharing``'s ``updateSharingInfo`` is
    the shipped consumer (pagelets/sharing.py).
    """

    def __init__(self, framed, view):
        self.framed = framed
        self.view = view

    def __call__(self, **options):
        return self.framed.render_framed(self.view, options)

    @property
    def macros(self):
        return self.framed.body.macros


class FramedTemplate:
    """A template attribute whose render is the whole framed page.

    Drop-in for a classic view's class-bound templates — ``index`` (what
    ``browser:page``'s ``template=`` becomes) or a multi-template dispatch
    set like PasswordResetView's ``form``/``invalid``/``expired``/
    ``finish``. The stock control flow keeps running verbatim; where it
    used to render the classic macro template, calling a FramedTemplate
    renders the pagelet frame (the ILayoutTemplate registered for the view
    class, so named layouts and the ajax fragment contract apply) with the
    wrapped body-only template as the page body — delivered through the
    framed body element, see ``IFramedPage``.

    Owns PageletPage.__call__'s two header jobs (response headers before,
    Diazo bypass strictly after render), which that ``__call__`` never
    performs for a framed page: the stock flow is in charge, not
    BrowserPagelet's.
    """

    def __init__(self, filename, _prefix=None):
        self.body = ViewPageTemplateFile(filename, _prefix)

    def __get__(self, view, cls=None):
        if view is None:
            return self
        return BoundFramedTemplate(self, view)

    def render_framed(self, view, options):
        view._set_http_headers()
        view._pagelet_body = self.body
        view._pagelet_body_options = options
        layout = getMultiAdapter((view, view.request), ILayoutTemplate)
        result = layout(view)
        view.request.response.setHeader("X-Theme-Disabled", "1")
        return result


@implementer(IFramedPage)
class FramedPage(PageletPage):
    """Base for converting a classic self-rendering page to a pagelet.

    Subclass the stock view class FIRST (``class LoginPagelet(LoginForm,
    FramedPage)``) so its ``__call__``/``render`` keep driving, and swap
    each class-bound template for a ``FramedTemplate``. Views without any
    ``__call__`` of their own (template-only pages) fall through to the
    one below: render the bound ``index``, exactly what Five's page class
    would have done.
    """

    _pagelet_body = None
    _pagelet_body_options = None

    def __call__(self):
        return self.index()

    def render_body(self):
        """Render the bound body template — the framed body element's
        content (FramedBodyChromePagelet, pagelets/framed.py)."""
        return self._pagelet_body(self, **self._pagelet_body_options)
