"""The main_template compatibility bridge.

A permanent, undocumented shim: the ``main_template`` view is overridden on
the pageletlayout layer with a pagelet-frame template exposing a compatible
``master`` macro (and the nested ``content`` macro the control-panel
``prefs_main_template`` chain binds), so every unconverted classic consumer
— add-ons included — renders pagelet chrome without being touched. Macros
keep *working* here but are never documented or recommended; everything new
is built on ``plone:pagelet``, and every macro-path render logs a
deprecation signal (``warn_macro_use``) pointing at
docs/porting-main-template.md.

Subclassing CMFPlone's MainTemplate keeps the whole classic contract for
free: ``__call__``, the ``macros`` property consumers bind via
``context/@@main_template/macros/master``, and the ajax_load switch to the
stock ajax_main_template. Only the full-frame template is ours.
"""

import logging

from App.config import getConfiguration
from Products.CMFPlone.browser.main_template import MainTemplate
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.contentprovider.interfaces import IContentProvider

from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.page import resolve_layout_name
from plone.pageletlayout.pagelets.layout import MANAGER_NAME


logger = logging.getLogger(__name__)

#: Consumers already logged in this process — the production rate limit
#: (once per consumer per process; development mode logs every render).
_warned_consumers = set()

PORTING_DOCS = "docs/porting-main-template.md in plone.pageletlayout"

#: The element the inline body region stands in for. The classic master
#: emits the content INSIDE it through METAL slots, so it is the frame's
#: fixed point: everything the storage orders before it renders above the
#: region, everything after it below.
BODY_ELEMENT = "plone.pageletlayout.body"

#: The one element the bridge cannot hand to the manager. The classic
#: contract puts title and description inside the content article, through
#: the ``content-title``/``content-description`` slots a consumer may fill
#: or suppress (blocks_view.pt leaves them alone on purpose, the control
#: panels replace them). Rendering the contentheader element as well would
#: print both — so the frame keeps emitting it inline, exactly as it did
#: before the chrome became storage-managed, and hiding or reordering it
#: has no effect on a bridged page. The only element that stays fixed.
INLINE_ELEMENTS = frozenset({"plone.pageletlayout.contentheader"})


class BridgedMainTemplate(MainTemplate):
    """MainTemplate with the pagelet frame as its full template."""

    main_template = ViewPageTemplateFile("templates/main_template.pt")

    @property
    def layout_name(self):
        """The applied layout's name, for the frame's body-class stamp —
        consumer views are plain BrowserViews without ``layout_name``, so
        the bridge template reaches it via ``context/@@main_template``."""
        return resolve_layout_name(self.request)

    def warn_macro_use(self, template=None):
        """The deprecation signal, called by the frame's master macro.

        ``template`` is the TAL ``template`` variable at macro-render
        time — the root template being rendered, i.e. the consumer that
        bound the macro (the same object classic main_template passes to
        ``plone_layout.bodyClass``), not the frame.
        """
        name = getattr(template, "filename", None) or repr(template)
        message = (
            f"{name} renders through the deprecated main_template macro "
            f"path, kept working by the plone.pageletlayout compatibility "
            f"bridge. Build new pages with plone:pagelet and port this "
            f"one — see {PORTING_DOCS}."
        )
        if getConfiguration().debug_mode:
            logger.warning(message)
        elif name not in _warned_consumers:
            _warned_consumers.add(name)
            logger.info(message)

    # -- the storage-managed chrome ------------------------------------------
    #
    # A bridged page renders the SAME element set as a pagelet page, from the
    # same IViewletSettingsStorage order: whatever an integrator reorders or
    # hides in @@manage-layout-viewlets, and whatever a theme adds to the
    # manager (viewlets.xml), reaches classic consumers too. The frame used to
    # call a template-fixed list of provider names instead, which silently
    # dropped every element the base package did not ship — a theme could add
    # one to the layout, see it on pagelet pages, and never on a bridged one.
    #
    # Only the *position* of the content stays template-fixed, because METAL
    # slots must sit inline in the body region and a provider's render is
    # opaque to slot filling: the manager's elements render around that region,
    # split at BODY_ELEMENT.

    #: The computed split, cached for the life of this view instance.
    _chrome_cache = None

    def _chrome(self, view):
        """The layout manager and its elements, split around the body region.

        Returns ``(manager, before, after, show_body)``. Cached per instance
        because ``update()`` has side effects — the status-messages element
        drains the message queue, so updating twice would swallow every
        message. The frame therefore binds ONE ``bridge`` variable and asks
        it for both slices and the body flag.

        ``view`` is the consumer's published view, the same object a pagelet
        page hands the manager: elements look their providers up on
        (context, request, view).
        """
        if self._chrome_cache is not None:
            return self._chrome_cache

        manager = getMultiAdapter(
            (self.context, self.request, view),
            IContentProvider,
            name=MANAGER_NAME,
        )
        manager.update()

        storage = getUtility(IViewletSettingsStorage)
        order = list(
            storage.getOrder(MANAGER_NAME, self.context.getCurrentSkinName())
        )
        # An element the storage does not name sorts after every named one —
        # the manager's own sort() appends the unknown ones at the end, and
        # the split has to agree with it or they would land above the body.
        unknown = len(order) + 1

        def position(name):
            try:
                return order.index(name)
            except ValueError:
                return unknown

        # Body missing from the order (an integrator removed it) puts every
        # named element above the region, which is what the manager renders.
        cut = position(BODY_ELEMENT)
        if cut == unknown:
            cut = len(order)

        # The body element never renders here — the inline region IS the body,
        # and letting the manager render it too would print the content twice.
        # Excluded by name, not by position: with the body missing from the
        # order it sorts as unknown, which would otherwise put it below.
        elements = [
            v
            for v in manager.viewlets
            if v.__name__ != BODY_ELEMENT and v.__name__ not in INLINE_ELEMENTS
        ]
        before = [v for v in elements if position(v.__name__) < cut]
        after = [v for v in elements if position(v.__name__) > cut]
        show_body = any(v.__name__ == BODY_ELEMENT for v in manager.viewlets)
        self._chrome_cache = (manager, before, after, show_body)
        return self._chrome_cache

    def chrome_before(self, view):
        """The elements the storage orders above the content."""
        manager, before, _after, _show_body = self._chrome(view)
        return self._render(manager, before)

    def chrome_after(self, view):
        """The elements the storage orders below the content."""
        manager, _before, after, _show_body = self._chrome(view)
        return self._render(manager, after)

    def show_body(self, view):
        """Is the body element visible? Hiding it in the storage blanks the
        content region here exactly as it blanks a pagelet page."""
        return self._chrome(view)[3]

    @staticmethod
    def _render(manager, elements):
        """Render one slice *through the manager*.

        Its ``render()`` carries the per-element error handling (one broken
        element logs and degrades to a marker, it does not take the page
        down); re-implementing that loop here would fork it. ``update()``
        already ran, so this only re-points what the loop walks.
        """
        manager.viewlets = elements
        return manager.render()
