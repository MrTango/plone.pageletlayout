"""Render tests for the slot layout.

The pagelet view renders end-to-end with the markup-contract hooks, the
elements land in the stock managers their slot assignment names — nested in
header, main and footer — and the shipped assignment stays in parity with
``slots.DEFAULT_ASSIGNMENTS``.
"""

import pathlib
import re
import unittest

import lxml.html
import transaction
from zope.component import getUtility

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.formwidget.namedfile.converter import b64encode_file
from plone.pageletlayout.pagelets.slots import assign
from plone.pageletlayout.pagelets.slots import ASSIGNMENTS_RECORD
from plone.pageletlayout.pagelets.slots import DEFAULT_ASSIGNMENTS
from plone.pageletlayout.pagelets.slots import SLOTS
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.pageletlayout.testing import INTEGRATION_TESTING


PACKAGE = pathlib.Path(__file__).parent.parent / "src" / "plone" / "pageletlayout"
SKINNAME = "Plone Default"


class TestLayoutRender(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.doc = api.content.create(
            container=self.portal,
            type="Document",
            id="a-page",
            title="A Page",
            description="A description",
        )
        transaction.commit()

    def _render(self, view_name):
        view = self.doc.restrictedTraverse(view_name)
        return view()

    def test_managed_view_renders_with_hooks(self):
        html = self._render("pagelet_view")
        # markup-contract hooks (§9)
        self.assertIn('class="plone-layout"', html)
        self.assertIn("element-contentheader", html)
        self.assertIn('class="plone-site-title"', html)
        self.assertRegex(html, r'<img alt=""[^>]+plone-logo\.svg')
        self.assertIn("documentFirstHeading", html)
        self.assertIn('id="content-core"', html)
        self.assertIn("element-body", html)
        self.assertIn("A Page", html)
        # The forbidden-utility ban is checked file-based, on our own
        # templates only (test_template_lint.py). It cannot be asserted over
        # rendered output any more: the page now carries stock viewlet markup
        # through the manager bridges (pagelets/managers.py) — CMFPlone's
        # plone.footer wraps the footer portlets in a Bootstrap .row — and
        # that markup is not ours to lint.

    def test_stock_logo_has_intrinsic_dimensions(self):
        html = self._render("pagelet_view")
        self.assertRegex(html, r'<img alt=""[^>]+width="215"[^>]+height="56"')

    def test_registry_logo_has_intrinsic_dimensions(self):
        svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'width="300" height="100" viewBox="0 0 300 100"></svg>'
        )
        api.portal.set_registry_record(
            "plone.site_logo",
            b64encode_file("logo.svg", svg),
        )
        transaction.commit()
        html = self._render("pagelet_view")
        self.assertRegex(
            html,
            r'<img alt=""[^>]+@@site-logo/logo\.svg"[^>]+width="300"'
            r'[^>]+height="100"',
        )

    def test_unreadable_logo_renders_without_dimensions(self):
        api.portal.set_registry_record("plone.site_logo", b64encode_file("logo.svg", b"junk"))
        transaction.commit()
        html = self._render("pagelet_view")
        img = re.search(r"<img alt=\"\"[^>]+>", html).group(0)
        self.assertIn("@@site-logo/logo.svg", img)
        self.assertNotIn("width=", img)


