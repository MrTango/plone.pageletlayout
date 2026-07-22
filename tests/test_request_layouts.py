"""Trigger-chain and named-layout tests (request-layouts tickets 08 + 09).

Three seams. The subscriber itself (``layouts.apply_layout``) is exercised
directly with a ``PubAfterTraversal`` event — precedence, escape hatch,
unknown-name fall-through, the at-most-one-layer rule. The end-to-end
behavior — the fullscreen region flip, the ajax fragment contract, the
layout body class — is pinned functionally through the publisher
(testbrowser), because the trigger chain only fires on a real publish:
``restrictedTraverse`` never emits ``IPubAfterTraversal``. The fragment's
element order (with a real status message queued) is pinned by marking the
request and rendering the view directly.
"""

import unittest

import transaction
from Products.statusmessages.interfaces import IStatusMessage
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
from plone.pageletlayout.interfaces import IAjaxLayoutLayer
from plone.pageletlayout.interfaces import IFullscreenLayoutLayer
from plone.pageletlayout.interfaces import IFullScreenPagelet
from plone.pageletlayout.interfaces import IPageLayout
from plone.pageletlayout.layouts import apply_layout
from plone.pageletlayout.page import PageletPage
from plone.pageletlayout.pagelets.layout import BodyOnlyRegion
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.pageletlayout.testing import INTEGRATION_TESTING
from plone.testing.zope import Browser


LOGGER = "plone.pageletlayout.layouts"


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
        self.fire({"ajax_load": "1"})
        self.assertTrue(IAjaxLayoutLayer.providedBy(self.request))

    def test_ajax_param_applies_the_ajax_layer(self):
        self.fire({"pagelet_layout": "ajax"})
        self.assertTrue(IAjaxLayoutLayer.providedBy(self.request))

    def test_explicit_falsy_alias_forces_nothing(self):
        self.fire({"ajax_load": "0"})
        self.assertFalse(IAjaxLayoutLayer.providedBy(self.request))
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))

    def test_param_beats_alias_beats_marker_one_layer_only(self):
        self.fire(
            {"pagelet_layout": "fullscreen", "ajax_load": "1"},
            published=self.marked_view(),
        )
        self.assertTrue(IFullscreenLayoutLayer.providedBy(self.request))
        self.assertFalse(IAjaxLayoutLayer.providedBy(self.request))

    def test_alias_beats_the_static_marker(self):
        self.fire({"ajax_load": "1"}, published=self.marked_view())
        self.assertTrue(IAjaxLayoutLayer.providedBy(self.request))
        self.assertFalse(IFullscreenLayoutLayer.providedBy(self.request))

    def test_unknown_name_falls_through_to_the_alias(self):
        # Lenient by design: ?pagelet_layout=typo&ajax_load=1 still honors
        # the ajax intent.
        with self.assertLogs(LOGGER, level="WARNING"):
            self.fire({"pagelet_layout": "no-such", "ajax_load": "1"})
        self.assertTrue(IAjaxLayoutLayer.providedBy(self.request))


class TestLayoutName(TriggerChainTestCase):
    def test_default_when_no_layer_applied(self):
        page = PageletPage(self.layer["portal"], self.request)
        self.assertEqual(page.layout_name, "default")

    def test_reports_the_applied_layers_registry_name(self):
        self.fire({"pagelet_layout": "fullscreen"})
        page = PageletPage(self.layer["portal"], self.request)
        self.assertEqual(page.layout_name, "fullscreen")

    def test_alias_request_reports_the_layout_name_alias_free(self):
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
    def test_registry_enumerates_all_shipped_layouts(self):
        # The spec's full registry assertion: fullscreen + ajax (default is
        # the absence of a layer and never has an entry).
        layouts = dict(getUtilitiesFor(IPageLayout))
        self.assertEqual(sorted(layouts), ["ajax", "fullscreen"])

    def test_the_fullscreen_entry(self):
        entry = dict(getUtilitiesFor(IPageLayout))["fullscreen"]
        self.assertEqual(entry.name, "fullscreen")
        self.assertIs(entry.layer, IFullscreenLayoutLayer)
        self.assertIs(entry.view_marker, IFullScreenPagelet)

    def test_the_ajax_entry_is_request_only(self):
        entry = dict(getUtilitiesFor(IPageLayout))["ajax"]
        self.assertEqual(entry.name, "ajax")
        self.assertIs(entry.layer, IAjaxLayoutLayer)
        self.assertIsNone(entry.view_marker)


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


