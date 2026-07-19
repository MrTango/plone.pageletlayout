"""Content pagelets (wayfinder ticket 13, per the ticket-03 decisions).

Body-only: each pagelet renders the type's content-core equivalent and
nothing else — title/description are chrome pagelets in the layout, exactly
the seam classic ``document_view`` keeps (its template only fills the
content-core slot). One shared view name ``pagelet_view`` per type via
``for=``; the FTI flip lives in ``profiles/default/types/``.
"""

from z3c.pagelet.browser import BrowserPagelet
from z3c.pagelet.interfaces import IPagelet
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.contentprovider.interfaces import IContentProvider

from plone.app.content.browser.contents import FolderContentsView
from plone.app.content.utils import json_dumps
from plone.app.contenttypes.behaviors.collection import ISyndicatableCollection
from plone.app.contenttypes.browser.collection import CollectionView
from plone.app.contenttypes.browser.folder import FolderView
from plone.base.utils import human_readable_size
from plone.event.interfaces import IEventAccessor
from plone.pageletlayout.chrome import ChromePagelet


class DocumentPagelet(BrowserPagelet):
    """The Document content-core: the ``text`` field (with the
    table-of-contents class hook), like classic ``document.pt``."""

    def update(self):
        text = getattr(self.context, "text", None)
        self.body = text.output_relative_to(self.context) if text else None
        self.toc = bool(getattr(self.context, "table_of_contents", False))


class BodyChromePagelet(ChromePagelet):
    """The content hole as an element: owns the ``#content-core`` wrapper
    (main_template markup classically) around z3c.pagelet's stock
    ``pagelet`` provider, which renders the *published* pagelet's content
    template. Making the body a named chrome pagelet keeps the Phase-2
    name == pagelet convention exception-free.

    The stock provider is looked up in code, not via ``provider:`` in a
    template — a template's ``view`` would be THIS pagelet, and the stock
    renderer would recurse into our own content template."""

    def render(self):
        renderer = getMultiAdapter(
            (self.context, self.request, self.view),
            IContentProvider,
            name="pagelet",
        )
        renderer.update()
        return f'<div id="content-core" class="element-body">{renderer.render()}</div>'


# ---------------------------------------------------------------------------
# Per-item content pagelets (wayfinder ticket 11): the full views for the five
# remaining default types, body-only like Document. Each reuses Plone's OWN
# per-type hooks (ticket 02 audit of plone.app.contenttypes / plone.app.event)
# and DELEGATES to the stock view for helper logic rather than porting it
# (wrap, don't re-implement — [[feedback-reuse-over-reimplement]]).
# ---------------------------------------------------------------------------


class NewsItemPagelet(DocumentPagelet):
    """News Item core == the ``text`` field, identical to Document: stock
    ``newsitem.pt`` fills only content-core with the text (the lead image is a
    separate behavior viewlet — chrome, not core)."""


class EventPagelet(BrowserPagelet):
    """Event core: the schema.org wrapper + the stock ``@@event_summary`` view
    + the ``text`` field, mirroring ``plone.app.event``'s event content-core.
    Field access goes through the stock ``IEventAccessor`` (the same adapter the
    classic ``event_view`` uses); ``@@event_summary`` is rendered in the
    template."""

    def update(self):
        self.data = IEventAccessor(self.context)


class FilePagelet(BrowserPagelet):
    """File core: inline audio/video for media types, a download action for the
    rest, plus type/size metadata. The type predicates and human-readable size
    come from the stock ``@@file_view`` (``FileView``), reused via delegation."""

    def update(self):
        self.helper = getMultiAdapter((self.context, self.request), name="file_view")
        file = getattr(self.context, "file", None)
        self.file = file
        if file is not None:
            self.content_type = file.contentType
            self.filename = file.filename
            base_url = self.context.absolute_url()
            self.download_url = f"{base_url}/@@download/file/{self.filename}"


class ImagePagelet(BrowserPagelet):
    """Image core: the ``large`` scale (linking to the fullscreen view) +
    type/dimension/size metadata + download & fullscreen actions. The scale tag
    comes from the stock ``@@images`` view; the size is formatted with the same
    ``human_readable_size`` helper the classic view uses."""

    def update(self):
        image = getattr(self.context, "image", None)
        self.image = image
        if image is None:
            return
        self.content_type = image.contentType
        width, height = image.getImageSize()
        self.dimension = f"{width}x{height}"
        self.human_size = human_readable_size(image.getSize())
        self.filename = image.filename
        base_url = self.context.absolute_url()
        self.download_url = f"{base_url}/@@download/image/{self.filename}"
        self.fullscreen_url = f"{base_url}/image_view_fullscreen"
        scale = getMultiAdapter((self.context, self.request), name="images")
        self.image_tag = scale.tag("image", scale="large", css_class="figure-img")


