"""Probe viewlets for the stock-manager bridge tests (pagelets/managers.py).

Real ``browser:viewlet`` registrations against real stock managers, because
that is exactly what an add-on does — and what silently vanished before the
bridges existed. They subclass ``plone.app.layout.viewlets.ViewletBase`` so
they behave like any shipped viewlet (Acquisition, the ordering protocol the
manager's ``sort()`` needs, the security declarations
``BaseOrderedViewletManager.filter`` checks with ``guarded_hasattr``).

One class per probe: registrations are torn down by name in the tests, but a
shared class would blur which registration a rendered marker came from.
"""

from plone.app.layout.viewlets import ViewletBase


class _MarkerViewlet(ViewletBase):
    """Renders one identifiable marker and nothing else."""

    marker = None

    def update(self):
        # Deliberately not ViewletBase.update() — the portal_state lookups it
        # does are irrelevant here and only add failure modes.
        pass

    def render(self):
        return f'<p class="{self.marker}">{self.marker}</p>'


class AboveContentBodyProbe(_MarkerViewlet):
    """IAboveContentBody, the manager plone.tableofcontents lives in."""

    marker = "probe-abovecontentbody"


class BelowContentBodyProbe(_MarkerViewlet):
    """IBelowContentBody — related items, keywords, rights, contributors."""

    marker = "probe-belowcontentbody"


class PortalFooterProbe(_MarkerViewlet):
    """IPortalFooter, next to the colophon and the site actions."""

    marker = "probe-portalfooter"


class AboveContentTitleProbe(_MarkerViewlet):
    """IAboveContentTitle — an in-element position, inside the header."""

    marker = "probe-abovecontenttitle"


class BelowContentTitleProbe(_MarkerViewlet):
    """IBelowContentTitle — between the title and the description."""

    marker = "probe-belowcontenttitle"


class EditFormProbe(_MarkerViewlet):
    """Bound to ``view=IDexterityEditForm``: it renders only when the
    manager was looked up against the *published view*, which is what
    carries that marker (the wrapper, not the pagelet)."""

    marker = "probe-editform"
