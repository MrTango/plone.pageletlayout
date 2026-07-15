"""Footer chrome pagelets (wayfinder ticket 12).

The portlet-indirection decision: the classic footer is portlet output
(``plone.footer`` viewlet -> ``plone.footerportlets`` manager -> three stock
portlets), but portlets machinery is out of scope — so each element is a
plain chrome pagelet and the indirection is skipped. Every pagelet owns its
themed Barceloneta footer row (``.row > .col-12`` shell included), so the
layout's footer container stays markup-free.

CopyrightChromePagelet doubles as the ticket-02 worked example: its trap
layout + publishable twin (``copyright-page``) live in configure.zcml, the
mechanism claims in tests/test_chrome_pagelet.py.
"""

from Acquisition import aq_inner
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName

from plone.pageletlayout.chrome import ChromePagelet


class CopyrightChromePagelet(ChromePagelet):
    """The footer signature (~the 'footer' Classic portlet rendering
    ``@@footer``): static copyright/license markup; only the year is
    computed."""

    def update(self):
        self.year = DateTime().year()


class SiteActionsChromePagelet(ChromePagelet):
    """The site actions (~the 'actions' portlet, category site_actions):
    Site Map / Accessibility / Contact from the actions tool. No visible
    actions -> no row (Diazo's drop rule, as render logic — the anontools
    precedent)."""

    def update(self):
        atool = getToolByName(self.context, "portal_actions")
        self.site_actions = [
            {
                "id": action["id"],
                "title": action["title"],
                "href": action["url"],
                "target": action.get("link_target", None),
            }
            for action in atool.listActionInfos(object=aq_inner(self.context))
            if action["category"] == "site_actions"
        ]

    def render(self):
        if not self.site_actions:
            return ""
        return super().render()
