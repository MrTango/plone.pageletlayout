"""The content actions as pagelets (classic-coverage map, ticket 09).

The four plone.app.content / plone.app.layout admin-action pages in the
map's high-traffic cut — ``delete_confirmation``, ``object_rename``,
``content_status_history`` and ``@@historyview`` — re-registered on the
pageletlayout layer through the FramedPage mechanism, stock view classes
reused whole.

Three of them *write*, so the cases below are round-trips: the assertion is
that the delete/rename/transition landed in the ZODB, not that some markup
appeared. The ticket flagged two things to watch, one case group each:

* the **modal path** — delete, rename and the workflow menu's "Advanced…"
  are all opened by ``pat-plone-modal``. The modal fetches the link's plain
  ``href`` (it never appends ``ajax_load``; of the shipped patterns only
  search and manageportlets do) and extracts ``$("#content").html()``, so
  the *default*-layout response is the one it parses — see
  ``TestModalExtractionContract`` and pagelets/framed.py,
* CSRF ``_authenticator`` on the state-changing POSTs.
"""

import unittest

import transaction
from zExceptions import Forbidden

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.testing.zope import Browser

from .test_live_surface import classic_markup_in
from .test_live_surface import missing_frame_in


FORM_URLENCODED = "application/x-www-form-urlencoded"


class ContentActionTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        # plone.app.testing ships a chainless site (layers.py sets the
        # default chain to ""); three of these four pages exist to *drive*
        # the workflow, so the fixture needs one.
        workflow = self.portal.portal_workflow
        workflow.setDefaultChain("simple_publication_workflow")
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="actions-folder", title="Actions"
        )
        self.doc = api.content.create(
            container=self.folder, type="Document", id="probe-doc", title="Probe Doc"
        )
        transaction.commit()
        self.doc_url = self.doc.absolute_url()
        self.folder_url = self.folder.absolute_url()

    def browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        browser.addHeader("Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}")
        return browser

    def open(self, path, browser=None):
        browser = browser or self.browser()
        browser.open(path)
        return browser.contents

    def token_in(self, html):
        """The CSRF token the rendered form carries."""
        after_name = html.split('name="_authenticator"', 1)[1]
        return after_name.split('value="', 1)[1].split('"', 1)[0]

    def post(self, url, fields, browser=None, token=None):
        """POST ``fields`` (a list of ``a=b`` strings) to ``url``."""
        browser = browser or self.browser()
        data = list(fields)
        if token is not None:
            data.append(f"_authenticator={token}")
        browser.post(url, "&".join(data), FORM_URLENCODED)
        return browser

    def fresh(self, obj_id, container=None):
        """Re-read an object from the (committed) ZODB, or None."""
        transaction.begin()
        container = self.portal.unrestrictedTraverse("actions-folder")
        return container.get(obj_id)

    def assert_framed(self, html, url=""):
        self.assertEqual(classic_markup_in(html), (), f"{url} renders classic master markup")
        self.assertEqual(missing_frame_in(html), (), f"{url} did not render the pagelet frame")

    def set_debug_mode(self, value):
        from App.config import getConfiguration

        config = getConfiguration()
        old = getattr(config, "debug_mode", False)
        config.debug_mode = value
        self.addCleanup(setattr, config, "debug_mode", old)

    def assert_off_the_macro_path(self, path):
        """Frame markers alone can't tell a conversion from the bridge
        (which frames macro consumers too); the discriminator is the
        deprecation signal, which a real pagelet never emits."""
        self.set_debug_mode(True)
        browser = self.browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            self.open(path, browser=browser)
        self.assert_framed(browser.contents, path)


class TestDeleteConfirmation(ContentActionTestCase):
    """``delete_confirmation``: the stock z3c form, framed."""

    @property
    def url(self):
        return f"{self.doc_url}/delete_confirmation"

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open(self.url), self.url)

    def test_renders_off_the_macro_path(self):
        self.assert_off_the_macro_path(self.url)

    def test_asks_the_confirmation_question(self):
        html = self.open(self.url)
        self.assertIn("Do you really want to delete this item?", html)
        self.assertIn("Probe Doc", html)

    def test_folder_warning_counts_the_contained_items(self):
        html = self.open(f"{self.folder_url}/delete_confirmation")
        self.assertIn("delete this folder and all its contents", html)

    def test_form_carries_the_csrf_token(self):
        self.assertIn('name="_authenticator"', self.open(self.url))

    def test_delete_removes_the_object(self):
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        self.post(
            self.url,
            ["form.buttons.Delete=Delete"],
            browser=browser,
            token=self.token_in(html),
        )
        self.assertIsNone(self.fresh("probe-doc"), "the document was not deleted")

    def test_delete_without_the_token_is_refused(self):
        browser = self.browser()
        with self.assertRaises(Forbidden):
            self.post(self.url, ["form.buttons.Delete=Delete"], browser=browser)
        self.assertIsNotNone(self.fresh("probe-doc"))

    def test_cancel_keeps_the_object(self):
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        self.post(
            self.url,
            ["form.buttons.Cancel=Cancel"],
            browser=browser,
            token=self.token_in(html),
        )
        self.assertIsNotNone(self.fresh("probe-doc"))

    def test_body_does_not_duplicate_the_frame_content_core(self):
        # The framed body element emits #content-core (framed.py); the
        # stock template's own wrapper would be a duplicate id inside it.
        # The second copy that remains is plone.app.linkintegrity's, from
        # the delete_confirmation_info fragment it registers — foreign
        # markup this conversion does not own, and classically the *third*
        # copy on this page rather than the second.
        html = self.open(self.url)
        self.assertIn('<div id="content-core" class="element-body">', html)
        self.assertEqual(html.count('id="content-core"'), 2)


