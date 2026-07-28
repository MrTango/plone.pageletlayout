"""@@sharing as a pagelet (classic-coverage map, ticket 08).

plone.app.workflow's sharing page renders in the pagelet frame on the
pageletlayout layer, with the stock ``SharingView`` class still doing every
bit of the work — role matrix, principal search, inheritance toggle, the
CSRF-guarded save. Unlike ``@@search`` this is a *writing* page, so the
cases below are round-trips: the assertion is that the change landed in the
ZODB, not that some markup appeared.

The ticket flagged three things to watch, one case group each:

* the page is a plain (non-z3c) self-posting form with ``_authenticator`` —
  the guards must still bite after the conversion,
* the principal-search behaviour, including ``@@updateSharingInfo``, the
  JSON fragment built from a METAL macro *inside* the page template,
* the role matrix must reuse the already-styled ``.table`` hooks.
"""

import json
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


#: The principal every role round-trip below shares with.
SHAREE = "sharee"

FORM_URLENCODED = "application/x-www-form-urlencoded"


class SharingTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="shared-folder", title="Shared"
        )
        self.doc = api.content.create(
            container=self.folder, type="Document", id="shared-doc", title="Shared Doc"
        )
        # No password: the sharee is only ever *shared with*, never logged
        # in as — plone.api generates one.
        api.user.create(username=SHAREE, email="sharee@example.com")
        transaction.commit()
        self.doc_url = self.doc.absolute_url()

    def browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        browser.addHeader(
            "Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
        )
        return browser

    def open_sharing(self, query="", browser=None):
        """Open ``@@sharing`` on the probe document; return the response."""
        browser = browser or self.browser()
        url = f"{self.doc_url}/@@sharing"
        if query:
            url = f"{url}?{query}"
        browser.open(url)
        return browser.contents

    def token_in(self, html):
        """The CSRF token the rendered form carries."""
        after_name = html.split('name="_authenticator"', 1)[1]
        return after_name.split('value="', 1)[1].split('"', 1)[0]

    def save(self, fields, browser=None, authenticator=True):
        """POST the sharing form's Save button with ``fields``.

        Returns the browser, so callers can inspect the re-rendered page.
        """
        browser = browser or self.browser()
        html = self.open_sharing(browser=browser)
        data = ["form.submitted:boolean=True", "form.button.Save=Save"] + list(fields)
        if authenticator:
            data.append(f"_authenticator={self.token_in(html)}")
        browser.post(f"{self.doc_url}/@@sharing", "&".join(data), FORM_URLENCODED)
        return browser

    def local_roles(self):
        """The probe document's local roles for the sharee, freshly read."""
        transaction.begin()
        return set(self.doc.get_local_roles_for_userid(userid=SHAREE))

    def assert_framed(self, html, url="@@sharing"):
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


class TestSharingPage(SharingTestCase):
    """The page renders framed, off the macro path, with its heading."""

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open_sharing())

    def test_renders_off_the_macro_path(self):
        # Frame markers alone can't tell a conversion from the bridge (which
        # frames macro consumers too); the discriminator is the deprecation
        # signal, which a real pagelet never emits.
        self.set_debug_mode(True)
        browser = self.browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            self.open_sharing(browser=browser)
        self.assert_framed(browser.contents)

    def test_heading_names_the_shared_item(self):
        html = self.open_sharing()
        self.assertIn("Sharing for", html)
        self.assertIn("Shared Doc", html)

    def test_content_core_is_not_duplicated(self):
        # The framed body element owns #content-core; the stock template
        # emitted its own, which would be a duplicate id inside the frame.
        self.assertEqual(self.open_sharing().count('id="content-core"'), 1)

    def test_default_page_hint_renders_for_a_default_page(self):
        self.folder.setDefaultPage("shared-doc")
        transaction.commit()
        html = self.open_sharing()
        self.assertIn("default view in a container", html)
        self.assertIn(f"{self.folder.absolute_url()}/sharing", html)

    def test_no_default_page_hint_otherwise(self):
        # Proves the case above is not vacuous.
        self.assertNotIn("default view in a container", self.open_sharing())


