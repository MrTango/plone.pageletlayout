"""Module where all interfaces, events and exceptions live."""

from z3c.pagelet.interfaces import IPagelet
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IPlonePageletlayoutLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IFullScreenPagelet(IPagelet):
    """Published pagelets that take the page region for themselves.

    Put on a published view via a ``plone:pagelet`` stanza's ``provides=``;
    a ``plone:chromepagelet`` stanza with ``view=`` this marker shadows the
    shipped ``plone.pageletlayout.pagelayout`` region provider with the
    body-only variant (``BodyOnlyRegion``) — the ``<head>`` plumbing and the
    toolbar stay, logo/nav/breadcrumbs/footer go. The full recipe:
    docs/directives.md, "Recipe: a full-screen view"."""
