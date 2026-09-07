"""Hide the stock viewlets the pagelet layout reimplements."""
import logging


logger = logging.getLogger(__name__)

#: The profile whose ``viewlets`` step carries the new order + hidden set.
PROFILE = "profile-plone.pageletlayout:default"


def upgrade(context):
    """Re-import the ``viewlets`` step.

    Profile version 1002 -> 1003. The stock viewlet managers are bridged into
    the layout now (see pagelets/managers.py), so profiles/default/viewlets.xml
    gained the eight bridge elements in its order *and* a ``<hidden>`` set for
    the nine stock viewlets this package reimplements — without which an
    installed site would render logo, breadcrumbs, byline, colophon and site
    actions twice.

    Narrowed to the one import step: a full profile re-import would also
    replay types, registry and rolemap, overwriting whatever the site has
    customised since install.
    """
    logger.info("Re-importing the viewlets step: bridge order + stock hidden set")
    context.runImportStepFromProfile(PROFILE, "viewlets", run_dependencies=False)
