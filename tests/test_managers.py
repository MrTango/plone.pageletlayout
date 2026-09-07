"""Functional tests for the stock viewlet-manager bridges (managers.py).

The layout renders one manager of its own; every *other* Plone manager —
``IAboveContentBody``, ``IPortalFooter``, ``IBelowContentBody``, … — is where
add-ons register their viewlets, and before the bridges those viewlets
vanished from a pagelet page with no error at all. Four facets, one test case
each:

* the bridges render (and the ``self.view`` lookup is what makes the
  form-bound ones work);
* the stock viewlets our elements replace render exactly once, because the
  profile hides them;
* every viewlet that renders through a bridge logs a deprecation signal
  naming itself and the fix;
* the sibling bridges are ordinary storage-managed elements — ELEMENTS,
  viewlets.xml and the ZCML stanzas agree.
"""

import unittest

import transaction
from zope.component import getGlobalSiteManager
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.configuration import xmlconfig
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import Interface
from zope.viewlet.interfaces import IViewlet

from plone import api
from plone.app.layout.viewlets import interfaces as stock_managers
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.interfaces import IPlonePageletlayoutLayer
from plone.pageletlayout.pagelets.layout import ELEMENTS
from plone.pageletlayout.pagelets.managers import CONTENT_HEADER_MANAGERS
from plone.pageletlayout.pagelets.managers import RENDERED_MANAGERS
from plone.pageletlayout.pagelets.managers import SIBLING_MANAGERS
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


MANAGERS_LOGGER = "plone.pageletlayout.pagelets.managers"

#: The stock skin name the profile's order/hidden sets are stored under.
SKINNAME = "Plone Default"

ZCML_WRAPPER = """\
<configure
    xmlns="http://namespaces.zope.org/zope"
    xmlns:browser="http://namespaces.zope.org/browser">
  <include package="Products.Five.viewlet" file="meta.zcml" />
  {}
</configure>
"""

VIEWLET_STANZA = """\
  <browser:viewlet
      name="{name}"
      manager="plone.app.layout.viewlets.interfaces.{manager}"
      class="tests.viewlet_fixtures.{class_}"
      view="{view}"
      layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
      permission="zope2.View"
      />
"""

DEFAULT_VIEW = "zope.browser.interfaces.IBrowserView"
EDIT_FORM_VIEW = "plone.dexterity.interfaces.IDexterityEditForm"


class ManagerBridgeTestCase(unittest.TestCase):
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

    def register_probe(self, name, manager, class_, view=DEFAULT_VIEW):
        """Register one probe viewlet exactly as an add-on would.

        Through ZCML, not ``provideAdapter``: ``browser:viewlet`` is what
        applies the AccessControl declarations that
        ``BaseOrderedViewletManager.filter`` checks with ``guarded_hasattr``
        — a hand-registered class is silently filtered out instead.

        Registrations made at test time outlive the test (the layer's
        registry is stacked per layer, not per test), so each is unwound
        again on cleanup — a probe left in IBelowContentBody would show up
        in every other test's rendered page.
        """
        view_iface = self._resolve(view)
        manager_iface = getattr(stock_managers, manager)
        xmlconfig.string(
            ZCML_WRAPPER.format(
                VIEWLET_STANZA.format(
                    name=name, manager=manager, class_=class_, view=view
                )
            )
        )
        self.addCleanup(
            getGlobalSiteManager().unregisterAdapter,
            required=(
                Interface,
                IPlonePageletlayoutLayer,
                view_iface,
                manager_iface,
            ),
            provided=IViewlet,
            name=name,
        )

    @staticmethod
    def _resolve(dotted):
        module, _, attr = dotted.rpartition(".")
        return getattr(__import__(module, fromlist=[attr]), attr)

    def render(self, context, name):
        return context.restrictedTraverse(name)()

    def set_debug(self, value):
        """Development mode, restored on cleanup (the test_form_layout
        idiom): it is the tier where every bridged render warns."""
        from App.config import getConfiguration

        config = getConfiguration()
        old = getattr(config, "debug_mode", False)
        config.debug_mode = value
        self.addCleanup(setattr, config, "debug_mode", old)


