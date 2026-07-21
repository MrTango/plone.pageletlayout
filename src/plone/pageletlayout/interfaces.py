"""Module where all interfaces, events and exceptions live."""

from z3c.pagelet.interfaces import IPagelet
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.schema import InterfaceField
from zope.schema import TextLine


class IPlonePageletlayoutLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IPageLayout(Interface):
    """One entry in the layout registry: a named page layout.

    Registered as a named utility (utility name = layout name) by the
    ``plone:pagelayout`` directive; ``getUtilitiesFor(IPageLayout)``
    enumerates every registered layout. The reserved name ``default`` is
    the absence of a layout layer and never has a registry entry.
    Normative model: docs/request-layouts.md, section 1.
    """

    name = TextLine(
        title="Layout name",
        description=(
            "Registry key, pagelet_layout param value, layout_name value, "
            "and body-class suffix — all four are this one spelling."
        ),
    )

    layer = InterfaceField(
        title="Layout layer",
        description=(
            "The hand-written request-marker interface the trigger chain "
            "applies; extends IPlonePageletlayoutLayer."
        ),
    )

    view_marker = InterfaceField(
        title="Static view marker",
        description=(
            "Marker (extending IPagelet) that triggers this layout as a "
            "published view's default; None when the layout is request-only."
        ),
        required=False,
    )


class IFullScreenPagelet(IPagelet):
    """Published pagelets that take the page region for themselves.

    Put on a published view via a ``plone:pagelet`` stanza's ``provides=``;
    a ``plone:chromepagelet`` stanza with ``view=`` this marker shadows the
    shipped ``plone.pageletlayout.pagelayout`` region provider with the
    body-only variant (``BodyOnlyRegion``) — the ``<head>`` plumbing and the
    toolbar stay, logo/nav/breadcrumbs/footer go. The full recipe:
    docs/directives.md, "Recipe: a full-screen view"."""