class TestAjaxFragmentContract(FunctionalLayoutTestCase):
    """The ajax layout end-to-end: both param spellings return the
    fragment-contract document (docs/request-layouts.md, section 6)."""

    def assert_contract_document(self, html):
        # A full document with a charset-only head: no title, no head
        # providers (styles/scripts/meta), no toolbar, no chrome elements.
        self.assertTrue(html.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn('lang="en"', html)
        # Charset only between <head> and </head> — no title, no head
        # providers. (plone.protect's transform appends protect.js to the
        # *body* on authenticated responses; that is outside the layout.)
        head = html[html.index("<head>") : html.index("</head>")]
        self.assertIn('<meta charset="utf-8"', head)
        self.assertNotIn("<title", head)
        self.assertNotIn("<link", head)
        self.assertNotIn("<script", head)
        self.assertNotIn('name="viewport"', html)
        self.assertNotIn('name="generator"', html)
        self.assertNotIn('id="edit-zone"', html)
        self.assertNotIn("element-logo", html)
        self.assertNotIn("element-colophon", html)
        # The extraction targets: #content wrapping the first h1 and the
        # body element's #content-core wrapper.
        self.assertIn('<article id="content">', html)
        self.assertIn('class="documentFirstHeading"', html)
        self.assertIn('id="content-core"', html)

    def assert_contract_headers(self):
        headers = self.browser.headers
        self.assertEqual(headers.get("X-Theme-Disabled"), "1")
        self.assertEqual(headers.get("X-Robots-Tag"), "noindex")

    def test_canonical_param_returns_the_contract_document(self):
        html = self.open("a-folder/a-doc/pagelet_view?pagelet_layout=ajax")
        self.assert_contract_document(html)
        self.assert_contract_headers()

    def test_alias_returns_the_contract_document(self):
        html = self.open("a-folder/a-doc/pagelet_view?ajax_load=1")
        self.assert_contract_document(html)
        self.assert_contract_headers()

    def test_body_attributes_carry_the_pattern_hooks(self):
        html = self.open("a-folder/a-doc/pagelet_view?pagelet_layout=ajax")
        # bodyClass + the layout body class, dir, and the patterns-settings
        # data attributes pat-plone-modal's redirect detection reads.
        self.assertIn("pagelet-layout-ajax", html)
        self.assertIn("portaltype-document", html)
        self.assertIn('dir="ltr"', html)
        self.assertIn("data-base-url=", html)
        self.assertIn("data-view-url=", html)

    def test_unknown_name_with_alias_returns_the_contract(self):
        with self.assertLogs(LOGGER, level="WARNING"):
            html = self.open("a-folder/a-doc/pagelet_view?pagelet_layout=no-such&ajax_load=1")
        self.assert_contract_document(html)
        self.assert_contract_headers()

    def test_alias_beats_the_static_marker_end_to_end(self):
        # folder_contents' default is fullscreen; the alias re-dresses it
        # as the ajax fragment.
        html = self.open("a-folder/folder_contents?ajax_load=1")
        self.assertIn("pagelet-layout-ajax", html)
        self.assertNotIn("pagelet-layout-fullscreen", html)
        self.assertNotIn('id="edit-zone"', html)
        self.assert_contract_headers()

    def test_explicit_falsy_alias_renders_the_default_layout(self):
        html = self.open("a-folder/a-doc/pagelet_view?ajax_load=0")
        self.assertIn("pagelet-layout-default", html)
        self.assertIn("element-logo", html)

    def test_content_id_is_ajax_only(self):
        # #content is the ajax layout's extraction hook; other layouts keep
        # per-view content ids. #content-core is present in every layout.
        default_html = self.open("a-folder/a-doc/pagelet_view")
        self.assertNotIn('id="content"', default_html)
        self.assertIn('id="content-core"', default_html)


class TestAjaxElementOrder(unittest.TestCase):
    """The fixed element set in document order, with a real queued status
    message. The trigger chain never fires on ``restrictedTraverse``, so
    the ajax layer is marked on the request directly (the
    test_fullscreen_contents precedent)."""

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.doc = api.content.create(
            container=self.portal, type="Document", id="a-doc", title="A Document"
        )

    def render_ajax(self):
        alsoProvides(self.request, IAjaxLayoutLayer)
        return self.doc.restrictedTraverse("pagelet_view")()

    def test_statusmessages_render_outside_and_before_content(self):
        IStatusMessage(self.request).add("Changes saved.")
        html = self.render_ajax()
        message = html.index("portalMessage")
        content = html.index('<article id="content">')
        self.assertLess(message, content)

    def test_first_h1_is_the_document_heading_then_content_core(self):
        html = self.render_ajax()
        first_h1 = html.index("<h1")
        self.assertIn('class="documentFirstHeading"', html[first_h1 : html.index("</h1>")])
        self.assertLess(html.index('<article id="content">'), first_h1)
        self.assertLess(first_h1, html.index('id="content-core"'))

    def test_ajax_region_sets_both_response_headers(self):
        self.render_ajax()
        response = self.request.response
        self.assertEqual(response.getHeader("X-Theme-Disabled"), "1")
        self.assertEqual(response.getHeader("X-Robots-Tag"), "noindex")
