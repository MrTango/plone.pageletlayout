"""The whole-body, one-manager pagelet layout.

Every visible element sits directly on ``<body>`` (the toolbar excepted — a
foreign subsystem that self-gates). ONE stock ``OrderedViewletManager`` named
``plone.pageletlayout.layout`` holds every element (body included) as the
same logic-free ``PageletViewlet`` wrapper. Order and visibility come from
``IViewletSettingsStorage`` (GS ``viewlets.xml``, ``@@manage-layout-viewlets``,
a future drag&drop UI), so the managed variant reorders/hides the *whole page*.

There is a single published variant: ``pagelet_view`` → the managed layout,
one provider name ``plone.pageletlayout.pagelayout`` resolving to the ordered
manager. ``ELEMENTS`` below stays the canonical top-to-bottom order; a parity
test pins ``viewlets.xml`` to it.

Lookups happen in code with ``self.view`` (the published pagelet) — a
``provider:`` expression inside a chrome pagelet's own template would hand the
nested providers THIS pagelet as the view (the BodyChromePagelet lesson).
"""

from Products.Five.browser import BrowserView
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import implementer
from zope.viewlet.interfaces import IViewlet
from zope.viewlet.interfaces import IViewletManager

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


#: The whole-body ordered viewlet manager (registered in configure.zcml as a
#: stock OrderedViewletManager). Its default order lives in
#: profiles/default/viewlets.xml.
MANAGER_NAME = "plone.pageletlayout.layout"


class ILayoutManager(IViewletManager):
    """The single whole-body viewlet manager: every visible element, body
    included; the toolbar excepted. A stock ``OrderedViewletManager`` provides
    it — no subclass of ours."""


#: The visible elements in canonical top-to-bottom page order (toolbar
#: excepted — foreign subsystem). The managed variant's default order is this
#: same list, imported into IViewletSettingsStorage by
#: profiles/default/viewlets.xml; equality between the two is what the parity
#: test pins (test_layout.py).
#:
#: ``contentheader`` is title + description merged into one ``<header>`` — they
#: reorder/hide together.
ELEMENTS = (
    "plone.pageletlayout.logo",
    "plone.pageletlayout.anontools",
    "plone.pageletlayout.globalnav",
    "plone.pageletlayout.searchbox",
    "plone.pageletlayout.breadcrumbs",
    "plone.pageletlayout.statusmessages",
    "plone.pageletlayout.socialtags",
    "plone.pageletlayout.contentheader",
    "plone.pageletlayout.byline",
    "plone.pageletlayout.body",
    "plone.pageletlayout.copyright",
    "plone.pageletlayout.colophon",
    "plone.pageletlayout.siteactions",
)


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


class ManagedLayoutRegionChromePagelet(ChromePagelet):
    """Managed variant: delegate to the ordered whole-body manager — order and
    visibility come from IViewletSettingsStorage configuration."""

    def render(self):
        manager = getMultiAdapter(
            (self.context, self.request, self.view),
            IContentProvider,
            name=MANAGER_NAME,
        )
        manager.update()
        return manager.render()


class BodyOnlyRegion(ChromePagelet):
    """The page region on full-screen views (IFullScreenPagelet): just the
    body element — no logo, nav, breadcrumbs or footer; the ``<head>``
    plumbing and the toolbar stay with the shell. Registered under the same
    provider name with ``view=`` the marker, so adapter specificity picks it
    on full-screen views and the managed region everywhere else (the recipe
    in docs/directives.md). A class, not a template: the body provider must
    be looked up with ``self.view``, the published pagelet (the
    BodyChromePagelet lesson)."""

    def render(self):
        provider = getMultiAdapter(
            (self.context, self.request, self.view),
            IContentProvider,
            name="plone.pageletlayout.body",
        )
        provider.update()
        return provider.render()


class _UnthemedMixin:
    """Pre-render theme-off: disable the theme from the start so StylesView
    omits barceloneta.min.css (the theme production-css, not a registry
    bundle). Diazo already never runs; only the CSS changes."""

    def update(self):
        self.request.response.setHeader("X-Theme-Disabled", "1")
        super().update()


class LayoutDocumentPagelet(_UnthemedMixin, DocumentPagelet):
    """Document, whole-body layout (``pagelet_view``)."""


# The five remaining per-item types (wayfinder ticket 11), each the theme-off
# whole-body layout over its body-only content pagelet.
class LayoutNewsItemPagelet(_UnthemedMixin, NewsItemPagelet):
    """News Item, whole-body layout (``pagelet_view``)."""


class LayoutEventPagelet(_UnthemedMixin, EventPagelet):
    """Event, whole-body layout (``pagelet_view``)."""


class LayoutFilePagelet(_UnthemedMixin, FilePagelet):
    """File, whole-body layout (``pagelet_view``)."""


class LayoutImagePagelet(_UnthemedMixin, ImagePagelet):
    """Image, whole-body layout (``pagelet_view``)."""


class LayoutLinkPagelet(_UnthemedMixin, LinkPagelet):
    """Link, whole-body layout (``pagelet_view``)."""


# The shared folderish listing views (wayfinder ticket 12), each the theme-off
# whole-body layout over one listing format. Registered for Folder, Collection
# and the site root; the site-root listing (formerly its own SiteRootListingPagelet
# + siteroot_listing.pt) folds into this shared set.
class LayoutListingPagelet(_UnthemedMixin, ListingPagelet):
    """Folderish ``listing_view``, whole-body layout."""


class LayoutSummaryPagelet(_UnthemedMixin, SummaryPagelet):
    """Folderish ``summary_view``, whole-body layout."""


class LayoutTabularPagelet(_UnthemedMixin, TabularPagelet):
    """Folderish ``tabular_view``, whole-body layout."""


class LayoutFullPagelet(_UnthemedMixin, FullPagelet):
    """Folderish ``full_view``, whole-body layout."""


class LayoutAlbumPagelet(_UnthemedMixin, AlbumPagelet):
    """Folderish ``album_view``, whole-body layout."""


class LayoutFolderContentsPagelet(_UnthemedMixin, FolderContentsPagelet):
    """``folder_contents``, whole-body layout — published full-screen: the
    registration's ``provides=IFullScreenPagelet`` flips the page region to
    ``BodyOnlyRegion``."""
