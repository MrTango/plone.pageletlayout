"""@@search as a pagelet (classic-coverage map, ticket 07).

CMFPlone's ``Search`` view re-registered on the pageletlayout layer through
the FramedPage mechanism: the stock class keeps every query method
(``results`` / ``filter_query`` / ``sort_options`` / ``types_list`` / …) and
only its class-bound template is swapped for a body-only twin.

**The result-updating path needs no vehicle of its own.** The ticket flagged
``updated_search`` as the thing to work out — that fragment view no longer
exists in Plone 6.2. Mockup's ``pat-search`` refetches *the same URL* with
``?ajax_load=1`` and lifts ``#search-results`` / ``#search-term`` /
``#results-count`` out of the response by id, so the shipped ajax layout is
already exactly the fragment it asks for: same page, same view class, one
layout swap by the trigger chain. Sorting, filtering and pagination all go
through that one path.

``@@ajax-search`` (``AjaxSearch``) stays as it is: it returns JSON from its
own ``__call__``, never a page, so there is no chrome to convert.
"""

import os.path
from html import escape

from Products.CMFPlone.browser.search import Search
from zope.component import getMultiAdapter
from zope.interface import implementer

from plone.pageletlayout.interfaces import ISearchPagelet
from plone.pageletlayout.page import FramedPage
from plone.pageletlayout.page import FramedTemplate
from plone.pageletlayout.pagelets.head import HeadLinksChromePagelet


def _path(filename):
    return os.path.join(os.path.dirname(__file__), "templates", filename)


@implementer(ISearchPagelet)
class SearchPagelet(Search, FramedPage):
    """@@search: the stock Search view, framed.

    ``Search`` is template-only — no ``__call__`` of its own — so
    ``FramedPage.__call__`` renders the bound ``index``, exactly what Five's
    page class did for the classic registration.
    """

    index = FramedTemplate(_path("search.pt"))


class SearchHeadLinksChromePagelet(HeadLinksChromePagelet):
    """The head links, plus the search-feed alternate link.

    This is where a converted page's ``head_slot`` markup goes: a head
    element shadowed on the ``view=`` dimension (here ``ISearchPagelet``),
    the same specificity move the framed body and content header make. The
    ajax layout renders no head providers at all, so the fragment stays
    charset-only for free.

    The stock slot's second link, ``rel="home"``, is dropped as dead weight
    — no consumer, and the frame's logo already links the navigation root.
    """

    def search_feed_url(self):
        """The feed for the *current* query, or None when there is nothing
        to subscribe to (no query, or search feeds switched off site-wide —
        the same condition as the visible subscribe link in the body)."""
        if not self.request.form.get("SearchableText"):
            return None
        syndication = getMultiAdapter(
            (self.context, self.request), name="syndication-util"
        )
        if not syndication.search_rss_enabled():
            return None
        query_string = self.request.get("QUERY_STRING", "")
        return f"{self.context.absolute_url()}/search_rss?{query_string}"

    def render(self):
        links = super().render()
        url = self.search_feed_url()
        if url is None:
            return links
        return (
            f"{links}\n"
            '<link rel="alternate" type="application/rss+xml" '
            f'title="RSS 1.0" href="{escape(url, quote=True)}" />'
        )