class TestSharingRoleMatrix(SharingTestCase):
    """The matrix reuses the site's already-styled ``.table`` hooks, and
    keeps every id the page's own markup contract names."""

    #: Ids and classes the page is addressed by (stock markup contract).
    HOOKS = (
        'id="user-group-sharing"',
        'id="user-group-sharing-container"',
        'id="user-group-sharing-head"',
        'id="user-group-sharing-settings"',
        'id="sharing-user-group-search"',
        'id="sharing-search-button"',
        'id="sharing-save-button"',
        'id="field-inherit"',
        'id="inherit"',
        "listingCheckbox",
    )

    def test_every_markup_hook_survives_the_conversion(self):
        html = self.open_sharing()
        for hook in self.HOOKS:
            with self.subTest(hook=hook):
                self.assertIn(hook, html)

    def test_matrix_uses_the_styled_table_hooks(self):
        html = self.open_sharing()
        self.assertIn('class="table table-bordered table-striped"', html)

    def test_logged_in_users_row_is_always_present(self):
        # The AuthenticatedUsers virtual group is sticky — the matrix is
        # never empty, so the table always has something to render.
        self.assertIn("AuthenticatedUsers", self.open_sharing())

    def test_managed_roles_are_column_headers(self):
        html = self.open_sharing()
        for role in ("Can view", "Can edit"):
            with self.subTest(role=role):
                self.assertIn(role, html)


class TestSharingSave(SharingTestCase):
    """Round-trips: what the form posts actually lands in the ZODB."""

    def test_granting_a_role_persists(self):
        self.save(
            [
                f"entries.id:records={SHAREE}",
                "entries.type:records=user",
                "entries.role_Reader:records=True",
                "inherit:boolean=True",
            ]
        )
        self.assertIn("Reader", self.local_roles())

    def test_revoking_a_role_persists(self):
        self.doc.manage_setLocalRoles(SHAREE, ["Reader"])
        transaction.commit()
        self.save(
            [
                f"entries.id:records={SHAREE}",
                "entries.type:records=user",
                "inherit:boolean=True",
            ]
        )
        self.assertNotIn("Reader", self.local_roles())

    def test_save_confirms_with_a_status_message(self):
        browser = self.save(
            [
                f"entries.id:records={SHAREE}",
                "entries.type:records=user",
                "entries.role_Reader:records=True",
                "inherit:boolean=True",
            ]
        )
        # The frame's statusmessages element renders it — the classic
        # global_statusmessage slot has no counterpart in a pagelet.
        self.assertIn("Changes saved.", browser.contents)
        self.assert_framed(browser.contents)

    def test_granted_role_shows_as_checked_afterwards(self):
        self.save(
            [
                f"entries.id:records={SHAREE}",
                "entries.type:records=user",
                "entries.role_Reader:records=True",
                "inherit:boolean=True",
            ]
        )
        html = self.open_sharing()
        row = html.split(f'title="{SHAREE}"', 1)[1].split("</tr>", 1)[0]
        reader_input = row.split('name="entries.role_Reader:records"', 1)[1].split(
            ">", 1
        )[0]
        self.assertIn("checked", reader_input)

    def test_cancel_redirects_back_to_the_item(self):
        browser = self.browser()
        html = self.open_sharing(browser=browser)
        browser.post(
            f"{self.doc_url}/@@sharing",
            "&".join(
                [
                    "form.submitted:boolean=True",
                    "form.button.Cancel=Cancel",
                    f"_authenticator={self.token_in(html)}",
                ]
            ),
            FORM_URLENCODED,
        )
        # plone_context_state.view_url() — the item itself for a type that
        # is not in plone.types_use_view_action_in_listings.
        self.assertEqual(browser.url, self.doc_url)


class TestSharingInheritance(SharingTestCase):
    """The inherit checkbox drives ``__ac_local_roles_block__``."""

    def blocked(self):
        transaction.begin()
        return bool(getattr(self.doc, "__ac_local_roles_block__", False))

    def test_unchecking_inherit_blocks_acquisition(self):
        self.save([])  # no inherit field == unchecked checkbox
        self.assertTrue(self.blocked())

    def test_rechecking_inherit_restores_acquisition(self):
        self.save([])
        self.assertTrue(self.blocked())
        self.save(["inherit:boolean=True"])
        self.assertFalse(self.blocked())

    def test_checkbox_reflects_the_stored_state(self):
        self.save([])
        field = self.open_sharing().split('id="inherit"', 1)[1].split(">", 1)[0]
        self.assertNotIn("checked", field)


class TestSharingCSRF(SharingTestCase):
    """The stock guards — POST-only and ``_authenticator`` — still bite."""

    def test_save_without_authenticator_is_forbidden(self):
        with self.assertRaises(Forbidden):
            self.save(
                [
                    f"entries.id:records={SHAREE}",
                    "entries.type:records=user",
                    "entries.role_Reader:records=True",
                ],
                authenticator=False,
            )

    def test_save_over_get_is_forbidden(self):
        with self.assertRaises(Forbidden):
            self.open_sharing(
                f"form.submitted:boolean=True&form.button.Save=Save"
                f"&entries.id:records={SHAREE}&entries.type:records=user"
            )

    def test_rejected_save_changes_nothing(self):
        with self.assertRaises(Forbidden):
            self.save(
                [
                    f"entries.id:records={SHAREE}",
                    "entries.type:records=user",
                    "entries.role_Reader:records=True",
                ],
                authenticator=False,
            )
        self.assertEqual(self.local_roles(), set())

    def test_the_form_carries_a_token(self):
        self.assertIn('name="_authenticator"', self.open_sharing())


