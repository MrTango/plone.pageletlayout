"""Status-messages chrome pagelet (wayfinder ticket 11).

Reuse-over-reimplement, and the reuse has to be the *manager*:
``plone.globalstatusmessage`` is not one viewlet but an
``OrderedViewletManager`` (``IGlobalStatusMessage``), and the show-and-clear
loop over ``IStatusMessage(request)`` is only its first entry. Add-ons
register alongside it — plone.app.dexterity's default-page warning ("You are
editing the default view of a container", bound to ``view=IDexterityEditForm``),
plone.volto's backend warning — so an element that renders only the message
loop silently drops every one of them. This pagelet owns the themed ``aside``
shell and nothing else; the manager renders inside it.
"""

from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider

from plone.pageletlayout.chrome import ChromePagelet


#: The stock manager's provider name (plone.app.layout's viewlets/configure.zcml).
MANAGER_NAME = "plone.globalstatusmessage"


class StatusMessagesChromePagelet(ChromePagelet):
    """The alert region — plone.globalstatusmessage's job, done by
    plone.globalstatusmessage."""

    def update(self):
        # Looked up in code against self.view — the published view, which is
        # what carries the dimension the manager's viewlets bind to (a
        # Dexterity edit form's wrapper provides IDexterityEditForm). A
        # ``provider:`` expression in this pagelet's own template would hand
        # the manager THIS pagelet as the view (the BodyChromePagelet lesson).
        self.manager = getMultiAdapter(
            (self.context, self.request, self.view),
            IContentProvider,
            name=MANAGER_NAME,
        )
        self.manager.update()

    @property
    def contents(self):
        return self.manager.render()
