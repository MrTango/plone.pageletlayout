"""The management screen for the slot layout.

Stock ``@@manage-viewlets`` orders and hides viewlets per manager, but cannot
move a layout element to another slot. This screen does all three for the
slots the frame renders.

Reuse-over-reimplement: every mutator is inherited. ``ManageViewlets``
(``plone.app.viewletmanager.manager``) already ships
``_getOrder``/``moveAbove``/``moveBelow``/``hide``/``show``, all
manager-agnostic. ``_ManageViewletsBase`` adds only the pieces a management
screen needs on top — the ``slots()`` template helper, slot assignment, preview
links, and a small ``?action=…&manager=…&viewlet=…`` protocol redirecting back to
itself.

* ``LayoutManageView`` (``@@manage-layout-viewlets``) — reorder, hide/show
  and assign to a slot, for every slot on the page.
"""

from Products.CMFPlone.resources.browser.resource import StylesView
from zope.component import getSiteManager
from zope.component import getUtility
from zope.interface import classImplementsOnly
from zope.interface import implementedBy
from zope.interface import providedBy
from zope.viewlet.interfaces import IViewlet

from plone.app.viewletmanager.interfaces import IViewletManagementView
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.app.viewletmanager.manager import ManageViewlets
from plone.pageletlayout.pagelets.slots import assign
from plone.pageletlayout.pagelets.slots import ILayoutManager
from plone.pageletlayout.pagelets.slots import slot_assignments
from plone.pageletlayout.pagelets.slots import SLOTS
from plone.protect.authenticator import createToken


class _StandalonePage:
    """Render these screens as self-contained pages, NOT through classic
    main_template.

    main_template wraps the admin table in the whole site chrome, which is
    pure noise around a viewlet-order table. These screens supply their own
    ``<head>``/``<body>`` instead; the templates pull ``styles()`` into the
    head so the Bootstrap classes they use still render (reusing the
    resource-registry CSS the rest of the site loads), with none of the chrome.

    CSS only — ``StylesView``, not ``ScriptsView`` — so the page stays a plain
    styled document with no mockup/pattern JS behaviors attached.

    Un-themed, like the front-end pagelet views: ``styles()`` sets
    ``X-Theme-Disabled`` before ``StylesView`` runs, so it omits
    ``barceloneta.min.css`` (the theme production-css — ``StylesView`` gates it
    on ``theming_policy.isThemeEnabled()``, which reads that response header);
    plone.app.theming reads the same header post-render and skips the Diazo
    transform. What's left is our own registry bundles.
    """

    def styles(self):
        # set BEFORE StylesView renders (same call) so isThemeEnabled() is
        # already False when it decides whether to emit the theme CSS
        self.request.response.setHeader("X-Theme-Disabled", "1")
        renderer = StylesView(self.context, self.request, self)
        renderer.__name__ = "StylesView"
        renderer.update()
        return renderer.render()


class _ManageViewletsBase(_StandalonePage, ManageViewlets):
    """Order, visibility and slot assignment for the slot layout.

    One table per slot (``slots.SLOTS``, page order), listing the stock
    viewlets and the layout elements assigned to it. A small
    ``?action=…&manager=…&viewlet=…`` protocol redirects back to itself.
    """

    view_name = None
    preview_managed = None

    def token(self):
        """CSRF token for the action links: these are GET requests that mutate
        the viewlet storage, so plone.protect must see a valid
        ``_authenticator`` or it diverts them to @@confirm-action."""
        return createToken()

    def pool_elements(self):
        """Names of every layout element registered for this request."""
        required = (
            providedBy(self.context),
            providedBy(self.request),
            providedBy(self),
            ILayoutManager,
        )
        return sorted(
            name for name, _factory in getSiteManager().adapters.lookupAll(required, IViewlet)
        )

    def slots(self):
        """Each slot with its viewlets in current order, as template rows."""
        storage = getUtility(IViewletSettingsStorage)
        skinname = self.context.getCurrentSkinName()
        elements = set(self.pool_elements())
        assignments = slot_assignments()
        result = []
        for slot in SLOTS:
            hidden = set(storage.getHidden(slot, skinname))
            order = self._getOrder(slot)
            last = len(order) - 1
            rows = [
                {
                    "name": name,
                    "label": name.rsplit(".", 1)[-1],
                    "hidden": name in hidden,
                    "is_first": index == 0,
                    "is_last": index == last,
                    "is_element": name in elements and assignments.get(name) == slot,
                }
                for index, name in enumerate(order)
            ]
            result.append({"name": slot, "label": slot.rsplit(".", 1)[-1], "rows": rows})
        return result

    def unassigned(self):
        """Layout elements no slot renders."""
        assignments = slot_assignments()
        return [name for name in self.pool_elements() if assignments.get(name) not in SLOTS]

    def slot_names(self):
        return SLOTS

    def preview_urls(self):
        base = self.context.absolute_url()
        return {"managed": f"{base}/{self.preview_managed}"}

    def _move(self, manager, viewlet, direction):
        order = self._getOrder(manager)
        index = order.index(viewlet)
        if direction == "up" and index > 0:
            self.moveAbove(manager, viewlet, order[index - 1])
        elif direction == "down" and index < len(order) - 1:
            self.moveBelow(manager, viewlet, order[index + 1])

    def __call__(self):
        action = self.request.get("action")
        viewlet = self.request.get("viewlet")
        manager = self.request.get("manager")
        if action and viewlet:
            if action == "assign":
                slot = self.request.get("slot")
                if not slot or slot in SLOTS:
                    assign(viewlet, slot)
            elif manager in SLOTS:
                if action in ("up", "down"):
                    self._move(manager, viewlet, action)
                elif action == "hide":
                    self.hide(manager, viewlet)
                elif action == "show":
                    self.show(manager, viewlet)
            self.request.response.redirect(f"{self.context.absolute_url()}/@@{self.view_name}")
            return ""
        return self.index()


# These screens reuse ManageViewlets purely for its storage mutators
# (_getOrder/moveAbove/moveBelow/hide/show) and render their OWN scoped table.
# But ManageViewlets is @implementer(IViewletManagementView), and that marker
# makes every OrderedViewletManager in main_template render in
# management-decoration mode the moment our view sits in their __parent__ chain.
# Strip the marker (keeping IBrowserView/ILocation) so only our table renders.
classImplementsOnly(
    _ManageViewletsBase,
    *(iface for iface in implementedBy(_ManageViewletsBase) if iface is not IViewletManagementView),
)


class LayoutManageView(_ManageViewletsBase):
    """Order, visibility and slot assignment for the whole page."""

    view_name = "manage-layout-viewlets"
    heading = "Page layout"
    preview_managed = "pagelet_view"
