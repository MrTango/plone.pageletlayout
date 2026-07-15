"""Status-messages chrome pagelet (wayfinder ticket 11).

Reuse-over-reimplement: the show-and-clear plumbing is
``IStatusMessage(request)`` (Products.statusmessages) and the alert type
mapping is plone.app.layout's ``MTYPES_DISPLAY`` — imported, not ported.
The pagelet owns only the themed ``aside`` shell and the alert markup
Barceloneta styles.
"""

from Products.statusmessages.interfaces import IStatusMessage

from plone.app.layout.viewlets.globalstatusmessage import MTYPES_DISPLAY
from plone.pageletlayout.chrome import ChromePagelet


class StatusMessagesChromePagelet(ChromePagelet):
    """The alert region (~plone.globalstatusmessage's job): render the
    request's queued messages as Bootstrap alerts, clearing them in the
    same breath (``show()`` semantics)."""

    def update(self):
        self.messages = IStatusMessage(self.request).show()

    def display_info_for_mtype(self, mtype):
        return MTYPES_DISPLAY.get(mtype, MTYPES_DISPLAY["info"])
