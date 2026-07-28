"""@@search as a pagelet (classic-coverage map, ticket 07).

CMFPlone's site search renders in the pagelet frame on the pageletlayout
layer — no classic master markup, no macro path — with the stock ``Search``
view class still doing every bit of the querying. Four things must hold at
once and each has its own case below:

* the page renders framed and searching actually works (round-trip),
* mockup's ``pat-search`` contract survives the conversion — it refetches
  the same URL with ``ajax_load=1`` and lifts three elements out by id, so
  the shipped ajax layout *is* the fragment vehicle,
* the de-utility-souped markup lays out with the ``plone-*`` primitives,
* the classic ``head_slot`` content (the search-feed alternate link) still
  reaches the head, now as a head element shadowed on the view dimension.
"""

import base64
import unittest

import transaction

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.base.interfaces.syndication import ISiteSyndicationSettings
from plone.namedfile.file import NamedBlobImage
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.testing.zope import Browser

from .test_live_surface import classic_markup_in
from .test_live_surface import missing_frame_in


class SearchTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    #: Titles created in setUp; "Zebra" is the unique term every query uses.
    ZEBRA = "Zebra Crossing Report"
    OTHER = "Unrelated Elephant Notes"

    def setUp(self):
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        api.content.create(
            container=self.portal, type="Document", id="zebra-doc", title=self.ZEBRA
        )
        api.content.create(
            container=self.portal, type="News Item", id="other-doc", title=self.OTHER
        )
        transaction.commit()

    def browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        browser.addHeader(
            "Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
        )
        return browser

    def search(self, query=""):
        """Open @@search with ``query`` and return the response body."""
        browser = self.browser()
        url = f"{self.portal_url}/@@search"
        if query:
            url = f"{url}?{query}"
        browser.open(url)
        return browser.contents

    def results_in(self, html):
        """The ``#search-results`` subtree.

        Result assertions must never read the whole page: the probe content
        sits at the portal root, so the global navigation lists it too.
        """
        return html.split('id="search-results"', 1)[1].split("</form>", 1)[0]

    def assert_framed(self, html, url="@@search"):
        self.assertEqual(
            classic_markup_in(html), (), f"{url} renders classic master markup"
        )
        self.assertEqual(
            missing_frame_in(html), (), f"{url} did not render the pagelet frame"
        )

    def set_debug_mode(self, value):
        from App.config import getConfiguration

        config = getConfiguration()
        old = getattr(config, "debug_mode", False)
        config.debug_mode = value
        self.addCleanup(setattr, config, "debug_mode", old)


class TestSearchPage(SearchTestCase):
    """The page renders framed, and the stock search actually searches."""

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.search())

    def test_renders_off_the_macro_path(self):
        # Frame markers alone can't tell a conversion from the bridge (the
        # bridge frames macro consumers too); the discriminator is the
        # deprecation signal, which a real pagelet never emits.
        self.set_debug_mode(True)
        browser = self.browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            browser.open(f"{self.portal_url}/@@search?SearchableText=Zebra")
        self.assert_framed(browser.contents)

    def test_query_returns_the_matching_item_only(self):
        results = self.results_in(self.search("SearchableText=Zebra"))
        self.assertIn(self.ZEBRA, results)
        self.assertNotIn(self.OTHER, results)

    def test_heading_shows_the_search_term(self):
        html = self.search("SearchableText=Zebra")
        self.assertIn('id="search-term"', html)
        self.assertIn("Search results for", html)

    def test_empty_query_renders_the_bare_search_page(self):
        html = self.search()
        self.assertIn("Search results", html)
        self.assertIn('id="searchform"', html)

    def test_no_matches_renders_the_no_results_message(self):
        html = self.search("SearchableText=nothingmatchesthisterm")
        self.assertIn("No results were found", html)

    def test_portal_type_filter_narrows_the_results(self):
        html = self.search("SearchableText=Zebra&portal_type%3Alist=News+Item")
        self.assertNotIn(self.ZEBRA, self.results_in(html))

    def test_result_count_is_rendered(self):
        html = self.search("SearchableText=Zebra")
        self.assertIn('id="results-count"', html)
        self.assertIn('id="search-results-number"', html)

    def test_heading_is_the_search_heading_not_the_portal_title(self):
        # The contentheader element is shadowed empty for framed pages, so
        # the portal title must not appear as the page h1.
        html = self.search("SearchableText=Zebra")
        self.assertNotIn(
            f'<h1 class="documentFirstHeading">{self.portal.Title()}</h1>', html
        )

    def test_batch_navigation_renders_for_a_long_result_set(self):
        for index in range(12):
            api.content.create(
                container=self.portal,
                type="Document",
                id=f"zebra-batch-{index}",
                title=f"Zebra Batch {index}",
            )
        transaction.commit()
        html = self.search("SearchableText=Zebra")
        self.assertIn('class="pagination"', html)
        self.assertIn("b_start:int", html)


class TestSearchResultThumbnails(SearchTestCase):
    """With ``plone.search_show_images`` on, a result with an image gets a
    thumbnail in the sidebar primitive's rail — the same content-plus-thumb
    shape listing.pt uses, so a result row reads like any other listed item.
    """

    #: A real 1x1 PNG, so the scale machinery has something to scale.
    PNG_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )

    def setUp(self):
        super().setUp()
        api.portal.set_registry_record("plone.search_show_images", True)
        api.content.create(
            container=self.portal,
            type="Image",
            id="zebra-image",
            title="Zebra Photograph",
            image=NamedBlobImage(
                data=self.PNG_1x1, filename="pixel.png", contentType="image/png"
            ),
        )
        transaction.commit()

    def test_thumbnail_renders_in_the_sidebar_rail(self):
        results = self.results_in(self.search("SearchableText=Zebra"))
        self.assertIn("plone-sidebar__aside", results)
        self.assertIn("image-responsive", results)
        self.assertIn("zebra-image/@@images/image", results)

    def test_no_rail_when_images_are_switched_off(self):
        # Proves the assertion above is not vacuous: the rail is the
        # show_images branch, nothing else emits it.
        api.portal.set_registry_record("plone.search_show_images", False)
        transaction.commit()
        results = self.results_in(self.search("SearchableText=Zebra"))
        self.assertNotIn("plone-sidebar__aside", results)


