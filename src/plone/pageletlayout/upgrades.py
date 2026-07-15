"""GenericSetup upgrade steps for plone.pageletlayout.

Wayfinder ticket 04 (two-package re-role) + ticket 15: plone.pageletlayout is a
CSS-less integration package now — the whole layered cascade AND the editor
toolbar chrome moved into plonetheme.clara's single compiled bundle. A fresh
install of the default profile already ships the zero-bundle registry.xml, but
an already-installed site keeps the old bundle records in its registry until
these steps purge them.
"""

from zope.component import getUtility

from plone.registry.interfaces import IRegistry


#: The six theme-CSS bundles plone.pageletlayout used to register, all now
#: folded into plonetheme.clara's one compiled bundle. ``bootstrap5`` was our
#: own invented name (ticket 01: Plone 6.2 ships no stock bootstrap5 CSS
#: bundle), so purging it is safe — but the guard below removes a bundle ONLY
#: when its csscompilation still points at this package's resources, so a
#: same-named bundle owned by another add-on is never touched.
_OLD_THEME_BUNDLES = (
    "pageletlayout-layers",
    "bootstrap5",
    "pageletlayout-tokens",
    "pageletlayout-primitives",
    "pageletlayout-bridge",
    "pageletlayout-components",
)

#: The editor-toolbar chrome bundle (ticket 15). Its #edit-zone styling now
#: lives in plonetheme.clara's clara.min.css (theme-owned, as in Barceloneta),
#: leaving the base literally zero-CSS.
_OLD_TOOLBAR_BUNDLE = "pageletlayout-toolbar"

_RESOURCE_MARKER = "plone.pageletlayout"


def _purge_bundle(registry, name):
    """Delete every record of bundle ``name`` — but only if it is still ours.

    Guarded on the csscompilation value pointing at this package's resources, so
    a same-named bundle owned by another add-on is never touched. Idempotent: a
    bundle already gone (fresh install / re-run) is silently skipped.
    """
    css_key = f"plone.bundles/{name}/csscompilation"
    record = registry.records.get(css_key)
    if record is None:
        return  # already gone (fresh install / re-run)
    if _RESOURCE_MARKER not in (record.value or ""):
        return  # not ours — leave another add-on's bundle alone
    prefix = f"plone.bundles/{name}/"
    for record_name in list(registry.records.keys()):
        if record_name.startswith(prefix):
            del registry.records[record_name]


def remove_theme_css_bundles(context):
    """Purge the six relocated theme-CSS bundle records (idempotent)."""
    registry = getUtility(IRegistry)
    for name in _OLD_THEME_BUNDLES:
        _purge_bundle(registry, name)


def remove_toolbar_bundle(context):
    """Purge the relocated editor-toolbar chrome bundle record (idempotent)."""
    registry = getUtility(IRegistry)
    _purge_bundle(registry, _OLD_TOOLBAR_BUNDLE)