class TestSlotFrame(unittest.TestCase):
    """Elements render inside the landmark their slot belongs to."""

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.doc = api.content.create(
            container=self.portal, type="Document", id="a-page", title="A Page"
        )
        transaction.commit()

    def tree(self):
        return lxml.html.fromstring(self.doc.restrictedTraverse("pagelet_view")())

    def test_elements_sit_in_their_landmarks(self):
        tree = self.tree()
        expected = {
            "#portal-top": ("#portal-logo", ".element-searchbox", "#portal-globalnav"),
            "#main-container": ("#portal-breadcrumbs", "#content"),
            "#content": (".element-contentheader", "#section-byline", "#content-core"),
            "#portal-footer-wrapper": (".element-colophon", ".element-siteactions"),
        }
        for landmark, hooks in expected.items():
            for hook in hooks:
                with self.subTest(landmark=landmark, hook=hook):
                    self.assertEqual(len(tree.cssselect(f"{landmark} {hook}")), 1)

    def test_landmarks_are_regions_of_the_layout(self):
        tree = self.tree()
        landmarks = ("header#portal-top", "main#main-container", "footer#portal-footer-wrapper")
        for selector in landmarks:
            with self.subTest(selector=selector):
                (landmark,) = tree.cssselect(f".plone-layout > {selector}")
                self.assertIn("plone-region", landmark.get("class"))

    def test_moving_an_element_needs_no_restart(self):
        assign("plone.pageletlayout.searchbox", "plone.portalfooter")
        transaction.commit()
        tree = self.tree()
        self.assertEqual(len(tree.cssselect("#portal-footer-wrapper .element-searchbox")), 1)
        self.assertEqual(len(tree.cssselect("#portal-top .element-searchbox")), 0)

    def test_order_inside_a_slot_comes_from_the_storage(self):
        storage = getUtility(IViewletSettingsStorage)
        order = list(storage.getOrder("plone.portalfooter", SKINNAME))
        order.remove("plone.pageletlayout.siteactions")
        order.insert(0, "plone.pageletlayout.siteactions")
        storage.setOrder("plone.portalfooter", SKINNAME, tuple(order))
        transaction.commit()
        html = self.doc.restrictedTraverse("pagelet_view")()
        self.assertLess(html.index("element-siteactions"), html.index("element-colophon"))

    def test_hiding_an_element_in_its_slot(self):
        storage = getUtility(IViewletSettingsStorage)
        hidden = storage.getHidden("plone.portalfooter", SKINNAME)
        storage.setHidden(
            "plone.portalfooter", SKINNAME, hidden + ("plone.pageletlayout.colophon",)
        )
        transaction.commit()
        self.assertEqual(self.tree().cssselect(".element-colophon"), [])

    def test_an_unassigned_element_renders_nowhere(self):
        assign("plone.pageletlayout.colophon", None)
        transaction.commit()
        self.assertEqual(self.tree().cssselect(".element-colophon"), [])

    def test_empty_footer_leaves_no_landmark(self):
        for name, slot in DEFAULT_ASSIGNMENTS.items():
            if slot == "plone.portalfooter":
                assign(name, None)
        storage = getUtility(IViewletSettingsStorage)
        hidden = storage.getHidden("plone.portalfooter", SKINNAME)
        storage.setHidden("plone.portalfooter", SKINNAME, hidden + ("plone.footer",))
        transaction.commit()
        self.assertEqual(self.tree().cssselect("#portal-footer-wrapper"), [])


class TestSlotParity(unittest.TestCase):
    """registry.xml, viewlets.xml and the 1004 upgrade profile agree with
    ``slots.DEFAULT_ASSIGNMENTS``."""

    layer = INTEGRATION_TESTING

    def test_installed_assignments_match_the_code(self):
        self.assertEqual(api.portal.get_registry_record(ASSIGNMENTS_RECORD), DEFAULT_ASSIGNMENTS)

    def test_every_assignment_names_a_slot(self):
        self.assertLessEqual(set(DEFAULT_ASSIGNMENTS.values()), set(SLOTS))

    def test_every_element_has_a_place_in_its_slot(self):
        storage = getUtility(IViewletSettingsStorage)
        for name, slot in DEFAULT_ASSIGNMENTS.items():
            with self.subTest(name=name):
                self.assertIn(name, storage.getOrder(slot, SKINNAME))

    def test_upgrade_profile_matches_the_default_profile(self):
        default = PACKAGE / "profiles" / "default"
        upgrade = PACKAGE / "upgrades" / "1004"
        self.assertEqual(
            (upgrade / "viewlets.xml").read_text(), (default / "viewlets.xml").read_text()
        )
        record = re.compile(r"<record\b.*?</record>", re.DOTALL)
        self.assertEqual(
            record.findall((upgrade / "registry.xml").read_text()),
            record.findall((default / "registry.xml").read_text()),
        )
