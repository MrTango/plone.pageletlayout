"""Setup handlers for plone.pageletlayout."""
from Products.CMFPlone.interfaces import INonInstallable
from zope.interface import implementer


@implementer(INonInstallable)
class HiddenProfiles:
    """Hidden profiles from the Plone add-ons control panel."""

    def getNonInstallableProfiles(self):
        """Return list of profiles that should not be available for install."""
        return [
            "plone.pageletlayout:uninstall",
            "plone.pageletlayout.upgrades:1004",
            "plone.pageletlayout.upgrades:1005",
        ]


def uninstall(context):
    """Uninstall script."""
    # Do something on uninstall if needed
    pass
