"""Head chrome pagelets (wayfinder ticket 07, per the ticket-04 recipe).

Invisible head plumbing is *wrapped*, never forked: the resource-registry
renderers and meta/link viewlets are instantiated directly — they are
self-sufficient given (context, request, view). This does not touch the
clean-reimplementation decision, which covers visible chrome; the one
visible-ish element here, the browser-tab title, IS reimplemented clean.
"""

import os.path
from html import escape

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.resources.browser.resource import ScriptsView
from Products.CMFPlone.resources.browser.resource import StylesView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility

import plone.app.layout.viewlets
from plone.app.layout.links.viewlets import CanonicalURL
from plone.app.layout.links.viewlets import FaviconViewlet
from plone.app.layout.links.viewlets import RSSViewlet
from plone.app.layout.links.viewlets import SearchViewlet
from plone.app.layout.viewlets.common import DublinCoreViewlet
from plone.app.layout.viewlets.social import SocialTagsViewlet
from plone.base.interfaces import IPloneSiteRoot
from plone.base.interfaces import ISiteSchema
from plone.base.navigationroot import get_navigation_root_object
from plone.base.utils import safe_text
from plone.pageletlayout.chrome import ChromePagelet
from plone.registry.interfaces import IRegistry


class HtmlTitleChromePagelet(ChromePagelet):
    """The <title>, reimplemented clean (~TitleViewlet's job, no
    plone.app.layout): page title + navigation-root/site title; the site
    root gets the site title alone. Portal-factory handling dropped —
    dead weight in the pagelet stack."""

    sep = " &mdash; "

    def update(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        site_title = safe_text(settings.site_title)
        if IPloneSiteRoot.providedBy(self.context):
            self.title_text = site_title
            return
        portal = getToolByName(self.context, "portal_url").getPortalObject()
        nav_root = get_navigation_root_object(self.context, portal)
        if IPloneSiteRoot.providedBy(nav_root):
            portal_title = site_title
        else:
            portal_title = escape(safe_text(nav_root.Title()))
        page_title = escape(safe_text(self.context.Title()))
        if page_title == portal_title:
            self.title_text = portal_title
        else:
            self.title_text = self.sep.join((page_title, portal_title))

    def render(self):
        return f"<title>{self.title_text}</title>"


class WrappedRenderersChromePagelet(ChromePagelet):
    """Base for the plumbing wrappers: instantiate each existing renderer
    with the identical (context, request, view) triple, update, concatenate
    the renders."""

    factories = ()

    def render(self):
        parts = []
        for factory in self.factories:
            renderer = factory(self.context, self.request, self.view)
            # browser:viewlet stamps __name__ onto its synthesized class;
            # instantiated directly it is None — but cache keys (e.g.
            # SearchViewlet's ram.cache) require a string.
            renderer.__name__ = factory.__name__
            renderer.update()
            parts.append(renderer.render())
        return "\n".join(parts)


#: plone.app.layout ships SocialTagsViewlet's head template alongside the
#: viewlet class; the head-meta wrapper below binds it explicitly (see below).
_LAYOUT_VIEWLETS_DIR = os.path.dirname(plone.app.layout.viewlets.__file__)


class _SocialTagsHead(SocialTagsViewlet):
    """SocialTagsViewlet's head facet: its ``<meta>`` tags, NOT a ``<title>``.

    SocialTagsViewlet subclasses TitleViewlet and carries no ``index`` of its
    own — the stock head registration supplies ``social_tags.pt`` (a bare
    ``<meta>`` repeat). Instantiated directly here (the head plumbing wraps
    renderers, no ZCML), it would fall back to TitleViewlet's ``title.pt`` and
    emit a *second* ``<title>`` — which Diazo used to dedupe against
    ``htmltitle`` but the un-themed render exposes (ticket 20 decision 5).
    Rebinding ``index`` to the stock head template restores the registered
    behavior: meta tags only, ``htmltitle`` owns the single ``<title>``."""

    index = ViewPageTemplateFile(
        os.path.join(_LAYOUT_VIEWLETS_DIR, "social_tags.pt")
    )


class HeadMetaChromePagelet(WrappedRenderersChromePagelet):
    """plone.htmlhead's meta viewlets (title excluded — reimplemented)."""

    factories = (DublinCoreViewlet, _SocialTagsHead)


class HeadLinksChromePagelet(WrappedRenderersChromePagelet):
    """plone.htmlhead.links minus the styles (separate pagelet) and minus
    plone.links.author (login-gated) / plone.nextprevious.links
    (folder-setting-gated) — both empty on the stock acceptance pages."""

    factories = (FaviconViewlet, SearchViewlet, RSSViewlet, CanonicalURL)


class StylesChromePagelet(WrappedRenderersChromePagelet):
    """All CSS bundles — including Barceloneta's theme production-css,
    which only renders while the theme still counts as enabled (the
    ticket-04 trap; see PageletPage.__call__)."""

    factories = (StylesView,)


class ScriptsChromePagelet(WrappedRenderersChromePagelet):
    """All JS bundles. Shares one per-request webresource cache with the
    styles pagelet — rendering both costs one computation."""

    factories = (ScriptsView,)
