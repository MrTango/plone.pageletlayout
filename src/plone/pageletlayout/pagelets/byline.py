"""Byline chrome pagelet (wayfinder ticket 15).

Reuse-over-reimplement, whole-viewlet edition: ``DocumentBylineViewlet``
carries its own ``index`` template and its markup is self-gating
(``view/show`` — authenticated or the publication-date registry switch;
the author part additionally behind ``allow_anon_views_about``). Wrapping
class + template gives exact classic markup and behavior; the pagelet owns
nothing but the wrapping (the head-plumbing pattern, applied to a visible
element because the *whole* element is reused, shell included).
"""

from plone.app.layout.viewlets.content import DocumentBylineViewlet
from plone.pageletlayout.chrome import ChromePagelet


class BylineChromePagelet(ChromePagelet):
    """The document byline (~plone.documentbyline): author badges,
    publication/modification dates, expiry marker."""

    def update(self):
        self.viewlet = DocumentBylineViewlet(
            self.context, self.request, self.view, None
        )
        self.viewlet.update()

    def render(self):
        return self.viewlet.render()
