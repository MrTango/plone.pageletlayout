"""The login/password family as pagelets (classic-coverage map, ticket 06).

Each view of CMFPlone's browser/login package renders in the pagelet frame
on the pageletlayout layer — no classic master markup, stock control flow
(redirects, POST handling, pwreset template dispatch) untouched. The family
converts via the FramedPage mechanism: the stock view classes are reused,
only their class-bound templates are swapped for framed body templates.
"""

import unittest

import transaction

from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.testing.zope import Browser

from .test_live_surface import classic_markup_in
from .test_live_surface import missing_frame_in


class LoginFamilyTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()

    def anonymous_browser(self):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        return browser

    def admin_browser(self):
        browser = self.anonymous_browser()
        browser.addHeader(
            "Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
        )
        return browser

    def assert_framed(self, html, url=""):
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


class TestLoginPage(LoginFamilyTestCase):
    """@@login renders framed and the login round-trip works."""

    def test_login_renders_in_pagelet_frame(self):
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/login")
        self.assert_framed(browser.contents, "login")

    def test_login_renders_off_the_macro_path(self):
        # The bridge frames macro consumers too, so frame markers alone
        # can't tell a conversion from the bridge: the discriminator is
        # the deprecation signal, which a real pagelet never emits — even
        # in development mode, where every macro render logs a WARNING.
        self.set_debug_mode(True)
        browser = self.anonymous_browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            browser.open(f"{self.portal_url}/login")

    def test_login_page_has_the_form(self):
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/login")
        self.assertIn('name="__ac_name"', browser.contents)
        self.assertIn('name="__ac_password"', browser.contents)

    def test_login_roundtrip_redirects_to_came_from(self):
        browser = self.anonymous_browser()
        browser.followRedirects = False
        target = f"{self.portal_url}/sitemap"
        browser.open(f"{self.portal_url}/login?came_from={target}")
        browser.getControl(name="__ac_name").value = TEST_USER_NAME
        browser.getControl(name="__ac_password").value = TEST_USER_PASSWORD
        browser.getControl(name="buttons.login").click()
        self.assertEqual(browser.headers["status"].split()[0], "302")
        self.assertEqual(browser.headers["location"], target)

    def test_failed_login_rerenders_framed_with_status_message(self):
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/login")
        browser.getControl(name="__ac_name").value = TEST_USER_NAME
        browser.getControl(name="__ac_password").value = "wrong-password"
        browser.getControl(name="buttons.login").click()
        self.assert_framed(browser.contents, "login POST")
        self.assertIn("Login failed", browser.contents)

    def test_login_heading_is_the_form_label_not_the_portal_title(self):
        # The contentheader element is shadowed empty for framed pages —
        # the body template carries the page's own heading, so the portal
        # title must not appear as the page h1.
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/login")
        html = browser.contents
        self.assertNotIn(
            f'<h1 class="documentFirstHeading">{self.portal.Title()}</h1>', html
        )
        self.assertIn("Log in", html)


class TestLoginAjaxFragment(LoginFamilyTestCase):
    """Modal consumers (stock login opens in a pat-plone-modal) get the
    ajax fragment contract, like every pagelet page."""

    def test_modal_extraction_point_is_in_the_default_layout(self):
        # Ticket 09's correction to this class' original premise:
        # pat-plone-modal fetches the link's plain ``href`` and never
        # appends ``ajax_load`` (of the shipped patterns only search and
        # manageportlets do), then extracts ``$("#content").html()``. The
        # ``login`` action carries a ``modal`` property (CMFPlone's
        # actions.xml), so the DEFAULT-layout response is what the modal
        # parses — the framed body element carries the id (framed.py).
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/login")
        html = browser.contents
        self.assertIn('<article id="content">', html)
        extracted = html.split('<article id="content">', 1)[1].split("</article>", 1)[0]
        self.assertIn('name="__ac_name"', extracted, "empty modal: form outside")
        self.assertIn('id="content-core"', extracted)

    def test_ajax_load_returns_the_fragment_document(self):
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/login?ajax_load=1")
        html = browser.contents
        self.assertIn('name="__ac_name"', html)
        self.assertNotIn("<title>", html, "ajax fragment must not re-plumb the head")
        self.assertIn("pagelet-layout-ajax", html)


