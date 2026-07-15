"""Global navigation chrome pagelet (wayfinder ticket 09).

The complex part — navtree build, depth query, caching, item markup — is
GlobalSectionsViewlet's, *reused*, not ported (Maik, 2026-07-11: reuse
complex code; plone.app.layout imports are not a problem). The pagelet owns
only the thin shell: the theme's navbar ul, which classically Diazo fills by
copying the content ul's children.

Caching comes along with the viewlet unchanged: plone.memoize.view.memoize
on its navtree/portal_tabs, per-request via request annotations — one tabs
lookup + one catalog query per page render however deep the tree recursion
goes.
"""

from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.pageletlayout.chrome import ChromePagelet


class GlobalnavChromePagelet(ChromePagelet):
    """The navbar tree (~plone.global_sections): wraps the stock viewlet
    and renders its tree into the theme's ul."""

    def update(self):
        self.sections = GlobalSectionsViewlet(
            self.context, self.request, self.view or self
        )
        # browser:viewlet stamps __name__ on its synthesized class;
        # instantiated directly it is None (the ticket-07 wrapper gotcha).
        self.sections.__name__ = "plone.global_sections"
        self.sections.update()

    @property
    def navtree(self):
        return self.sections.navtree

    def render_globalnav(self):
        return self.sections.render_globalnav()
