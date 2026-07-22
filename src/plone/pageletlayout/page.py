"""Publishable pagelet page base (wayfinder ticket 07, per ticket 04).

Two jobs main_template used to own move into the published object itself:

* the response headers the ``plone.httpheaders`` provider set (that viewlet
  renders no markup — it's not chrome, so it gets no provider entrypoint),
* the Diazo bypass: the pagelet layout reproduces the *themed* Barceloneta
  markup directly, so the theme transform must not run over it again.
"""

from functools import cached_property

from z3c.pagelet.browser import BrowserPagelet
from zope.component import getUtilitiesFor
from zope.component import getUtility

from plone.pageletlayout.interfaces import IPageLayout
from plone.registry.interfaces import IRegistry


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
        for name, entry in sorted(getUtilitiesFor(IPageLayout)):
            if entry.layer.providedBy(self.request):
                return name
        return "default"

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
