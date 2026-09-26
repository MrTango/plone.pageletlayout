"""The slot layout: Plone's stock viewlet managers in their semantic places.

The page region nests the stock managers the way classic main_template does —
``<header>`` (portaltop, portalheader, mainnavigation), ``<main>`` (status
messages, abovecontent, ``article#content`` with the content header, body and
the content managers) and ``<footer>`` (portalfooter). The toolbar stays a
foreign subsystem outside the region.

Layout elements are ``PageletViewlet`` wrappers registered for the element
pool ``ILayoutManager``; a slot assignment (slots.py) decides which stock
manager renders each one. Order and visibility come from
``IViewletSettingsStorage`` per manager (GS ``viewlets.xml``,
``@@manage-layout-viewlets``).

Lookups happen in code with ``self.view`` (the published pagelet) — a
``provider:`` expression inside a chrome pagelet's own template would hand the
nested providers THIS pagelet as the view (the BodyChromePagelet lesson).
"""

from Products.Five.browser import BrowserView
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import implementer
from zope.viewlet.interfaces import IViewlet

from plone.pageletlayout.chrome import ChromePagelet
from plone.pageletlayout.pagelets.content import AlbumPagelet
from plone.pageletlayout.pagelets.content import DocumentPagelet
from plone.pageletlayout.pagelets.content import EventPagelet
from plone.pageletlayout.pagelets.content import FilePagelet
from plone.pageletlayout.pagelets.content import FolderContentsPagelet
from plone.pageletlayout.pagelets.content import FullPagelet
from plone.pageletlayout.pagelets.content import ImagePagelet
from plone.pageletlayout.pagelets.content import LinkPagelet
from plone.pageletlayout.pagelets.content import ListingPagelet
from plone.pageletlayout.pagelets.content import NewsItemPagelet
from plone.pageletlayout.pagelets.content import SummaryPagelet
from plone.pageletlayout.pagelets.content import TabularPagelet
from plone.pageletlayout.pagelets.slots import CONTENT_HEADER_SLOTS
from plone.pageletlayout.pagelets.slots import ILayoutManager  # noqa: F401
from plone.pageletlayout.pagelets.slots import SLOTS


@implementer(IViewlet)
class PageletViewlet(BrowserView):
    """Generic, logic-free wrapper: renders one named content provider.

    ``pagelet`` names the provider to wrap and is set *per registration*:
    stock ``browser:viewlet`` passes arbitrary attributes into the class dict
    (keyword_arguments), so one class serves every element —

        <browser:viewlet
            name="plone.pageletlayout.logo"
            pagelet="plone.pageletlayout.logo"
            class="plone.pageletlayout.pagelets.layout.PageletViewlet"
            manager="plone.pageletlayout.pagelets.layout.ILayoutManager"
            permission="zope2.View"
            />

    The wrapped pagelet is looked up on (context, request, view) — view being
    the published pagelet the manager was rendered with — the identical triple
    the layout's ``provider:`` expression hands a chrome pagelet.
    """

    pagelet = None  # the provider name; set by the ZCML registration

    def __init__(self, context, request, view, manager=None):
        super().__init__(context, request)
        self.__parent__ = view
        self.view = view
        self.manager = manager

    def update(self):
        self.provider = getMultiAdapter(
            (self.context, self.request, self.view),
            IContentProvider,
            name=self.pagelet,
        )
        self.provider.update()

    def render(self):
        return self.provider.render()


class SlotLayoutRegionChromePagelet(ChromePagelet):
    """The default page region: the stock managers nested in header, main
    and footer (templates/pagelayout.pt). Everything renders in update(),
    against the published pagelet, and only once — the status messages
    drain their queue on render."""

    def update(self):
        self.slots = {
            name.rsplit(".", 1)[-1]: render_provider(self, name)
            for name in SLOTS
            if name not in CONTENT_HEADER_SLOTS.values()
        }
        self.statusmessages = render_provider(self, "plone.pageletlayout.statusmessages")
        self.contentheader = render_provider(self, "plone.pageletlayout.contentheader")
        self.body = render_provider(self, "plone.pageletlayout.body")


def render_provider(region, name):
    """Update and render one named provider for ``region.view``, stripped so
    an empty manager is detectable (managers join viewlets with newlines)."""
    provider = getMultiAdapter(
        (region.context, region.request, region.view),
        IContentProvider,
        name=name,
    )
    provider.update()
    return provider.render().strip()


