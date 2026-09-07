"""The stock viewlet managers, bridged into the pagelet layout.

The layout renders exactly one viewlet manager of its own
(``plone.pageletlayout.layout``, see layout.py). Plone's *other* managers —
``IAboveContentBody``, ``IPortalFooter``, ``IBelowContentBody``, … — are
where every add-on registers its viewlets, so without a bridge those
viewlets vanish from a pagelet page with no error at all: no exception, no
log line, just missing content. Stock Plone alone loses lock info, the table
of contents, contributors, keywords, related items, rights, the document
actions and the member tools.

The bridge is the status-messages pattern generalized: render the stock
*manager*, don't re-implement its viewlets. One class,
``StockManagerChromePagelet``, parameterized per ZCML registration by
``manager_name=`` exactly the way ``PageletViewlet`` is parameterized by
``pagelet=``.

The lookup happens **in code, against ``self.view``** — the published view
is what carries the dimension a manager's viewlets bind to (a Dexterity edit
form's *wrapper* is what provides ``IDexterityEditForm``;
``plone.dexterity.browser.edit`` does ``classImplements(DefaultEditView,
IDexterityEditForm)``). A ``provider:`` expression inside the pagelet's own
template would hand the manager THIS pagelet as the view: the
BodyChromePagelet lesson, documented in layout.py.

Two kinds of bridge, and the difference is structural:

* **Sibling elements** (``SIBLING_MANAGERS``) sit directly in the layout
  manager, so they are storage-managed like every other element —
  hideable, reorderable, visible in ``@@manage-layout-viewlets``.
* **In-element providers** (``CONTENT_HEADER_MANAGERS``) have no meaning as
  siblings: ``plone.abovecontenttitle`` is *above the title*, which only
  exists inside the content header. They render inside contentheader.pt,
  through ``ContentHeaderChromePagelet``.

Bridging alone would be a regression: nine stock viewlets duplicate elements
this package reimplements (logo, breadcrumbs, byline, colophon, …), so
profiles/default/viewlets.xml hides them. That is configuration, not a
code-level exemption — an integrator who prefers the stock viewlet can just
unhide it.

Finally, a bridge is a waypoint, not a destination: every viewlet that
renders through one logs a deprecation signal naming itself and the fix
(register into ``ILayoutManager`` instead). Viewlets in managers we do *not*
bridge still vanish silently — tests/test_viewlet_ratchet.py is the meter
for those.
"""

import logging

from App.config import getConfiguration
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider

from plone.pageletlayout.bridge import PORTING_DOCS
from plone.pageletlayout.chrome import ChromePagelet


logger = logging.getLogger(__name__)

#: ``(manager name, viewlet name)`` pairs already logged in this process —
#: the production rate limit, the same two-tier shape as
#: ``bridge.warn_macro_use`` (development mode logs every render).
_warned_viewlets = set()

#: The stock managers rendered as sibling layout elements: element provider
#: name -> stock manager name. The same pairs ride on the ZCML stanzas
#: (``manager_name=`` in managers.zcml); a parity test pins the two against
#: each other, as it does for ELEMENTS and viewlets.xml.
SIBLING_MANAGERS = {
    "plone.pageletlayout.portaltop": "plone.portaltop",
    "plone.pageletlayout.portalheader": "plone.portalheader",
    "plone.pageletlayout.mainnavigation": "plone.mainnavigation",
    "plone.pageletlayout.abovecontent": "plone.abovecontent",
    "plone.pageletlayout.abovecontentbody": "plone.abovecontentbody",
    "plone.pageletlayout.belowcontentbody": "plone.belowcontentbody",
    "plone.pageletlayout.belowcontent": "plone.belowcontent",
    "plone.pageletlayout.portalfooter": "plone.portalfooter",
}

#: The three managers that belong *inside* the content header: content-header
#: attribute -> stock manager name, in the order classic main_template renders
#: them around the title and the description.
CONTENT_HEADER_MANAGERS = {
    "above_title": "plone.abovecontenttitle",
    "below_title": "plone.belowcontenttitle",
    "below_description": "plone.belowcontentdescription",
}

#: Every stock manager whose viewlets reach a pagelet page. The sibling and
#: in-element bridges, plus the two managers that were already rendered
#: before this module existed: ``plone.globalstatusmessage`` (the
#: status-messages element is a bridge of its own, see statusmessages.py) and
#: ``plone.toolbar`` (a ``provider:`` expression straight in layout.pt — a
#: foreign subsystem that self-gates). The viewlet ratchet treats these as
#: the reachable set; a viewlet in any *other* manager is an orphan.
RENDERED_MANAGERS = frozenset(
    set(SIBLING_MANAGERS.values())
    | set(CONTENT_HEADER_MANAGERS.values())
    | {"plone.globalstatusmessage", "plone.toolbar"}
)