class TestPasswordReset(LoginFamilyTestCase):
    """The @@passwordreset flow: the stock four-template dispatch, framed."""

    def _reset_key(self):
        from plone.app.testing import TEST_USER_ID

        key = self.portal.portal_password_reset.requestReset(TEST_USER_ID)[
            "randomstring"
        ]
        transaction.commit()
        return key

    def test_reset_form_renders_framed_off_the_macro_path(self):
        key = self._reset_key()
        self.set_debug_mode(True)
        browser = self.anonymous_browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            browser.open(f"{self.portal_url}/passwordreset/{key}")
        self.assert_framed(browser.contents, "passwordreset")
        self.assertIn('name="pwreset_action"', browser.contents)

    def test_invalid_key_renders_the_invalid_page_framed(self):
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/passwordreset/not-a-real-key")
        self.assert_framed(browser.contents, "passwordreset (invalid)")
        self.assertIn("invalid request", browser.contents)

    def test_posting_a_new_password_finishes_framed(self):
        from plone import api
        from plone.app.testing import TEST_USER_NAME

        # Autologin redirects past the finish page — turn it off so the
        # stock dispatch actually renders ``finish``.
        api.portal.set_registry_record(
            "plone.autologin_after_password_reset", False
        )
        key = self._reset_key()
        browser = self.anonymous_browser()
        browser.open(f"{self.portal_url}/passwordreset/{key}")
        browser.getControl(name="userid").value = TEST_USER_NAME
        browser.getControl(name="password").value = "new-secret-Passw0rd"
        browser.getControl(name="password2").value = "new-secret-Passw0rd"
        browser.getControl(name="form.submitted").value = "1"
        self.submit_form(browser, name="pwreset_action")
        self.assert_framed(browser.contents, "passwordreset (finish)")
        self.assertIn("Password set", browser.contents)

    def submit_form(self, browser, name):
        form = browser.getForm(name=name)
        form.submit()


class TestPasswordChangePages(LoginFamilyTestCase):
    """forced / initial password change render framed for a member."""

    def member_browser(self):
        from plone.app.testing import TEST_USER_NAME
        from plone.app.testing import TEST_USER_PASSWORD

        browser = self.anonymous_browser()
        browser.addHeader(
            "Authorization", f"Basic {TEST_USER_NAME}:{TEST_USER_PASSWORD}"
        )
        return browser

    def test_password_change_pages_render_framed_off_the_macro_path(self):
        self.set_debug_mode(True)
        for page, heading in (
            ("initial-login-password-change", "Welcome!"),
            ("forced-password-change", "Time to change your password!"),
        ):
            with self.subTest(page=page):
                browser = self.member_browser()
                with self.assertNoLogs(
                    "plone.pageletlayout.bridge", level="INFO"
                ):
                    browser.open(f"{self.portal_url}/{page}")
                self.assert_framed(browser.contents, page)
                self.assertIn(heading, browser.contents)
                self.assertIn("current_password", browser.contents)


class TestExplainPWResetTool(LoginFamilyTestCase):
    """The reset tool's ZMI explain page renders framed on the tool."""

    def test_renders_framed_off_the_macro_path(self):
        self.set_debug_mode(True)
        browser = self.admin_browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            browser.open(
                f"{self.portal_url}/portal_password_reset/explainPWResetTool"
            )
        self.assert_framed(browser.contents, "explainPWResetTool")
        self.assertIn("Password Reset Tool", browser.contents)


class TestSimplePages(LoginFamilyTestCase):
    """The single-template members render framed, off the macro path."""

    #: (url, must-contain content marker, authenticated?)
    PAGES = (
        ("logged-out", "id=\"content-core\"", True),
        ("insufficient-privileges", "Insufficient Privileges", False),
        ("@@login-help", "form", False),
        ("mail_password_form", 'name="mail_password"', False),
        ("mail_password_response", "Password reset confirmation sent", False),
    )

    def test_pages_render_framed_off_the_macro_path(self):
        self.set_debug_mode(True)
        for page, marker, authenticated in self.PAGES:
            with self.subTest(page=page):
                browser = (
                    self.admin_browser() if authenticated
                    else self.anonymous_browser()
                )
                with self.assertNoLogs(
                    "plone.pageletlayout.bridge", level="INFO"
                ):
                    browser.open(f"{self.portal_url}/{page}")
                self.assert_framed(browser.contents, page)
                self.assertIn(marker, browser.contents)
