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


class IFullscreenLayoutLayer(IPlonePageletlayoutLayer):
    """The ``fullscreen`` layout layer: a full standalone page without
    chrome — the site's ``<head>`` plumbing and toolbar stay, the page
    region is body-only (``BodyOnlyRegion`` shadows the region provider on
    this layer). Applied by the trigger chain via ``?pagelet_layout=
    fullscreen`` or the ``IFullScreenPagelet`` static view marker; bound to
    its name by the ``plone:pagelayout`` stanza in layouts.zcml."""


class IFullScreenPagelet(IPagelet):
    """Static view marker: published pagelets whose *default* layout is
    ``fullscreen``.

    Put on a published view via a ``plone:pagelet`` stanza's ``provides=``.
    A trigger only: the trigger chain (layouts.py) sees the marker on the
    published view and applies ``IFullscreenLayoutLayer`` — all fullscreen
    variants register on that layer, and ``?pagelet_layout=default`` is the
    escape hatch back to the default layout. The full recipe:
    docs/directives.md, "Recipe: a full-screen view"."""
