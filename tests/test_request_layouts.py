"""Trigger-chain and fullscreen-layout tests (request-layouts ticket 08).

Two seams. The subscriber itself (``layouts.apply_layout``) is exercised
directly with a ``PubAfterTraversal`` event — precedence, escape hatch,
unknown-name fall-through, the at-most-one-layer rule. The end-to-end
behavior — the fullscreen region flip, the layout body class, the toolbar
and head staying intact — is pinned functionally through the publisher
(testbrowser), because the trigger chain only fires on a real publish:
``restrictedTraverse`` never emits ``IPubAfterTraversal``.
"""

import unittest

import transaction
from zope.component import getGlobalSiteManager
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import alsoProvides
from ZPublisher.pubevents import PubAfterTraversal

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.interfaces import IFullscreenLayoutLayer
from plone.pageletlayout.interfaces import IFullScreenPagelet
from plone.pageletlayout.interfaces import IPageLayout
from plone.pageletlayout.interfaces import IPlonePageletlayoutLayer
from plone.pageletlayout.layouts import apply_layout
from plone.pageletlayout.metaconfigure import PageLayout
from plone.pageletlayout.page import PageletPage
from plone.pageletlayout.pagelets.layout import BodyOnlyRegion
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.pageletlayout.testing import INTEGRATION_TESTING
from plone.testing.zope import Browser


LOGGER = "plone.pageletlayout.layouts"


class ITestAjaxLayer(IPlonePageletlayoutLayer):
    """Stand-in ajax layout layer: ticket 09 ships the real one; here it
    only proves the alias trigger resolves the name through the registry."""


class _MarkedView:
    """A published-view stand-in carrying the static fullscreen marker."""


class TriggerChainTestCase(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.request = self.layer["request"]

    def fire(self, form=None, published=None):
        self.request.form.update(form or {})
        if published is not None:
            self.request["PUBLISHED"] = published
        apply_layout(PubAfterTraversal(self.request))

    def marked_view(self):
        view = _MarkedView()
        alsoProvides(view, IFullScreenPagelet)
        return view

    def register_ajax(self):
        gsm = getGlobalSiteManager()
        entry = PageLayout("ajax", ITestAjaxLayer)
        gsm.registerUtility(entry, IPageLayout, name="ajax")
        self.addCleanup(gsm.unregisterUtility, entry, IPageLayout, "ajax")


class TestTriggerChain(TriggerChainTestCase):
    def test_param_applies_the_fullscreen_layer(self):
        self.fire({"pagelet_layout": "fullscreen"})
        self.assertTrue(IFullscreenLayoutLayer.providedBy(self.request))

    def test_no_trigger_applies_no_layer(self):
        self.fire()
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))

    def test_static_marker_applies_the_layer(self):
        self.fire(published=self.marked_view())
        self.assertTrue(IFullscreenLayoutLayer.providedBy(self.request))

    def test_param_default_is_the_escape_hatch(self):
        # Even on a statically-marked view: no layer, the default renders.
        self.fire({"pagelet_layout": "default"}, published=self.marked_view())
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))

    def test_unknown_name_warns_and_falls_through_to_the_marker(self):
        with self.assertLogs(LOGGER, level="WARNING") as captured:
            self.fire({"pagelet_layout": "no-such"}, published=self.marked_view())
        self.assertEqual(len(captured.records), 1)
        self.assertIn("no-such", captured.output[0])
        self.assertTrue(IFullscreenLayoutLayer.providedBy(self.request))

    def test_unknown_name_alone_yields_the_default(self):
        with self.assertLogs(LOGGER, level="WARNING"):
            self.fire({"pagelet_layout": "no-such"})
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))

    def test_alias_resolves_the_ajax_layout_through_the_registry(self):
        self.register_ajax()
        self.fire({"ajax_load": "1"})
        self.assertTrue(ITestAjaxLayer.providedBy(self.request))

    def test_alias_is_inert_while_no_ajax_layout_is_registered(self):
        # No special-casing: the name just misses the registry, so the
        # chain falls through to the static marker.
        self.fire({"ajax_load": "1"}, published=self.marked_view())
        self.assertFalse(ITestAjaxLayer.providedBy(self.request))
        self.assertTrue(IFullscreenLayoutLayer.providedBy(self.request))

    def test_explicit_falsy_alias_forces_nothing(self):
        self.register_ajax()
        self.fire({"ajax_load": "0"})
        self.assertFalse(ITestAjaxLayer.providedBy(self.request))
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))

    def test_param_beats_alias_beats_marker_one_layer_only(self):
        self.register_ajax()
        self.fire(
            {"pagelet_layout": "fullscreen", "ajax_load": "1"},
            published=self.marked_view(),
        )
        self.assertTrue(IFullscreenLayoutLayer.providedBy(self.request))
        self.assertFalse(ITestAjaxLayer.providedBy(self.request))

    def test_alias_beats_the_static_marker(self):
        self.register_ajax()
        self.fire({"ajax_load": "1"}, published=self.marked_view())
        self.assertTrue(ITestAjaxLayer.providedBy(self.request))
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))