class TestSharingPrincipalSearch(SharingTestCase):
    """``search_term`` adds matching principals to the matrix."""

    def test_user_search_lists_the_match(self):
        html = self.open_sharing(f"search_term={SHAREE}")
        self.assertIn(SHAREE, html.split('id="user-group-sharing"', 1)[1])

    def test_user_search_omits_non_matches(self):
        self.assertNotIn(
            SHAREE, self.open_sharing("search_term=nobodymatchesthis")
        )

    def test_group_search_lists_the_match(self):
        api.group.create(groupname="sharing-probe-group", title="Sharing Probe Group")
        transaction.commit()
        html = self.open_sharing("search_term=sharing-probe-group")
        self.assertIn("Sharing Probe Group", html)

    def test_search_result_can_be_granted_a_role(self):
        # The whole point of searching: the found principal's row posts back
        # like any other, so the grant round-trips in one step.
        browser = self.browser()
        html = self.open_sharing(f"search_term={SHAREE}", browser=browser)
        browser.post(
            f"{self.doc_url}/@@sharing",
            "&".join(
                [
                    "form.submitted:boolean=True",
                    "form.button.Save=Save",
                    f"entries.id:records={SHAREE}",
                    "entries.type:records=user",
                    "entries.role_Reader:records=True",
                    "inherit:boolean=True",
                    f"_authenticator={self.token_in(html)}",
                ]
            ),
            FORM_URLENCODED,
        )
        self.assertIn("Reader", self.local_roles())


class TestSharingUpdateSharingInfo(SharingTestCase):
    """``@@updateSharingInfo``: the JSON fragment built from the page
    template's ``user-group-sharing`` macro.

    Stock is **broken** in Plone 6.2 — the macro reads ``icons`` (and
    ``portal_url``/``can_view_groups``) from main_template's globals, which
    the macro wrapper does not provide, so every call raises ``NameError``.
    Converting the page moves those defines onto the macro itself, which
    makes the fragment self-contained and the endpoint work.
    """

    def fragment(self, query=""):
        browser = self.browser()
        url = f"{self.doc_url}/@@updateSharingInfo"
        if query:
            url = f"{url}?{query}"
        browser.open(url)
        return json.loads(browser.contents)

    def test_returns_json_with_body_and_messages(self):
        payload = self.fragment()
        self.assertEqual(sorted(payload), ["body", "messages"])

    def test_body_is_the_role_matrix(self):
        body = self.fragment()["body"]
        self.assertIn('id="user-group-sharing"', body)
        self.assertIn("AuthenticatedUsers", body)

    def test_body_is_a_fragment_not_a_page(self):
        # It replaces the table in place, so it must carry no frame.
        self.assertNotIn("plone-layout", self.fragment()["body"])

    def test_fragment_reflects_a_search_term(self):
        self.assertIn(SHAREE, self.fragment(f"search_term={SHAREE}")["body"])


class TestSharingAjaxLayout(SharingTestCase):
    """``ajax_load=1`` selects the ajax frame, like every framed page."""

    def test_ajax_load_selects_the_ajax_layout(self):
        self.assertIn("pagelet-layout-ajax", self.open_sharing("ajax_load=1"))

    def test_fragment_does_not_replumb_the_head(self):
        # Read the head, not the whole document: the matrix's inline SVG
        # icons carry <title> elements of their own (accessible names).
        head = self.open_sharing("ajax_load=1").split("</head>", 1)[0]
        self.assertNotIn("<title>", head)
        self.assertNotIn("<link", head)

    def test_fragment_still_carries_the_matrix(self):
        self.assertIn('id="user-group-sharing"', self.open_sharing("ajax_load=1"))


class TestSharingNoUtilitySoup(SharingTestCase):
    """The rendered page is part of the markup contract: layout comes from
    the ``plone-*`` primitives, never Bootstrap spacing/flex utilities
    (design principle #3), same discipline as ticket 07's search page."""

    def sharing_body_markup(self):
        """The converted body only — chrome is not this ticket's surface.

        Cut from the framed body element's ``#content-core`` to the next
        layout element (the copyright row, whose Barceloneta ``.row/.col``
        shell is chrome and deliberately out of the lint's scope).
        """
        html = self.open_sharing()
        return html.split('id="content-core"', 1)[1].split("element-copyright", 1)[0]

    def test_no_forbidden_utilities_in_the_rendered_body(self):
        from .test_template_lint import forbidden_in_markup

        self.assertEqual(forbidden_in_markup(self.sharing_body_markup()), [])

    def test_primitives_carry_the_layout(self):
        self.assertIn("plone-stack", self.sharing_body_markup())
