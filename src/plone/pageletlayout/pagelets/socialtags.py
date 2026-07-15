"""Social-tags body microdata chrome pagelet (wayfinder ticket 13).

Reuse-over-reimplement: ``SocialTagsViewlet`` is genuinely complex
(registry settings, syndication adapters, image scales, anonymous gating)
— its computation is wrapped like the head plumbing; only the invisible
``span#social-tags-body`` shell (classic ``social_tags_body.pt``) is owned.
The head-meta variant of the same viewlet already renders via
``HeadMetaChromePagelet``.
"""

from plone.app.layout.viewlets.social import SocialTagsViewlet
from plone.pageletlayout.chrome import ChromePagelet


class SocialTagsBodyChromePagelet(ChromePagelet):
    """The schema.org microdata span (~plone.socialtags' job): the wrapped
    viewlet's itemprop tags, display:none in the content region."""

    def update(self):
        viewlet = SocialTagsViewlet(self.context, self.request, self.view, None)
        viewlet.update()
        self.body_tags = viewlet.body_tags