class TestLayoutName(TriggerChainTestCase):
    def test_default_when_no_layer_applied(self):
        page = PageletPage(self.layer["portal"], self.request)
        self.assertEqual(page.layout_name, "default")

    def test_reports_the_applied_layers_registry_name(self):
        self.fire({"pagelet_layout": "fullscreen"})
        page = PageletPage(self.layer["portal"], self.request)
        self.assertEqual(page.layout_name, "fullscreen")

    def test_alias_request_reports_the_layout_name_alias_free(self):
        self.register_ajax()
        self.fire({"ajax_load": "1"})
        page = PageletPage(self.layer["portal"], self.request)
        self.assertEqual(page.layout_name, "ajax")

    def test_reachable_from_chrome_pagelets_as_view_layout_name(self):
        # The composition rule: a chrome pagelet's self.view is the
        # published pagelet — and on the fullscreen layer, the region
        # provider resolving at all proves the layer-dimension shadow.
        self.fire({"pagelet_layout": "fullscreen"})
        portal = self.layer["portal"]
        view = PageletPage(portal, self.request)
        provider = getMultiAdapter(
            (portal, self.request, view),
            IContentProvider,
            name="plone.pageletlayout.pagelayout",
        )
        self.assertIsInstance(provider, BodyOnlyRegion)
        self.assertEqual(provider.view.layout_name, "fullscreen")


class TestLayoutRegistry(TriggerChainTestCase):
    def test_registry_enumerates_the_fullscreen_layout(self):
        layouts = dict(getUtilitiesFor(IPageLayout))
        self.assertIn("fullscreen", layouts)
        entry = layouts["fullscreen"]
        self.assertEqual(entry.name, "fullscreen")
        self.assertIs(entry.layer, IFullscreenLayoutLayer)
        self.assertIs(entry.view_marker, IFullScreenPagelet)


class FunctionalLayoutTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        folder = api.content.create(
            container=self.portal, type="Folder", id="a-folder", title="A Folder"
        )
        api.content.create(
            container=folder, type="Document", id="a-doc", title="A Document"
        )
        transaction.commit()
        self.browser = Browser(self.layer["app"])
        self.browser.handleErrors = False
        self.browser.addHeader(
            "Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}"
        )

    def open(self, path):
        self.browser.open(f"{self.portal_url}/{path}")
        return self.browser.contents


class TestFullscreenOnRequest(FunctionalLayoutTestCase):
    """?pagelet_layout=fullscreen re-dresses any pagelet page."""

    def test_unmarked_view_renders_the_default_layout(self):
        html = self.open("a-folder/a-doc/pagelet_view")
        self.assertIn("element-logo", html)
        self.assertIn("pagelet-layout-default", html)

    def test_fullscreen_param_drops_chrome_keeps_head_and_toolbar(self):
        html = self.open("a-folder/a-doc/pagelet_view?pagelet_layout=fullscreen")
        # body-only region: no chrome elements
        self.assertNotIn("element-logo", html)
        self.assertNotIn("element-globalnav", html)
        self.assertNotIn("element-colophon", html)
        # the shared frame stays whole: full head plumbing and the toolbar
        self.assertIn('<meta name="generator"', html)
        self.assertIn('id="edit-zone"', html)
        # the content itself still renders
        self.assertIn('id="content-core"', html)

    def test_frame_stamps_the_fullscreen_body_class(self):
        html = self.open("a-folder/a-doc/pagelet_view?pagelet_layout=fullscreen")
        self.assertIn("pagelet-layout-fullscreen", html)
        self.assertNotIn("pagelet-layout-default", html)


class TestFullscreenByStaticMarker(FunctionalLayoutTestCase):
    """folder_contents keeps its unchanged provides= stanza and still
    renders fullscreen — now via the layer the trigger chain applies."""

    def test_folder_contents_defaults_to_fullscreen(self):
        html = self.open("a-folder/folder_contents")
        self.assertIn("pat-structure", html)
        self.assertNotIn("element-logo", html)
        self.assertIn('id="edit-zone"', html)
        self.assertIn("pagelet-layout-fullscreen", html)

    def test_escape_hatch_renders_the_default_layout(self):
        html = self.open("a-folder/folder_contents?pagelet_layout=default")
        self.assertIn("pat-structure", html)
        self.assertIn("element-logo", html)
        self.assertIn("pagelet-layout-default", html)

    def test_unknown_name_falls_through_to_the_marker(self):
        with self.assertLogs(LOGGER, level="WARNING") as captured:
            html = self.open("a-folder/folder_contents?pagelet_layout=no-such")
        self.assertEqual(len(captured.records), 1)
        self.assertNotIn("element-logo", html)
        self.assertIn("pagelet-layout-fullscreen", html)
