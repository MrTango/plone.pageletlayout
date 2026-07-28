"""Module where all interfaces, events and exceptions live."""

from z3c.pagelet.interfaces import IPagelet
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.schema import InterfaceField
from zope.schema import TextLine

from plone.app.z3cform.interfaces import IPloneFormLayer


class IPlonePageletlayoutLayer(IPloneFormLayer, IDefaultBrowserLayer):
    """Marker interface that defines a browser layer.

    Extends ``IPloneFormLayer`` deliberately: the S1 form-layout seam
    (pagelets/forms.py) registers the wrapped-form frame for
    ``(IFormWrapper, IPlonePageletlayoutLayer)``, which must beat
    plone.app.z3cform's ``(IFormWrapper, IPloneFormLayer)`` registration.
    Sibling browser layers tie-break on the request's marking order — an
    install-order accident per site; inheritance makes "more specific"
    true by construction. Every Plone 6 site has the form layer installed
    (plone.app.z3cform is core), so the subsumption never adds behavior a
    pageletlayout request didn't already have."""


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


class IAjaxLayoutLayer(IPlonePageletlayoutLayer):
    """The ``ajax`` layout layer: the bare fragment-contract document
    serving fetch/modal consumers — what stock ``ajax_load=1`` delivers.
    Charset-only head, no toolbar, the fixed ``AjaxRegion`` element set
    (docs/request-layouts.md, section 6). Request-only: no view defaults
    to ajax, so its ``plone:pagelayout`` stanza (layouts.zcml) has no
    view_marker; applied by the trigger chain via ``?pagelet_layout=ajax``
    or the ``ajax_load`` alias."""


class IFramedPage(IPagelet):
    """Published pagelets converted from classic self-rendering pages.

    The FramedPage mechanism (page.py): the stock view class keeps its
    control flow — ``__call__`` redirect checks, POST handling, multi-
    template dispatch — and only its class-bound templates are swapped for
    ``FramedTemplate``s, which render the pagelet frame with the wrapped
    body-only template as the page body. The marker is the ``view=``
    dimension the framed chrome shadows key on (pagelets/framed.zcml):
    the body element renders the bound body, the contentheader element is
    empty (a framed page's heading lives in its body template, per
    docs/porting-main-template.md)."""


class ISearchPagelet(IFramedPage):
    """The converted ``@@search`` (pagelets/search.py).

    A framed page like any other; the marker exists because search is the
    first converted page that needs markup of its own in the ``<head>`` —
    the classic template's ``head_slot``. It is the ``view=`` dimension a
    head element shadows on, the same specificity move the framed body and
    content header make one level up."""


class IFullScreenPagelet(IPagelet):
    """Static view marker: published pagelets whose *default* layout is
    ``fullscreen``.

    Put on a published view via a ``plone:pagelet`` stanza's ``provides=``.
    A trigger only: the trigger chain (layouts.py) sees the marker on the
    published view and applies ``IFullscreenLayoutLayer`` — all fullscreen
    variants register on that layer, and ``?pagelet_layout=default`` is the
    escape hatch back to the default layout. The full recipe:
    docs/directives.md, "Recipe: a full-screen view"."""