class TestObjectRename(ContentActionTestCase):
    """``object_rename``: the stock z3c form, framed."""

    @property
    def url(self):
        return f"{self.doc_url}/object_rename"

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open(self.url), self.url)

    def test_renders_off_the_macro_path(self):
        self.assert_off_the_macro_path(self.url)

    def test_shows_the_form_label_as_heading(self):
        html = self.open(self.url)
        self.assertIn("Rename item", html)

    def test_fields_are_prefilled_from_the_object(self):
        html = self.open(self.url)
        self.assertIn('value="probe-doc"', html)
        self.assertIn('value="Probe Doc"', html)

    def test_rename_changes_id_and_title(self):
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        self.post(
            self.url,
            [
                "form.widgets.new_id=renamed-doc",
                "form.widgets.new_title=Renamed Doc",
                "form.buttons.Rename=Rename",
            ],
            browser=browser,
            token=self.token_in(html),
        )
        self.assertIsNone(self.fresh("probe-doc"), "old id still present")
        renamed = self.fresh("renamed-doc")
        self.assertIsNotNone(renamed, "the document was not renamed")
        self.assertEqual(renamed.title, "Renamed Doc")

    def test_rename_without_the_token_is_refused(self):
        browser = self.browser()
        with self.assertRaises(Forbidden):
            self.post(
                self.url,
                [
                    "form.widgets.new_id=renamed-doc",
                    "form.widgets.new_title=Renamed Doc",
                    "form.buttons.Rename=Rename",
                ],
                browser=browser,
            )
        self.assertIsNotNone(self.fresh("probe-doc"))

    def test_cancel_changes_nothing(self):
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        self.post(
            self.url,
            [
                "form.widgets.new_id=renamed-doc",
                "form.widgets.new_title=Renamed Doc",
                "form.buttons.Cancel=Cancel",
            ],
            browser=browser,
            token=self.token_in(html),
        )
        self.assertIsNotNone(self.fresh("probe-doc"))

    def test_body_does_not_duplicate_the_frame_content_core(self):
        # The stock template nested TWO #content-core divs inside the slot,
        # on top of the one main_template already emitted.
        self.assertEqual(self.open(self.url).count('id="content-core"'), 1)


class TestContentStatusHistory(ContentActionTestCase):
    """``content_status_history``: the workflow "Advanced…" screen."""

    @property
    def url(self):
        return f"{self.doc_url}/content_status_history"

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open(self.url), self.url)

    def test_renders_off_the_macro_path(self):
        self.assert_off_the_macro_path(self.url)

    def test_shows_the_publishing_process_heading(self):
        self.assertIn("Publishing process", self.open(self.url))

    def test_offers_the_available_transitions(self):
        html = self.open(self.url)
        self.assertIn('name="workflow_action"', html)
        self.assertIn('value="publish"', html)

    def test_renders_the_two_date_widgets(self):
        html = self.open(self.url)
        self.assertIn("form.widgets.effective_date", html)
        self.assertIn("form.widgets.expiration_date", html)

    def test_keeps_the_no_store_cache_header(self):
        # The classic template set this from its top_slot; a converted page
        # has no slots, so the view owns it (content_actions.py).
        browser = self.browser()
        browser.open(self.url)
        self.assertIn("no-store", browser.headers.get("Cache-Control", ""))

    def test_transition_publishes_the_document(self):
        self.assertEqual(api.content.get_state(self.doc), "private")
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        path = "/".join(self.doc.getPhysicalPath())
        self.post(
            self.url,
            [
                "form.submitted=1",
                "workflow_action=publish",
                f"paths:list={path}",
                "form.button.Publish=Save",
            ],
            browser=browser,
            token=self.token_in(html),
        )
        transaction.begin()
        self.assertEqual(api.content.get_state(self.doc), "published")

    def test_transition_without_the_token_is_refused(self):
        browser = self.browser()
        path = "/".join(self.doc.getPhysicalPath())
        with self.assertRaises(Forbidden):
            self.post(
                self.url,
                [
                    "form.submitted=1",
                    "workflow_action=publish",
                    f"paths:list={path}",
                    "form.button.Publish=Save",
                ],
                browser=browser,
            )
        transaction.begin()
        self.assertEqual(api.content.get_state(self.doc), "private")

    def test_missing_transition_reports_the_error_framed(self):
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        path = "/".join(self.doc.getPhysicalPath())
        self.post(
            self.url,
            ["form.submitted=1", f"paths:list={path}", "form.button.Publish=Save"],
            browser=browser,
            token=self.token_in(html),
        )
        self.assertIn("You must select a publishing action.", browser.contents)
        self.assert_framed(browser.contents, "content_status_history (error)")

    def test_body_does_not_duplicate_the_frame_content_core(self):
        self.assertEqual(self.open(self.url).count('id="content-core"'), 1)

    def test_dead_jscalendar_resources_are_gone(self):
        # The classic javascript_head_slot pulled two files from a
        # portal_skins folder Plone 6 no longer ships — 404s on every
        # render. Nothing replaces them: the date widgets are patterns.
        self.assertNotIn("jscalendar", self.open(self.url))