class LinkPagelet(BrowserPagelet):
    """Link core: the (variable-substituted) target as a link, plus optional
    meta and the edit-only redirect notice. URL resolution, the display dict
    and the edit check are reused from the stock ``@@link_redirect_view``."""

    def update(self):
        self.helper = getMultiAdapter((self.context, self.request), name="link_redirect_view")
        url = self.helper.url()
        self.display = self.helper.display_link()
        self.target_url = self.helper.absolute_target_url()
        self.is_external = url.startswith("http")
        self.is_mail = url.startswith("mailto")
        self.can_edit = self.helper.can_edit
        self.redirect_links = self.context.portal_registry["plone.redirect_links"]


# ---------------------------------------------------------------------------
# Folderish listing pagelets (wayfinder ticket 12): the shared listing/summary/
# tabular/full/album views for Folder + Collection + the site root, body-only
# like the per-item views. Each DELEGATES to Plone's own listing machinery
# (plone.app.contenttypes' FolderView / CollectionView) for the batch, thumb
# scales, tabular fields and album grouping rather than porting any of it
# (wrap, don't re-implement — [[feedback-reuse-over-reimplement]]); the clean
# body templates emit ticket-10's reused hooks (.entries / .item / .summary /
# .card / .table / .album) with the utility soup stripped. One view class per
# FORMAT (the plone:template binding is per class); the context type (Folder vs
# Collection vs site root) only picks which stock helper drives the data.
# ---------------------------------------------------------------------------


class FolderishListingPagelet(BrowserPagelet):
    """Shared base: expose the stock folder/collection listing view as
    ``view.helper`` so the body template reuses its ``batch()`` and helper
    methods verbatim. ``CollectionView`` (query results) is used for anything
    carrying the collection behavior; ``FolderView`` (folder contents, also the
    site root) for everything else — the same split ``plone.app.contenttypes``
    registers its own templates over."""

    def update(self):
        if ISyndicatableCollection.providedBy(self.context):
            self.helper = CollectionView(self.context, self.request)
        else:
            self.helper = FolderView(self.context, self.request)


class ListingPagelet(FolderishListingPagelet):
    """``listing_view`` — a single elastic column of item rows (``.entries`` >
    ``.item``)."""


class SummaryPagelet(FolderishListingPagelet):
    """``summary_view`` — item rows with description + read-more (``.entries`` >
    ``.summary``)."""


class TabularPagelet(FolderishListingPagelet):
    """``tabular_view`` — a ``.table`` of the configured tabular fields."""


class AlbumPagelet(FolderishListingPagelet):
    """``album_view`` — a flexbin-justified ``.entries.album`` grid of image and
    sub-folder ``.card`` / ``.card.album`` tiles."""


class FullPagelet(FolderishListingPagelet):
    """``full_view`` — each item's full body stacked. Reuses each item's OWN
    ticket-11 body pagelet (its ``pagelet_view`` content) rather than porting a
    per-type renderer; containers (folders/collections, which have no
    ``pagelet_view``) degrade to their title + description."""

    def update(self):
        super().update()
        self.full_entries = [
            {
                "title": item.Title() or item.getId(),
                "description": item.Description(),
                "url": self._item_url(item),
                "body": self._item_body(item.getObject()),
            }
            for item in self.helper.batch()
        ]

    def _item_url(self, item):
        url = item.getURL()
        if item.PortalType() in self.helper.use_view_action:
            url = f"{url}/view"
        return url

    def _item_body(self, obj):
        """Render ``obj``'s body-only content pagelet (the same body its own
        ``pagelet_view`` shows), or ``None`` when the type has no pagelet view
        (containers) or rendering fails — the caller shows title + description."""
        view = queryMultiAdapter((obj, self.request), IPagelet, name="pagelet_view")
        if view is None:
            return None
        try:
            view.update()
            provider = queryMultiAdapter(
                (obj, self.request, view), IContentProvider, name="pagelet"
            )
            if provider is None:
                return None
            provider.update()
            return provider.render()
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Management views: the pattern-driven screens that classically render through
# main_template. folder_contents is the first — a full-screen pagelet (the
# docs/directives.md recipe, shipped): body-only region, head plumbing and
# toolbar stay.
# ---------------------------------------------------------------------------


class FolderContentsPagelet(BrowserPagelet):
    """folder_contents core: the CSRF authenticator token + the
    ``pat-structure`` div that boots the management UI. The options JSON
    DELEGATES to the stock ``FolderContentsView`` — all the vocabulary /
    column / index / upload plumbing stays upstream (wrap, don't
    re-implement — [[feedback-reuse-over-reimplement]])."""

    def update(self):
        helper = FolderContentsView(self.context, self.request)
        self.options = json_dumps(helper.get_options())
