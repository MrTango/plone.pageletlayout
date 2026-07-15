"""Custom manage-viewlets screens for the pagelet-only whole-body manager.

Stock ``@@manage-viewlets`` never lists our manager: that UI renders through
classic main_template and only decorates managers appearing on *its* page, and
our manager renders only in the pagelet layout. These views are scoped to the
one manager instead.

Reuse-over-reimplement: every mutator is inherited. ``ManageViewlets``
(``plone.app.viewletmanager.manager``) already ships
``_getOrder``/``moveAbove``/``moveBelow``/``hide``/``show``, all
manager-agnostic. ``_ManageViewletsBase`` adds only the pieces a management
screen needs on top — scoping, an ``elements()`` template helper, preview
links, and a small ``?action=…&viewlet=…`` protocol that redirects back to
itself.

* ``LayoutManageView`` (``@@manage-layout-viewlets``) — reorder + hide/show
  across the whole-body layout manager (the whole page).
"""

from Products.CMFPlone.resources.browser.resource import StylesView
from zope.component import getUtility
from zope.interface import classImplementsOnly
from zope.interface import implementedBy

from plone.app.viewletmanager.interfaces import IViewletManagementView
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.app.viewletmanager.manager import ManageViewlets
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
    """Shared base for the pagelet-manager management screens.

    A concrete view sets ``manager_name`` (the ``OrderedViewletManager`` this
    screen scopes to), ``view_name`` (the ``@@…`` name it is registered under,
    for the self-redirect + form action) and ``preview_managed`` (the view name
    the preview link points at). Everything else — the CSRF token,
    ``elements()``, ``preview_urls()``, the move helper and the action protocol
    — is shared, all driven off ``manager_name``.
    """

    manager_name = None
    view_name = None
    preview_managed = None

    def token(self):
        """CSRF token for the action links: these are GET requests that mutate
        the viewlet storage, so plone.protect must see a valid
        ``_authenticator`` or it diverts them to @@confirm-action."""
        return createToken()

    def elements(self):
        """The manager's viewlets in current order, as template rows."""
        storage = getUtility(IViewletSettingsStorage)
        skinname = self.context.getCurrentSkinName()
        hidden = set(storage.getHidden(self.manager_name, skinname))
        order = self._getOrder(self.manager_name)
        last = len(order) - 1
        return [
            {
                "name": name,
                "label": name.rsplit(".", 1)[-1],
                "hidden": name in hidden,
                "is_first": index == 0,
                "is_last": index == last,
            }
            for index, name in enumerate(order)
        ]

    def preview_urls(self):
        base = self.context.absolute_url()
        return {"managed": f"{base}/{self.preview_managed}"}

    def _move(self, viewlet, direction):
        order = self._getOrder(self.manager_name)
        index = order.index(viewlet)
        if direction == "up" and index > 0:
            self.moveAbove(self.manager_name, viewlet, order[index - 1])
        elif direction == "down" and index < len(order) - 1:
            self.moveBelow(self.manager_name, viewlet, order[index + 1])

    def __call__(self):
        action = self.request.get("action")
        viewlet = self.request.get("viewlet")
        if action and viewlet:
            if action in ("up", "down"):
                self._move(viewlet, action)
            elif action == "hide":
                self.hide(self.manager_name, viewlet)
            elif action == "show":
                self.show(self.manager_name, viewlet)
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
    """Order/visibility for the whole-body layout manager — reorder +
    hide/show across every visible element on the page."""

    manager_name = "plone.pageletlayout.layout"
    view_name = "manage-layout-viewlets"
    heading = "Whole-page layout"
    manages = "the whole-body pagelet layout manager"
    preview_managed = "pagelet_view"