class BodyOnlyRegion(ChromePagelet):
    """The fullscreen layout's page region: just the body element — no
    logo, nav, breadcrumbs or footer; the ``<head>`` plumbing and the
    toolbar stay with the shell. Registered under the same provider name
    with ``layer=IFullscreenLayoutLayer``, so adapter specificity picks it
    whenever the trigger chain applied the fullscreen layer
    (``?pagelet_layout=fullscreen`` or the IFullScreenPagelet static
    marker) and the managed region everywhere else (the recipe in
    docs/directives.md)."""

    def render(self):
        return render_provider(self, "plone.pageletlayout.body")


class AjaxRegion(ChromePagelet):
    """The ajax layout's page region: the fragment contract's **fixed**
    element set — statusmessages, then ``<article id="content">`` wrapping
    contentheader + body (docs/request-layouts.md, section 6). Fixed by
    construction: the element set is a consumer contract (stock Mockup
    patterns extract ``.portalMessage``, the first ``h1`` and ``#content``),
    not a site-configurable layout — ``viewlets.xml`` cannot reorder or
    hide it. ``#content-core`` (the body element's wrapper) stays present
    in every layout; ``#content`` is emitted here and — since ticket 09,
    for the modal consumers that never ask for a fragment — by the framed
    body element in the other layouts (pagelets/framed.py)."""

    def update(self):
        # Both ajax response headers live here — layer-bound code every
        # ajax response renders, canonical spelling and alias alike.
        setHeader = self.request.response.setHeader
        # The contract must not depend on theme cooperation (Barceloneta's
        # notheme rules key on the ajax_load spelling only).
        setHeader("X-Theme-Disabled", "1")
        # The charset-only head has no canonical link, so the noindex
        # rides as a header (docs/request-layouts.md, section 9).
        setHeader("X-Robots-Tag", "noindex")

    def render(self):
        messages = render_provider(self, "plone.pageletlayout.statusmessages")
        header = render_provider(self, "plone.pageletlayout.contentheader")
        body = render_provider(self, "plone.pageletlayout.body")
        return f'{messages}<article id="content">{header}{body}</article>'


class _UnthemedMixin:
    """Pre-render theme-off: disable the theme from the start so StylesView
    omits barceloneta.min.css (the theme production-css, not a registry
    bundle). Diazo already never runs; only the CSS changes."""

    def update(self):
        self.request.response.setHeader("X-Theme-Disabled", "1")
        super().update()


class LayoutDocumentPagelet(_UnthemedMixin, DocumentPagelet):
    """Document, slot layout (``pagelet_view``)."""


# The five remaining per-item types (wayfinder ticket 11), each the theme-off
# slot layout over its body-only content pagelet.
class LayoutNewsItemPagelet(_UnthemedMixin, NewsItemPagelet):
    """News Item, slot layout (``pagelet_view``)."""


class LayoutEventPagelet(_UnthemedMixin, EventPagelet):
    """Event, slot layout (``pagelet_view``)."""


class LayoutFilePagelet(_UnthemedMixin, FilePagelet):
    """File, slot layout (``pagelet_view``)."""


class LayoutImagePagelet(_UnthemedMixin, ImagePagelet):
    """Image, slot layout (``pagelet_view``)."""


class LayoutLinkPagelet(_UnthemedMixin, LinkPagelet):
    """Link, slot layout (``pagelet_view``)."""


# The shared folderish listing views (wayfinder ticket 12), each the theme-off
# slot layout over one listing format. Registered for Folder, Collection
# and the site root; the site-root listing (formerly its own SiteRootListingPagelet
# + siteroot_listing.pt) folds into this shared set.
class LayoutListingPagelet(_UnthemedMixin, ListingPagelet):
    """Folderish ``listing_view``, slot layout."""


class LayoutSummaryPagelet(_UnthemedMixin, SummaryPagelet):
    """Folderish ``summary_view``, slot layout."""


class LayoutTabularPagelet(_UnthemedMixin, TabularPagelet):
    """Folderish ``tabular_view``, slot layout."""


class LayoutFullPagelet(_UnthemedMixin, FullPagelet):
    """Folderish ``full_view``, slot layout."""


class LayoutAlbumPagelet(_UnthemedMixin, AlbumPagelet):
    """Folderish ``album_view``, slot layout."""


class LayoutFolderContentsPagelet(_UnthemedMixin, FolderContentsPagelet):
    """``folder_contents``, slot layout — published full-screen: the
    registration's ``provides=IFullScreenPagelet`` flips the page region to
    ``BodyOnlyRegion``."""
