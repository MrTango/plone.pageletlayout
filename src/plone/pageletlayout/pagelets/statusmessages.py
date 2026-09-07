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

The manager lookup itself is ``managers.render_stock_manager`` — this element
was the prototype the stock-manager bridges generalized, and sharing the
helper keeps the two from drifting.
"""

from plone.pageletlayout.chrome import ChromePagelet
from plone.pageletlayout.pagelets.managers import render_stock_manager


#: The stock manager's provider name (plone.app.layout's viewlets/configure.zcml).
MANAGER_NAME = "plone.globalstatusmessage"


class StatusMessagesChromePagelet(ChromePagelet):
    """The alert region — plone.globalstatusmessage's job, done by
    plone.globalstatusmessage.

    A manager bridge like the ones in managers.py, and it uses the same
    helper: the lookup happens in code against ``self.view``, and every
    viewlet that rides it logs the deprecation signal. It differs only in
    owning a themed ``aside`` shell of its own — which is why it is not one
    of the generic ``StockManagerChromePagelet`` registrations.
    """

    def update(self):
        self.contents = render_stock_manager(self, MANAGER_NAME)