#: The modules the viewlet ZCML directives synthesize their classes in.
#: ``browser:viewlet`` never registers the class an add-on wrote — it
#: registers ``type(class_.__name__, (class_, SimpleAttributeViewlet), …)``,
#: built in one of these modules. So a viewlet's own ``__module__`` names
#: the directive, never the add-on, and is useless in a message or a
#: checked-in list.
_FACTORY_MODULES = frozenset(
    {
        "Products.Five.viewlet.metaconfigure",
        "zope.viewlet.metaconfigure",
    }
)


def viewlet_class_origin(klass):
    """``module.ClassName`` of the class an add-on actually wrote.

    The synthesized class *keeps the base's name*, so the first base of the
    same name from a real module is the code to port. A template-only
    viewlet has no such base — ``browser:viewlet`` synthesizes the whole
    class and names it after the template file, which is then the honest
    identifier, so that name is returned as-is.
    """
    for base in klass.__mro__[1:]:
        if base.__name__ == klass.__name__ and base.__module__ not in _FACTORY_MODULES:
            return f"{base.__module__}.{base.__name__}"
    return f"{klass.__module__}.{klass.__name__}"


def warn_bridged_viewlets(manager_name, manager):
    """Log the deprecation signal for every viewlet the bridge just rendered.

    Two-tier rate limit, copied from ``bridge.warn_macro_use``:
    ``logger.warning`` on every render in development mode, one
    ``logger.info`` per (manager, viewlet) per process otherwise.

    Logging rather than ``warnings.warn(DeprecationWarning)`` deliberately:
    Zope's default filters swallow those and dedupe them per code location,
    which would collapse every add-on's viewlet into one anonymous line.

    Hidden viewlets never reach ``manager.viewlets``
    (``BaseOrderedViewletManager.filter``), so a stock duplicate we hide in
    viewlets.xml is silent — as it should be, there is nothing to port.
    """
    debug_mode = getConfiguration().debug_mode
    for viewlet in manager.viewlets:
        name = getattr(viewlet, "__name__", None) or repr(viewlet)
        origin = viewlet_class_origin(type(viewlet))
        message = (
            f"Viewlet {name} ({origin}) renders through the stock viewlet "
            f"manager {manager_name}, bridged into the whole-body pagelet "
            f"layout by plone.pageletlayout. Register it into "
            f"plone.pageletlayout.pagelets.layout.ILayoutManager instead, so "
            f"it becomes a layout element an integrator can order and hide — "
            f"see {PORTING_DOCS}."
        )
        if debug_mode:
            logger.warning(message)
        elif (manager_name, name) not in _warned_viewlets:
            _warned_viewlets.add((manager_name, name))
            logger.info(message)


def render_stock_manager(pagelet, manager_name):
    """Update and render one stock viewlet manager for ``pagelet``.

    The lookup triple is (context, request, ``pagelet.view``) — the
    published view, never the pagelet (see the module docstring).
    """
    manager = getMultiAdapter(
        (pagelet.context, pagelet.request, pagelet.view),
        IContentProvider,
        name=manager_name,
    )
    manager.update()
    warn_bridged_viewlets(manager_name, manager)
    # Stripped so "empty" is detectable: OrderedViewletManager joins its
    # viewlets with newlines, so a manager whose viewlets all render nothing
    # still returns whitespace — and the element would emit an empty wrapper
    # on every page for every bridge.
    return manager.render().strip()


class StockManagerChromePagelet(ChromePagelet):
    """One stock viewlet manager as a layout element.

    ``manager_name`` names the manager to render and is set *per
    registration*: ``plone:chromepagelet`` passes arbitrary attributes into
    the class dict, so one class serves every bridge —

        <plone:chromepagelet
            name="plone.pageletlayout.portalfooter"
            class=".managers.StockManagerChromePagelet"
            manager_name="plone.portalfooter"
            layer="…"
            />

    The content template is registered once, standalone, for this class:
    eight stanzas each carrying ``template=`` would be eight registrations
    of the same adapter, i.e. a configuration conflict.
    """

    manager_name = None  # the stock manager's name; set by the registration

    def update(self):
        # Rendered here, not in the template: render() has side effects on
        # some managers (the message queue drains), so it must happen once.
        self.contents = render_stock_manager(self, self.manager_name)

    @property
    def element_class(self):
        """``element-portalfooter`` for ``plone.portalfooter`` — the same
        ``element-<suffix>`` hook every other layout element carries."""
        return "element-" + self.manager_name.rsplit(".", 1)[-1]


class ContentHeaderChromePagelet(ChromePagelet):
    """The content header, with the three in-element managers around it.

    ``plone.abovecontenttitle`` / ``plone.belowcontenttitle`` /
    ``plone.belowcontentdescription`` are positions *within* a title-and-
    description block — as siblings of the block they would mean nothing —
    so they render inside this element's template, in classic
    main_template's order.
    """

    def update(self):
        for attribute, manager_name in CONTENT_HEADER_MANAGERS.items():
            setattr(self, attribute, render_stock_manager(self, manager_name))
