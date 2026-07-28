"""Functional tests for the main_template compatibility bridge.

The bridge overrides the ``main_template`` view on the pageletlayout layer
with a pagelet-frame template exposing a compatible ``master`` macro, so
every unconverted classic consumer renders pagelet chrome untouched. The
probe corpus below is the live-verified classic surface from the charting
plan (.scratch/classic-coverage/plan.md): each page used to render the
classic Barceloneta frame (``#visual-portal-wrapper``); with the bridge it
must render the pagelet frame instead.
"""

import unittest

import transaction

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


class BridgeTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def _render(self, context, view_name):
        return context.restrictedTraverse(view_name)()

    def assert_pagelet_chrome(self, html, page):
        # pagelet frame markers in, classic master markers out
        self.assertIn('class="plone-layout"', html, f"{page}: no pagelet frame")
        self.assertIn("element-body", html, f"{page}: no body region")
        self.assertNotIn(
            "visual-portal-wrapper", html, f"{page}: classic master markup"
        )
        self.assertNotIn(
            "portal-column-content", html, f"{page}: classic master markup"
        )
        # htmltitle owns the single head <title> (no duplicate from head
        # slots or meta providers; SVG icon <title>s in the body don't count)
        head = html.split("</head>", 1)[0]
        self.assertEqual(
            head.count("<title"), 1, f"{page}: duplicated <title> in head"
        )


class TestBridgeChrome(BridgeTestCase):
    """The probe corpus renders the pagelet frame via the bridged macro."""

    def test_accessibility_info_renders_pagelet_chrome(self):
        # a steady-state long-tail page (stays on the bridge forever; the
        # login family it replaced here converted in ticket 06)
        html = self._render(self.portal, "accessibility-info")
        self.assert_pagelet_chrome(html, "accessibility-info")

    def test_controlpanel_overview_renders_pagelet_chrome(self):
        # binds BOTH bridged macros: prefs_main_template wraps master and
        # the nested content macro
        html = self._render(self.portal, "@@overview-controlpanel")
        self.assert_pagelet_chrome(html, "@@overview-controlpanel")

    def test_controlpanel_form_wrapper_renders_pagelet_chrome(self):
        # a ControlPanelFormWrapper panel (S2): controlpanel_layout.pt →
        # prefs_main_template → bridged master
        html = self._render(self.portal, "@@mail-controlpanel")
        self.assert_pagelet_chrome(html, "@@mail-controlpanel")


class TestBridgeChromeOnContent(BridgeTestCase):
    """Corpus members that need a content object."""

    def setUp(self):
        super().setUp()
        self.doc = api.content.create(
            container=self.portal,
            type="Document",
            id="a-page",
            title="A Page",
        )
        transaction.commit()

    def test_body_slot_page_renders_pagelet_chrome(self):
        # manage-assignments.pt fills the ``body`` slot (not content-core)
        # — a content-rules admin screen, steady-state long tail. @@sharing
        # stood here until ticket 08 converted it (and this test kept
        # passing while silently no longer exercising the bridge).
        html = self._render(self.doc, "@@manage-content-rules")
        self.assert_pagelet_chrome(html, "@@manage-content-rules")

    def test_content_core_page_renders_pagelet_chrome(self):
        # document.pt fills ``content-core``. An S5 dormant fallback (the
        # FTI default is pagelet_view), so it is never converted out from
        # under this test — @@historyview stood here until ticket 09.
        html = self._render(self.doc, "@@document_view")
        self.assert_pagelet_chrome(html, "@@document_view")

    def test_head_slot_lands_in_head(self):
        # CMFEditions' versions_history_form fills head_slot with a
        # stylesheet link — a steady-state long-tail page, so this example
        # cannot be converted out from under the test (@@search stood here
        # until ticket 07 converted it).
        html = self._render(self.doc, "versions_history_form")
        head = html.split("</head>", 1)[0]
        self.assertIn(
            'href="compare.css"', head, "head_slot content missing from <head>"
        )


class TestBridgeSlots(BridgeTestCase):
    """The classic slot contract keeps working through the bridged macro."""

    def test_slot_content_lands_in_body_region(self):
        # accessibility-info.pt fills the ``main`` slot; its content must
        # render inside the element-body wrapper, before the footer elements
        html = self._render(self.portal, "accessibility-info")
        body_region = html.index('class="element-body"')
        slot_content = html.index("https://www.w3.org/TR/WCAG20/")
        footer = html.index("element-copyright")
        self.assertTrue(
            body_region < slot_content < footer,
            "main-slot content did not land inside the element-body region",
        )

    def test_theme_disabled_header_set(self):
        # Diazo off, like PageletPage.__call__ (Clara's expression-gated
        # bundle keys on this header)
        self._render(self.portal, "accessibility-info")
        self.assertEqual(
            self.request.response.getHeader("X-Theme-Disabled"), "1"
        )


class TestMacroDeprecationWarning(BridgeTestCase):
    """Rendering via the bridged macro path emits the deprecation signal.

    Macros keep working on the bridge forever, but must not spread: in
    development mode every macro-path render logs a WARNING naming the
    consumer template and pointing at the porting docs; in production the
    same message is logged once per consumer per process at INFO.
    A converted pagelet page never touches the macro path and stays silent.
    """

    LOGGER = "plone.pageletlayout.bridge"

    def _set_debug(self, value):
        from App.config import getConfiguration

        config = getConfiguration()
        old = getattr(config, "debug_mode", False)
        config.debug_mode = value
        self.addCleanup(setattr, config, "debug_mode", old)

    def test_dev_mode_macro_render_warns_with_name_and_doc_pointer(self):
        self._set_debug(True)
        with self.assertLogs(self.LOGGER, level="WARNING") as captured:
            self._render(self.portal, "accessibility-info")
        text = "\n".join(captured.output)
        self.assertIn(
            "accessibility-info.pt", text, "warning does not name the consumer"
        )
        self.assertIn(
            "porting-main-template",
            text,
            "warning does not point at the porting docs",
        )

    def test_pagelet_page_emits_nothing(self):
        # a converted page renders the pagelet frame directly — no macro
        # path, no signal, even in development mode
        self._set_debug(True)
        doc = api.content.create(
            container=self.portal,
            type="Document",
            id="converted-page",
            title="Converted Page",
        )
        transaction.commit()
        with self.assertNoLogs(self.LOGGER, level="INFO"):
            self._render(doc, "pagelet_view")

    def test_production_logs_once_per_consumer_per_process(self):
        from plone.pageletlayout import bridge

        self._set_debug(False)
        bridge._warned_consumers.clear()
        self.addCleanup(bridge._warned_consumers.clear)
        with self.assertLogs(self.LOGGER, level="INFO") as captured:
            self._render(self.portal, "accessibility-info")
            self._render(self.portal, "accessibility-info")
        self.assertEqual(
            len(captured.records), 1, "production signal is not rate-limited"
        )
        self.assertEqual(captured.records[0].levelname, "INFO")
        # a different consumer still gets its own line
        with self.assertLogs(self.LOGGER, level="INFO") as captured:
            self._render(self.portal, "@@overview-controlpanel")
        self.assertIn("overview.pt", captured.records[0].getMessage())
