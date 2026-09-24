"""Header element chrome pagelets (wayfinder ticket 08).

Visible chrome, so the clean-reimplementation decision applies: each class
does the classic viewlet's *job* (registry/actions lookups) without touching
plone.app.layout.
"""

from pathlib import Path

import Products.CMFPlone.browser
from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import getSiteLogo
from zope.component import getUtility

from plone.base.interfaces import ISearchSchema
from plone.base.interfaces import ISiteSchema
from plone.base.navigationroot import get_navigation_root_object
from plone.formwidget.namedfile.converter import b64decode_file
from plone.namedfile.utils import getImageInfo
from plone.pageletlayout.chrome import ChromePagelet
from plone.registry.interfaces import IRegistry


STOCK_LOGO = Path(Products.CMFPlone.browser.__file__).parent / "static" / "plone-logo.svg"


def logo_dimensions(site_logo):
    """(width, height) of the logo, or (None, None) when unreadable."""
    try:
        data = b64decode_file(site_logo)[1] if site_logo else STOCK_LOGO.read_bytes()
        width, height = getImageInfo(data)[1:]
    except Exception:
        return None, None
    if width <= 1 or height <= 1:
        return None, None
    return width, height


class LogoChromePagelet(ChromePagelet):
    """The site logo (~plone.logo's job): registry logo — or the stock
    resource — linked to the navigation root."""

    def update(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISiteSchema, prefix="plone", check=False)
        self.logo_title = settings.site_title
        portal = getToolByName(self.context, "portal_url").getPortalObject()
        nav_root = get_navigation_root_object(self.context, portal)
        self.navigation_root_url = nav_root.absolute_url()
        self.navigation_root_title = nav_root.Title()
        self.img_src = getSiteLogo()
        self.img_width, self.img_height = logo_dimensions(settings.site_logo)


class AnontoolsChromePagelet(ChromePagelet):
    """The login/register links (~plone.anontools' job): the portal 'user'
    actions, for anonymous visitors only. Visibility is logic here, not a
    permission — providers are never traversed (pattern decision #4)."""

    def update(self):
        mtool = getToolByName(self.context, "portal_membership")
        self.anonymous = bool(mtool.isAnonymousUser())
        self.user_actions = []
        if not self.anonymous:
            return
        atool = getToolByName(self.context, "portal_actions")
        for action in atool.listActionInfos(object=aq_inner(self.context)):
            if action["category"] != "user":
                continue
            self.user_actions.append(
                {
                    "title": action["title"],
                    "href": action["url"],
                    "id": "personaltools-{}".format(action["id"]),
                    "target": action.get("link_target", None),
                }
            )

    def render(self):
        if not (self.anonymous and self.user_actions):
            return ""
        return super().render()


class SearchboxChromePagelet(ChromePagelet):
    """The search form (~plone.searchbox's job): livesearch setting from
    the registry, action URL on the navigation root. The classic render
    needs Diazo to move it into the navbar; the layout places it there."""

    def update(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISearchSchema, prefix="plone")
        self.livesearch = settings.enable_livesearch
        self.show_images = settings.search_show_images
        portal = getToolByName(self.context, "portal_url").getPortalObject()
        nav_root = get_navigation_root_object(self.context, portal)
        self.navigation_root_url = nav_root.absolute_url()
