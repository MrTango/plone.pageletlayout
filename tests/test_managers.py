"""Functional tests for the slots: the stock viewlet managers the frame
renders, and the layout elements assigned to them.

* viewlets registered into the stock managers render in their classic
  positions (and view-bound ones bind to the published view);
* the stock viewlets our elements replace render exactly once, because the
  profile hides them;
* a viewlet registered both in a stock manager and as an element renders
  once;
* @@manage-layout-viewlets orders, hides and assigns per slot.
"""

import re
import unittest

import transaction
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.configuration import xmlconfig
from zope.interface import Interface
from zope.viewlet.interfaces import IViewlet

from plone import api
from plone.app.layout.viewlets import interfaces as stock_managers
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.interfaces import IPlonePageletlayoutLayer
from plone.pageletlayout.pagelets.layout import ILayoutManager
from plone.pageletlayout.pagelets.managers import RENDERED_MANAGERS
from plone.pageletlayout.pagelets.slots import assign
from plone.pageletlayout.pagelets.slots import ASSIGNMENTS_RECORD
from plone.pageletlayout.pagelets.slots import DEFAULT_ASSIGNMENTS
from plone.pageletlayout.pagelets.slots import SLOTS
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


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

LAYOUT_STANZA = """\
  <browser:viewlet
      name="{name}"
      manager="plone.pageletlayout.pagelets.layout.ILayoutManager"
      class="tests.viewlet_fixtures.{class_}"
      layer="plone.pageletlayout.interfaces.IPlonePageletlayoutLayer"
      permission="zope2.View"
      />
"""

DEFAULT_VIEW = "zope.browser.interfaces.IBrowserView"
EDIT_FORM_VIEW = "plone.dexterity.interfaces.IDexterityEditForm"