class TestBridgedManagersRender(ManagerBridgeTestCase):
    """A viewlet registered into a bridged manager reaches the page."""

    def test_sibling_bridges_render_their_viewlets(self):
        self.register_probe(
            "probe.abovecontentbody", "IAboveContentBody", "AboveContentBodyProbe"
        )
        self.register_probe(
            "probe.belowcontentbody", "IBelowContentBody", "BelowContentBodyProbe"
        )
        self.register_probe("probe.portalfooter", "IPortalFooter", "PortalFooterProbe")
        html = self.render(self.doc, "pagelet_view")
        for marker in (
            "probe-abovecontentbody",
            "probe-belowcontentbody",
            "probe-portalfooter",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_sibling_bridges_keep_the_classic_positions(self):
        # A bridge is only useful if it puts the viewlet where the add-on
        # meant it to be: above-content-body above the body, below-content-
        # body below it, the footer below that.
        self.register_probe(
            "probe.abovecontentbody", "IAboveContentBody", "AboveContentBodyProbe"
        )
        self.register_probe(
            "probe.belowcontentbody", "IBelowContentBody", "BelowContentBodyProbe"
        )
        self.register_probe("probe.portalfooter", "IPortalFooter", "PortalFooterProbe")
        html = self.render(self.doc, "pagelet_view")
        self.assertLess(html.index("probe-abovecontentbody"), html.index("content-core"))
        self.assertLess(html.index("content-core"), html.index("probe-belowcontentbody"))
        self.assertLess(
            html.index("probe-belowcontentbody"), html.index("probe-portalfooter")
        )

    def test_in_element_bridges_render_inside_the_content_header(self):
        # The three content-header managers are positions *within* the
        # title block, so they must land between the header's open tag and
        # the elements that follow it — not as siblings.
        self.register_probe(
            "probe.abovecontenttitle", "IAboveContentTitle", "AboveContentTitleProbe"
        )
        self.register_probe(
            "probe.belowcontenttitle", "IBelowContentTitle", "BelowContentTitleProbe"
        )
        html = self.render(self.doc, "pagelet_view")
        header = html.index("element-contentheader")
        title = html.index("documentFirstHeading")
        description = html.index("documentDescription")
        self.assertLess(header, html.index("probe-abovecontenttitle"))
        self.assertLess(html.index("probe-abovecontenttitle"), title)
        self.assertLess(title, html.index("probe-belowcontenttitle"))
        self.assertLess(html.index("probe-belowcontenttitle"), description)

    def test_empty_bridge_renders_nothing_at_all(self):
        # No probes: the managers with no visible viewlets must not leave
        # an empty wrapper behind on every page.
        html = self.render(self.doc, "pagelet_view")
        self.assertNotIn("element-abovecontentbody", html)
        self.assertNotIn("element-portaltop", html)

    def test_view_bound_viewlet_renders_on_the_wrapped_form(self):
        # The point of looking the manager up in code against self.view: a
        # viewlet bound to view=IDexterityEditForm binds to the published
        # *wrapper*. Handing the manager the pagelet instead (a provider:
        # expression in our own template) would drop it.
        self.register_probe(
            "probe.editform",
            "IAboveContentBody",
            "EditFormProbe",
            view=EDIT_FORM_VIEW,
        )
        self.assertIn("probe-editform", self.render(self.doc, "@@edit"))

    def test_view_bound_viewlet_stays_off_the_view_page(self):
        # ... and the same registration must NOT leak onto an ordinary page,
        # which would mean the view dimension was being ignored.
        self.register_probe(
            "probe.editform",
            "IAboveContentBody",
            "EditFormProbe",
            view=EDIT_FORM_VIEW,
        )
        self.assertNotIn("probe-editform", self.render(self.doc, "pagelet_view"))


class TestStockDuplicatesRenderOnce(ManagerBridgeTestCase):
    """Bridging without hiding would double the chrome we reimplement."""

    #: (marker, expected occurrences). Our logo/searchbox/breadcrumbs/
    #: globalnav templates deliberately keep the stock ids, and the byline
    #: pagelet wraps the stock viewlet whole — so ONE occurrence is the proof
    #: that exactly one of the two rendered. ``portal-siteactions`` is an id
    #: only the stock template uses, so zero is the proof there.
    MARKERS = (
        ('id="portal-logo"', 1),
        ('id="portal-searchbox"', 1),
        ('id="portal-breadcrumbs"', 1),
        ('id="portal-globalnav"', 1),
        ('id="section-byline"', 1),
        ('id="social-tags-body"', 1),
        ('id="portal-siteactions"', 0),
    )

    def test_no_element_renders_twice(self):
        html = self.render(self.doc, "pagelet_view")
        for marker, expected in self.MARKERS:
            with self.subTest(marker=marker):
                self.assertEqual(html.count(marker), expected)

    def test_our_own_elements_are_all_there(self):
        # The mirror image: hiding must not have taken out the real thing.
        html = self.render(self.doc, "pagelet_view")
        for marker in (
            "element-logo",
            "element-searchbox",
            "element-breadcrumbs",
            "element-colophon",
            "element-siteactions",
        ):
            with self.subTest(marker=marker):
                self.assertEqual(html.count(marker), 1)

    def test_profile_hides_every_reimplemented_stock_viewlet(self):
        storage = getUtility(IViewletSettingsStorage)
        expected = {
            "plone.portalheader": {"plone.logo", "plone.anontools", "plone.searchbox"},
            "plone.mainnavigation": {"plone.global_sections"},
            "plone.abovecontent": {"plone.path_bar"},
            "plone.abovecontenttitle": {"plone.socialtags"},
            "plone.belowcontenttitle": {"plone.documentbyline"},
            "plone.portalfooter": {"plone.colophon", "plone.site_actions"},
        }
        for manager, hidden in expected.items():
            with self.subTest(manager=manager):
                self.assertTrue(
                    hidden.issubset(set(storage.getHidden(manager, SKINNAME))),
                    f"{manager}: the profile did not hide {sorted(hidden)}",
                )

    def test_hiding_only_touches_managers_we_render(self):
        # Hiding a viewlet in a manager nothing renders would be a no-op
        # dressed up as a decision.
        storage = getUtility(IViewletSettingsStorage)
        for manager in (
            "plone.portalheader",
            "plone.mainnavigation",
            "plone.abovecontent",
            "plone.abovecontenttitle",
            "plone.belowcontenttitle",
            "plone.portalfooter",
        ):
            with self.subTest(manager=manager):
                self.assertIn(manager, RENDERED_MANAGERS)
                self.assertTrue(storage.getHidden(manager, SKINNAME))

    def test_membertools_is_not_hidden(self):
        # The logged-in half of the personal bar has no element of ours —
        # AnontoolsChromePagelet covers the anonymous half only — so it stays
        # visible and reaches the page through the portalheader bridge.
        #
        # It still renders nothing here: membertools.pt is gated on
        # ``not is_toolbar_visible``, and the pagelet layout always renders
        # the toolbar. Leaving it unhidden is what matters — the day a site
        # turns the toolbar off, the personal bar appears instead of staying
        # lost, which is exactly what the bridge is for.
        storage = getUtility(IViewletSettingsStorage)
        self.assertNotIn(
            "plone.membertools", storage.getHidden("plone.portalheader", SKINNAME)
        )

    def test_footer_portlets_reach_the_page(self):
        # plone.footer renders the footer portlet manager, which had no way
        # onto a pagelet page at all before the portalfooter bridge. Plone's
        # own default assignments there are a colophon and a site-actions
        # portlet, so a stock site now shows those *alongside* our colophon
        # and siteactions elements: our elements are the clean
        # reimplementation and stay, the portlet assignments are site data an
        # integrator removes (docs/porting-main-template.md).
        html = self.render(self.doc, "pagelet_view")
        self.assertIn("element-portalfooter", html)
        self.assertIn("portletWrapper", html)
        self.assertEqual(html.count('id="portal-colophon"'), 1)


class TestDeprecationSignal(ManagerBridgeTestCase):
    """A bridge is a waypoint: what rides it says so, in the log.

    The "must stay silent" cases below assert on the message text rather
    than with ``assertNoLogs``: stock Plone always has *something* riding a
    bridge (the footer portlets, lock info), so the logger is never quiet
    and ``assertNoLogs`` on it could only ever fail. What is being pinned is
    per-viewlet — that this particular viewlet is not the one being asked to
    move.
    """

    def test_warning_names_the_viewlet_and_the_fix(self):
        self.register_probe(
            "probe.belowcontentbody", "IBelowContentBody", "BelowContentBodyProbe"
        )
        self.set_debug(True)
        with self.assertLogs(MANAGERS_LOGGER, level="WARNING") as logs:
            self.render(self.doc, "pagelet_view")
        message = "\n".join(logs.output)
        self.assertIn("probe.belowcontentbody", message)
        self.assertIn("tests.viewlet_fixtures", message)
        self.assertIn("plone.belowcontentbody", message)
        self.assertIn("ILayoutManager", message)
        self.assertIn("docs/porting-main-template.md", message)

    def test_hidden_stock_viewlets_are_silent(self):
        # Nothing to port: a hidden viewlet never renders, so it must not
        # ask anyone to port it.
        self.set_debug(True)
        with self.assertLogs(MANAGERS_LOGGER, level="WARNING") as logs:
            self.render(self.doc, "pagelet_view")
        message = "\n".join(logs.output)
        for viewlet in (
            "plone.colophon",
            "plone.site_actions",
            "plone.path_bar",
            "plone.documentbyline",
        ):
            with self.subTest(viewlet=viewlet):
                self.assertNotIn(f"Viewlet {viewlet} ", message)

    def test_our_own_elements_are_silent(self):
        # The layout's own elements live in ILayoutManager, which is not a
        # bridge — they are already where the message asks viewlets to go.
        self.set_debug(True)
        with self.assertLogs(MANAGERS_LOGGER, level="WARNING") as logs:
            self.render(self.doc, "pagelet_view")
        message = "\n".join(logs.output)
        for element in ELEMENTS:
            with self.subTest(element=element):
                self.assertNotIn(f"Viewlet {element} ", message)


class TestBridgeRegistrationParity(ManagerBridgeTestCase):
    """The sibling bridges are ordinary elements — three sources agree."""

    def test_every_sibling_bridge_is_a_layout_element(self):
        missing = sorted(set(SIBLING_MANAGERS) - set(ELEMENTS))
        self.assertEqual(
            missing,
            [],
            "a bridge with no entry in layout.ELEMENTS is never rendered",
        )

    def test_zcml_manager_names_match_the_table(self):
        # managers.zcml carries manager_name="…" per stanza; SIBLING_MANAGERS
        # is the same mapping in Python (the ratchet reads it). They must
        # not drift.
        view = self.doc.restrictedTraverse("pagelet_view")
        for element, manager_name in sorted(SIBLING_MANAGERS.items()):
            with self.subTest(element=element):
                provider = getMultiAdapter(
                    (self.doc, self.request, view), IContentProvider, name=element
                )
                self.assertEqual(provider.manager_name, manager_name)

    def test_rendered_managers_covers_both_bridge_kinds(self):
        self.assertTrue(set(SIBLING_MANAGERS.values()) <= RENDERED_MANAGERS)
        self.assertTrue(set(CONTENT_HEADER_MANAGERS.values()) <= RENDERED_MANAGERS)
        # ... plus the two that were already rendered before managers.py
        self.assertIn("plone.globalstatusmessage", RENDERED_MANAGERS)
        self.assertIn("plone.toolbar", RENDERED_MANAGERS)

    def test_bridges_are_hideable_like_any_other_element(self):
        # Storage-managed: hiding a bridge in @@manage-layout-viewlets takes
        # its viewlets off the page, exactly as it does for our own chrome.
        self.register_probe(
            "probe.belowcontentbody", "IBelowContentBody", "BelowContentBodyProbe"
        )
        self.assertIn("probe-belowcontentbody", self.render(self.doc, "pagelet_view"))

        manage = self.doc.restrictedTraverse("@@manage-layout-viewlets")
        manage.hide("plone.pageletlayout.layout", "plone.pageletlayout.belowcontentbody")
        self.addCleanup(
            manage.show,
            "plone.pageletlayout.layout",
            "plone.pageletlayout.belowcontentbody",
        )
        # No commit: the render below runs in this connection and sees the
        # write. Committing here would try to persist the site's local
        # component registry, whose cache now holds the ZCML-synthesized
        # probe class — a test artifact, not a product path.
        self.assertNotIn("probe-belowcontentbody", self.render(self.doc, "pagelet_view"))