class TestHistoryView(ContentActionTestCase):
    """``@@historyview``: the workflow/version history entry page."""

    @property
    def url(self):
        return f"{self.doc_url}/@@historyview"

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open(self.url), self.url)

    def test_renders_off_the_macro_path(self):
        self.assert_off_the_macro_path(self.url)

    def test_shows_the_history_heading_and_entries(self):
        html = self.open(self.url)
        self.assertIn("History", html)
        # @@contenthistory's own markup, rendered into the body
        self.assertIn('id="history-list"', html)
        self.assertIn("historyRecord", html)

    def test_body_does_not_duplicate_the_frame_content_core(self):
        self.assertEqual(self.open(self.url).count('id="content-core"'), 1)


class TestModalExtractionContract(ContentActionTestCase):
    """What ``pat-plone-modal`` needs from a converted page.

    The modal fetches the link's plain ``href`` — the default layout, not
    the ajax fragment — and then, from that document: takes ``h1:first`` as
    the modal title (removing it from the content), lifts ``.portalMessage``
    into the prepend area, sets the modal body to ``$("#content").html()``
    and clones ``.formControls > input[type=submit]`` into the button bar.
    ``delete``, ``rename`` (CMFPlone actions.xml) and the workflow menu's
    "Advanced…" (plone.app.contentmenu) all open this way.
    """

    #: (page, a marker that must survive extraction into the modal body)
    MODAL_PAGES = (
        ("delete_confirmation", "form.buttons.Delete"),
        ("object_rename", "form.widgets.new_id"),
        ("content_status_history", 'name="workflow_action"'),
    )

    def extracted(self, html):
        """What ``$("#content").html()`` would hand the modal."""
        self.assertIn('<article id="content">', html, "no #content: the modal body is empty")
        return html.split('<article id="content">', 1)[1].split("</article>", 1)[0]

    def test_content_is_the_modal_extraction_point(self):
        for page, marker in self.MODAL_PAGES:
            with self.subTest(page=page):
                self.assertIn(marker, self.extracted(self.open(f"{self.doc_url}/{page}")))

    def test_page_heading_is_the_first_h1(self):
        # titleSelector is "h1:first" over the whole document — the frame
        # must not put an h1 above the body, or the modal title (which is
        # *removed* from the content) would be the wrong element.
        for page, _marker in self.MODAL_PAGES:
            with self.subTest(page=page):
                html = self.open(f"{self.doc_url}/{page}")
                self.assertIn("<h1", html)
                self.assertLess(
                    html.index('<article id="content">'),
                    html.index("<h1"),
                    "an h1 renders above #content — it would hijack the modal title",
                )

    def test_submit_buttons_are_in_form_controls(self):
        for page, _marker in self.MODAL_PAGES:
            with self.subTest(page=page):
                self.assertIn("formControls", self.open(f"{self.doc_url}/{page}"))

    def test_status_messages_stay_outside_content(self):
        # prependContent (".portalMessage") is lifted separately; inside
        # #content it would be swallowed by the modal body instead.
        html = self.open(f"{self.doc_url}/delete_confirmation")
        self.assertNotIn("portalMessage", self.extracted(html))

    def test_ajax_layout_does_not_duplicate_the_content_id(self):
        # AjaxRegion supplies #content itself for the fixed fragment
        # element set; the body element must not add a second one.
        for page, marker in self.MODAL_PAGES:
            with self.subTest(page=page):
                html = self.open(f"{self.doc_url}/{page}?ajax_load=1")
                self.assertEqual(html.count('id="content"'), 1)
                self.assertIn(marker, html)
                self.assertIn("pagelet-layout-ajax", html)