class TestSearchPatternHooks(SearchTestCase):
    """mockup's ``pat-search`` drives this page entirely through ids and
    class hooks in the body markup (``@plone/mockup`` src/pat/search).
    De-utility-souping the template must not drop any of them."""

    #: Every selector pat-search looks up, as a literal markup fragment.
    HOOKS = (
        "pat-search",  # the pattern trigger
        "searchPage",  # pat-search binds its submit handler to these forms
        'id="searchform"',
        'id="search-batch-start"',
        'id="advanced-search-input"',
        'id="search-filter"',
        'id="search-filter-toggle"',
        'id="pt_toggle"',
        "search-type-options",
        'id="sorting-options"',
        'name="sort_on"',
        'name="sort_order"',
        'id="search-results"',
        'id="search-term"',
        'id="results-count"',
        "data-default-sort=",
        "data-sort=",
    )

    def test_every_pattern_hook_survives_the_conversion(self):
        html = self.search("SearchableText=Zebra")
        for hook in self.HOOKS:
            with self.subTest(hook=hook):
                self.assertIn(hook, html)


class TestSearchNoUtilitySoup(SearchTestCase):
    """The rendered page is part of the markup contract: layout comes from
    the ``plone-*`` primitives, never Bootstrap spacing/flex utilities
    (design principle #3). test_template_lint pins the template file; this
    pins what actually reaches the browser for the converted page."""

    def search_form_markup(self):
        """The search form's own subtree — chrome and third-party markup
        are not this ticket's surface. plone.batching's shared navigation
        template renders inside the form and is third-party too, so it is
        cut as well (it opens with a ``<nav class=...>``)."""
        html = self.search("SearchableText=Zebra")
        form = html.split('id="searchform"', 1)[1].split("</form>", 1)[0]
        return form.split('<nav class="', 1)[0]

    def test_no_forbidden_utilities_in_the_rendered_form(self):
        from .test_template_lint import forbidden_in_markup

        self.assertEqual(forbidden_in_markup(self.search_form_markup()), [])

    def test_primitives_carry_the_layout(self):
        markup = self.search_form_markup()
        self.assertIn("plone-stack", markup)
        self.assertIn("plone-cluster", markup)


class TestSearchAjaxFragment(SearchTestCase):
    """pat-search refetches ``<same url>?ajax_load=1&<params>`` and pulls
    three elements out of the response by id — so the shipped ajax layout is
    the fragment vehicle, no ``updated_search`` view needed (that fragment
    view is gone from Plone 6.2 entirely)."""

    def fragment(self, query="SearchableText=Zebra"):
        return self.search(f"ajax_load=1&{query}")

    def test_ajax_load_selects_the_ajax_layout(self):
        self.assertIn("pagelet-layout-ajax", self.fragment())

    def test_fragment_does_not_replumb_the_head(self):
        self.assertNotIn("<title>", self.fragment())

    def test_fragment_carries_the_three_replaced_elements(self):
        html = self.fragment()
        for element_id in ("search-results", "search-term", "results-count"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', html)

    def test_fragment_carries_the_results(self):
        self.assertIn(self.ZEBRA, self.results_in(self.fragment()))

    def test_fragment_keeps_the_default_sort_attribute(self):
        # Read off `#search-results` by the pattern right after replacement.
        self.assertIn("data-default-sort=", self.fragment())


class TestSearchHeadLinks(SearchTestCase):
    """The classic ``head_slot``: the search-feed alternate link, now a head
    element shadowed on the ``view=ISearchPagelet`` dimension."""

    def search_feed_links_in(self, html):
        return [
            line
            for line in html.splitlines()
            if "application/rss+xml" in line and "search_rss" in line
        ]

    def disable_search_rss(self):
        registry = api.portal.get_tool("portal_registry")
        settings = registry.forInterface(ISiteSyndicationSettings)
        settings.search_rss_enabled = False
        transaction.commit()

    def test_query_page_advertises_the_search_feed(self):
        html = self.search("SearchableText=Zebra")
        self.assertTrue(
            self.search_feed_links_in(html),
            "no search_rss alternate link in the head",
        )

    def test_bare_search_page_does_not_advertise_a_feed(self):
        # Nothing to subscribe to without a query — the stock condition.
        self.assertFalse(self.search_feed_links_in(self.search()))

    def test_disabled_search_rss_drops_the_link(self):
        self.disable_search_rss()
        self.assertFalse(
            self.search_feed_links_in(self.search("SearchableText=Zebra"))
        )

    def test_fragment_never_carries_head_links(self):
        # The ajax layout's head is charset-only by contract.
        html = self.search("ajax_load=1&SearchableText=Zebra")
        self.assertFalse(self.search_feed_links_in(html))

    def test_other_pages_keep_the_plain_head_links(self):
        # The shadow is scoped to the search pagelet: a sibling framed page
        # must still resolve the base head-links element.
        browser = self.browser()
        browser.open(f"{self.portal_url}/login")
        self.assertFalse(self.search_feed_links_in(browser.contents))
        self.assertIn('rel="search"', browser.contents)
