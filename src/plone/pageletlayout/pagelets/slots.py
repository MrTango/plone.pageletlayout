"""Slots: the stock viewlet managers the frame renders, and which element
renders in which of them.

The frame nests Plone's own managers in their classic, semantic places
(``templates/pagelayout.pt``). Layout elements are registered once, for
``ILayoutManager`` — the element pool, which nothing renders directly. The
registry record ``ASSIGNMENTS_RECORD`` maps each element to the slot it
renders in, and ``AssignedElements`` hands the assigned elements to that
slot's manager through plone.app.viewletmanager's ``IAdditionalViewlets``
hook. Order and visibility inside a slot come from
``IViewletSettingsStorage``, exactly as for the stock viewlets next to them.
"""

from zope.component import adapter
from zope.component import getSiteManager
from zope.component import queryUtility
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import providedBy
from zope.viewlet.interfaces import IViewlet
from zope.viewlet.interfaces import IViewletManager

from plone.app.viewletmanager.interfaces import IAdditionalViewlets
from plone.pageletlayout.interfaces import IPlonePageletlayoutLayer
from plone.registry.interfaces import IRegistry


class ILayoutManager(IViewletManager):
    """The element pool: every layout element is registered for it, and a
    slot assignment decides which stock manager renders it. No manager
    provides it."""


#: element name -> slot (stock manager) name
ASSIGNMENTS_RECORD = "plone.pageletlayout.slot_assignments"

#: The slots, in page order. The frame renders each one exactly once.
SLOTS = (
    "plone.portaltop",
    "plone.portalheader",
    "plone.mainnavigation",
    "plone.abovecontent",
    "plone.abovecontenttitle",
    "plone.belowcontenttitle",
    "plone.belowcontentdescription",
    "plone.abovecontentbody",
    "plone.belowcontentbody",
    "plone.belowcontent",
    "plone.portalfooter",
)

#: The slots inside the content header, around the title and description.
#: The contentheader element renders them, not the region.
CONTENT_HEADER_SLOTS = {
    "above_title": "plone.abovecontenttitle",
    "below_title": "plone.belowcontenttitle",
    "below_description": "plone.belowcontentdescription",
}

#: The shipped assignment, where classic Plone renders the viewlet each
#: element replaces. profiles/default/registry.xml holds the same table.
DEFAULT_ASSIGNMENTS = {
    "plone.pageletlayout.logo": "plone.portalheader",
    "plone.pageletlayout.anontools": "plone.portalheader",
    "plone.pageletlayout.searchbox": "plone.portalheader",
    "plone.pageletlayout.globalnav": "plone.mainnavigation",
    "plone.pageletlayout.breadcrumbs": "plone.abovecontent",
    "plone.pageletlayout.socialtags": "plone.abovecontenttitle",
    "plone.pageletlayout.contentheader": "plone.abovecontentbody",
    "plone.pageletlayout.byline": "plone.belowcontenttitle",
    "plone.pageletlayout.siteactions": "plone.portalfooter",
    "plone.pageletlayout.copyright": "plone.portalfooter",
    "plone.pageletlayout.colophon": "plone.portalfooter",
}


def slot_assignments():
    registry = queryUtility(IRegistry)
    if registry is None:
        return {}
    return registry.get(ASSIGNMENTS_RECORD) or {}


def assign(element, slot):
    """Move ``element`` into ``slot``; an empty slot unassigns it."""
    registry = queryUtility(IRegistry)
    assignments = dict(registry.get(ASSIGNMENTS_RECORD) or {})
    if slot:
        assignments[element] = slot
    else:
        assignments.pop(element, None)
    registry[ASSIGNMENTS_RECORD] = assignments


def element_factory(context, request, view, name):
    """The pool registration of element ``name`` for this lookup, or None."""
    required = (
        providedBy(context),
        providedBy(request),
        providedBy(view),
        ILayoutManager,
    )
    return getSiteManager().adapters.lookup(required, IViewlet, name=name)


@implementer(IAdditionalViewlets)
@adapter(Interface, IPlonePageletlayoutLayer, Interface, IViewletManager)
class AssignedElements:
    """The elements assigned to one slot, built for that slot's manager."""

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.view = view
        self.manager = manager

    def viewlets(self):
        slot = getattr(self.manager, "__name__", None)
        for name, target in slot_assignments().items():
            if target != slot:
                continue
            factory = element_factory(self.context, self.request, self.view, name)
            if factory is not None:
                yield name, factory(self.context, self.request, self.view, self.manager)