class SlotTestCase(unittest.TestCase):
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

    def register_layout_element(self, name, class_):
        """Register the same probe as a layout element — the ported half of
        a dual registration. No order entry: an unordered viewlet renders at
        the end of the layout, which is enough to count it."""
        xmlconfig.string(ZCML_WRAPPER.format(LAYOUT_STANZA.format(name=name, class_=class_)))
        self.addCleanup(
            getGlobalSiteManager().unregisterAdapter,
            required=(
                Interface,
                IPlonePageletlayoutLayer,
                Interface,
                ILayoutManager,
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


class TestSlotsRender(SlotTestCase):
    """A viewlet registered into a slot's manager reaches the page."""

    def test_slots_render_their_viewlets(self):
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

    def test_slots_keep_the_classic_positions(self):
        # A slot is only useful if it puts the viewlet where the add-on
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

    def test_content_header_slots_render_inside_the_content_header(self):
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

    def test_empty_slot_renders_nothing_at_all(self):
        # No landmark is left behind empty when its slots render nothing.
        html = self.render(self.doc, "pagelet_view")
        self.assertIsNone(re.search(r"<(header|footer)\b[^>]*>\s*</\1>", html))

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


class TestStockDuplicatesRenderOnce(SlotTestCase):
    """Rendering the stock managers without hiding would double the chrome
    our elements reimplement."""

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
        # visible and reaches the page through the portalheader slot.
        #
        # It still renders nothing here: membertools.pt is gated on
        # ``not is_toolbar_visible``, and the pagelet layout always renders
        # the toolbar. Leaving it unhidden is what matters — the day a site
        # turns the toolbar off, the personal bar appears instead of staying
        # lost.
        storage = getUtility(IViewletSettingsStorage)
        self.assertNotIn(
            "plone.membertools", storage.getHidden("plone.portalheader", SKINNAME)
        )

    def test_footer_portlets_reach_the_page(self):
        # plone.footer renders the footer portlet manager, which had no way
        # onto a pagelet page before the portalfooter slot. Plone's
        # own default assignments there are a colophon and a site-actions
        # portlet, so a stock site now shows those *alongside* our colophon
        # and siteactions elements: our elements are the clean
        # reimplementation and stay, the portlet assignments are site data an
        # integrator removes (docs/porting-main-template.md).
        html = self.render(self.doc, "pagelet_view")
        self.assertIn("portletWrapper", html.split('id="portal-footer-wrapper"', 1)[1])
        self.assertEqual(html.count('id="portal-colophon"'), 1)


class TestDualRegistration(SlotTestCase):
    """A viewlet registered in a stock manager *and* as a layout element
    under the same name renders once: the stock registration wins over the
    assigned twin (plone.app.viewletmanager's IAdditionalViewlets rule)."""

    NAME = "probe.portalfooter"
    CLASS = "PortalFooterProbe"
    #: One per render: the probe's marker text appears twice per render.
    MARKER = 'class="probe-portalfooter"'

    def test_the_dual_registered_viewlet_renders_exactly_once(self):
        self.register_probe(self.NAME, "IPortalFooter", self.CLASS)
        self.register_layout_element(self.NAME, self.CLASS)
        assign(self.NAME, "plone.portalfooter")
        html = self.render(self.doc, "pagelet_view")
        self.assertEqual(html.count(self.MARKER), 1)

    def test_an_assigned_element_renders_in_its_slot(self):
        self.register_layout_element(self.NAME, self.CLASS)
        assign(self.NAME, "plone.portalfooter")
        html = self.render(self.doc, "pagelet_view")
        footer = html.split('id="portal-footer-wrapper"', 1)[1]
        self.assertIn(self.MARKER, footer)

    def test_an_unassigned_element_does_not_render(self):
        self.register_layout_element(self.NAME, self.CLASS)
        self.assertNotIn(self.MARKER, self.render(self.doc, "pagelet_view"))


class TestManageLayoutViewlets(SlotTestCase):
    """@@manage-layout-viewlets orders, hides and assigns per slot."""

    def manage(self, **form):
        self.request.form.update(form)
        for key, value in form.items():
            self.request.other[key] = value
        return self.doc.restrictedTraverse("@@manage-layout-viewlets")

    def test_rendered_managers_are_the_slots(self):
        self.assertTrue(set(SLOTS) <= RENDERED_MANAGERS)
        self.assertIn("plone.globalstatusmessage", RENDERED_MANAGERS)
        self.assertIn("plone.toolbar", RENDERED_MANAGERS)

    def test_every_slot_lists_its_elements(self):
        slots = {slot["name"]: slot for slot in self.manage().slots()}
        self.assertEqual(list(slots), list(SLOTS))
        for name, slot in DEFAULT_ASSIGNMENTS.items():
            with self.subTest(name=name):
                rows = {row["name"]: row for row in slots[slot]["rows"]}
                self.assertTrue(rows[name]["is_element"])

    def test_stock_viewlets_cannot_change_slot(self):
        slots = {slot["name"]: slot for slot in self.manage().slots()}
        rows = {row["name"]: row for row in slots["plone.portalfooter"]["rows"]}
        self.assertFalse(rows["plone.footer"]["is_element"])

    def test_assign_moves_an_element(self):
        self.manage(
            action="assign", viewlet="plone.pageletlayout.colophon", slot="plone.portalheader"
        )()
        self.assertEqual(
            api.portal.get_registry_record(ASSIGNMENTS_RECORD)["plone.pageletlayout.colophon"],
            "plone.portalheader",
        )

    def test_assign_rejects_an_unknown_slot(self):
        self.manage(
            action="assign", viewlet="plone.pageletlayout.colophon", slot="plone.htmlhead"
        )()
        self.assertEqual(
            api.portal.get_registry_record(ASSIGNMENTS_RECORD)["plone.pageletlayout.colophon"],
            "plone.portalfooter",
        )

    def test_unassigned_elements_are_listed(self):
        assign("plone.pageletlayout.colophon", None)
        self.assertIn("plone.pageletlayout.colophon", self.manage().unassigned())

    def test_hide_is_scoped_to_the_slot(self):
        self.manage(
            action="hide", manager="plone.portalfooter", viewlet="plone.pageletlayout.colophon"
        )()
        storage = getUtility(IViewletSettingsStorage)
        self.assertIn(
            "plone.pageletlayout.colophon", storage.getHidden("plone.portalfooter", SKINNAME)
        )
        self.assertNotIn('id="portal-colophon"', self.render(self.doc, "pagelet_view"))

    def test_the_screen_renders(self):
        html = self.manage()()
        for slot in SLOTS:
            with self.subTest(slot=slot):
                self.assertIn(f'data-slot="{slot}"', html)
