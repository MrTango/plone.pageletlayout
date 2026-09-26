"""Rendering stock viewlet managers from chrome pagelets.

The lookup happens **in code, against ``self.view``** — the published view is
what carries the dimension a manager's viewlets bind to (a Dexterity edit
form's *wrapper* provides ``IDexterityEditForm``). A ``provider:`` expression
inside a chrome pagelet's own template would hand the manager THIS pagelet as
the view: the BodyChromePagelet lesson, documented in layout.py.
"""

from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider

from plone.pageletlayout.chrome import ChromePagelet
from plone.pageletlayout.pagelets.slots import CONTENT_HEADER_SLOTS
from plone.pageletlayout.pagelets.slots import SLOTS


#: Every stock manager whose viewlets reach a pagelet page: the slots, plus
#: ``plone.globalstatusmessage`` (inside the status-messages element) and
#: ``plone.toolbar`` (a foreign subsystem the frame renders itself). The
#: viewlet ratchet treats a viewlet in any *other* manager as an orphan.
RENDERED_MANAGERS = frozenset(set(SLOTS) | {"plone.globalstatusmessage", "plone.toolbar"})


def render_stock_manager(pagelet, manager_name):
    """Update and render one stock manager for ``pagelet.view``, stripped so
    an empty manager is detectable."""
    manager = getMultiAdapter(
        (pagelet.context, pagelet.request, pagelet.view),
        IContentProvider,
        name=manager_name,
    )
    manager.update()
    return manager.render().strip()


class ContentHeaderChromePagelet(ChromePagelet):
    """The content header, with the three content-header slots around the
    title and the description, in classic main_template's order."""

    def update(self):
        for attribute, manager_name in CONTENT_HEADER_SLOTS.items():
            setattr(self, attribute, render_stock_manager(self, manager_name))
