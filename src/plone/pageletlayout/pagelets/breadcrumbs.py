"""Breadcrumbs chrome pagelet (wayfinder ticket 10).

The crumb computation is ``@@breadcrumbs_view`` — CMFPlone plumbing, not a
viewlet job: interface-dispatched (INavigationRoot gets the empty
``RootPhysicalNavigationBreadcrumbs``), nav-root and view-action aware.
Reused, exactly as the classic ``plone.path_bar`` viewlet calls it; the
pagelet owns only the markup shell.
"""

from Products.CMFCore.utils import getToolByName
from zope.component import getMultiAdapter

from plone.base.navigationroot import get_navigation_root_object
from plone.pageletlayout.chrome import ChromePagelet


class BreadcrumbsChromePagelet(ChromePagelet):
    """The path bar (~plone.path_bar): Home plus the crumb trail from
    ``@@breadcrumbs_view``, in Barceloneta's breadcrumb markup."""

    def update(self):
        breadcrumbs_view = getMultiAdapter(
            (self.context, self.request), name="breadcrumbs_view"
        )
        self.breadcrumbs = breadcrumbs_view.breadcrumbs()
        portal = getToolByName(self.context, "portal_url").getPortalObject()
        nav_root = get_navigation_root_object(self.context, portal)
        self.navigation_root_url = nav_root.absolute_url()
