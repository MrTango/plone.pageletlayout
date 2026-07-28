"""Live-surface walk: no page in the probe corpus renders classic chrome.

The verification harness' first meter (classic-coverage map, ticket 04).
The corpus is the live-verified probe table from the charting plan
(.scratch/classic-coverage/plan.md): the pages that used to render the
classic Barceloneta frame, plus the pagelet-native landmarks. Each URL is
fetched through the publisher as the site owner and must come back with
the pagelet frame and **zero** classic master markup
(``#visual-portal-wrapper`` / ``#portal-column-content``).

Extend the corpus as views convert (map tickets 05-10) — one line per URL.
The static ratchet (test_static_ratchet.py) is the companion meter for
"nothing *new* renders via the macro path".
"""

import unittest

import transaction

from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.app.testing import setRoles
from plone.testing.zope import Browser

from plone.pageletlayout.testing import FUNCTIONAL_TESTING


#: Classic main_template output markers — present only in Barceloneta
#: master markup, never in the pagelet frame.
CLASSIC_MARKERS = ("visual-portal-wrapper", "portal-column-content")

#: Pagelet frame markers — every page on the layer must carry them.
FRAME_MARKERS = ('class="plone-layout"', "element-body")

#: Probe URLs relative to the portal root (charting plan corpus; the
#: login/password family block extends it per ticket 06 — the pwreset
#: templates are invisible to the registry walk, so this corpus is their
#: only meter; ``passwordreset`` without a key renders the invalid branch).
PORTAL_PROBES = (
    "",
    "folder_contents",
    "@@search",
    # A real query renders the whole results machinery, not just the empty
    # form — the half of @@search ticket 07 converted (results, batch nav).
    "@@search?SearchableText=Probe",
    "sitemap",
    "contact-info",
    "login",
    "@@login-help",
    "logged-out",
    "insufficient-privileges",
    "mail_password_form",
    "mail_password_response",
    "passwordreset",
    "initial-login-password-change",
    "forced-password-change",
    "portal_password_reset/explainPWResetTool",
    "@@overview-controlpanel",
    "@@usergroup-userprefs",
    "@@personal-information",
)

#: Probe URLs relative to a content object.
DOCUMENT_PROBES = (
    "edit",
    "@@sharing",
    # A search term renders the half of @@sharing ticket 08 had to keep
    # working through the conversion: the matrix grown by a principal
    # search, not just the stored role settings.
    "@@sharing?search_term=admin",
    "@@historyview",
    # The content actions (ticket 09). All three are also modal consumers,
    # which parse this very (default-layout) response — see
    # tests/test_content_actions.py::TestModalExtractionContract.
    "delete_confirmation",
    "object_rename",
    "content_status_history",
    # The sitemap is registered for="*" — on a content context it renders the
    # current-item branch of the tree (ticket 10).
    "sitemap",
)


def classic_markup_in(html):
    """The classic markers present in ``html`` (empty tuple == clean)."""
    return tuple(marker for marker in CLASSIC_MARKERS if marker in html)


def missing_frame_in(html):
    """The pagelet-frame markers absent from ``html`` (empty == framed)."""
    return tuple(marker for marker in FRAME_MARKERS if marker not in html)


class TestLiveSurface(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.doc = api.content.create(
            container=self.portal,
            type="Document",
            id="probe-page",
            title="Probe Page",
        )
        transaction.commit()
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
        )

    def assert_pagelet_surface(self, base_url, probes):
        for probe in probes:
            url = f"{base_url}/{probe}" if probe else base_url
            with self.subTest(url=url):
                self.browser.open(url)
                html = self.browser.contents
                self.assertEqual(
                    classic_markup_in(html),
                    (),
                    f"{url} renders classic master markup",
                )
                self.assertEqual(
                    missing_frame_in(html),
                    (),
                    f"{url} did not render the pagelet frame",
                )

    def test_portal_surface_is_classic_free(self):
        self.assert_pagelet_surface(self.portal.absolute_url(), PORTAL_PROBES)

    def test_document_surface_is_classic_free(self):
        self.assert_pagelet_surface(self.doc.absolute_url(), DOCUMENT_PROBES)


class TestMarkersHaveTeeth(unittest.TestCase):
    """Planted classic markup must be caught (the meter is not vacuous)."""

    def test_classic_markup_detected(self):
        html = '<body><div id="visual-portal-wrapper"><div id="portal-column-content">'
        self.assertEqual(
            classic_markup_in(html),
            ("visual-portal-wrapper", "portal-column-content"),
        )

    def test_frameless_page_detected(self):
        self.assertEqual(missing_frame_in("<body>bare</body>"), FRAME_MARKERS)
