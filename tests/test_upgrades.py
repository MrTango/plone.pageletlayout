"""Upgrade steps: the 1002 -> 1003 viewlets re-import.

An installed site keeps the viewlet order and hidden set it imported at
install time, so the bridge elements and the hidden stock duplicates only
reach it through this step. Two things matter: it actually applies the new
profile state, and re-running it changes nothing (GenericSetup import steps
are re-run whenever an integrator reinstalls).
"""

import unittest

from zope.component import getUtility

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.pagelets.layout import ELEMENTS
from plone.pageletlayout.pagelets.layout import MANAGER_NAME
from plone.pageletlayout.pagelets.managers import SIBLING_MANAGERS
from plone.pageletlayout.testing import INTEGRATION_TESTING
from plone.pageletlayout.upgrades.v1003 import upgrade


SKINNAME = "Plone Default"

#: What the step has to put back: the bridge elements in the order, and one
#: representative hidden set. Derived, not restated — a bridge added to
#: managers.py must not need a second edit here to stay covered.
BRIDGE_ELEMENTS = tuple(SIBLING_MANAGERS)


class TestViewletsUpgrade(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.setup_tool = self.portal.portal_setup
        self.storage = getUtility(IViewletSettingsStorage)

    def order(self):
        return tuple(self.storage.getOrder(MANAGER_NAME, SKINNAME))

    def hidden(self, manager):
        return set(self.storage.getHidden(manager, SKINNAME))

    def test_profile_version_is_1003(self):
        self.assertEqual(
            self.setup_tool.getLastVersionForProfile("plone.pageletlayout:default"),
            ("1003",),
        )

    def test_upgrade_restores_the_order_and_the_hidden_set(self):
        # Simulate a 1002 site: the pre-bridge order, nothing hidden.
        pre_bridge = tuple(
            name for name in ELEMENTS if name not in BRIDGE_ELEMENTS
        )
        self.storage.setOrder(MANAGER_NAME, SKINNAME, pre_bridge)
        self.storage.setHidden("plone.portalfooter", SKINNAME, ())
        self.assertNotIn("plone.pageletlayout.portalfooter", self.order())

        upgrade(self.setup_tool)

        self.assertEqual(self.order(), ELEMENTS)
        self.assertIn("plone.colophon", self.hidden("plone.portalfooter"))

    def test_upgrade_is_idempotent(self):
        upgrade(self.setup_tool)
        once = (self.order(), self.hidden("plone.portalfooter"))
        upgrade(self.setup_tool)
        self.assertEqual((self.order(), self.hidden("plone.portalfooter")), once)

    def test_upgrade_does_not_apply_the_whole_profile(self):
        # Narrowed on purpose: a whole-profile reload would replay types,
        # registry and rolemap over a site's own customisations. What this
        # pins is the coarse half of that — the handler runs one import step,
        # it does not re-apply the profile (which would also restamp the
        # recorded version).
        before = self.setup_tool.getLastVersionForProfile(
            "plone.pageletlayout:default"
        )
        upgrade(self.setup_tool)
        self.assertEqual(
            self.setup_tool.getLastVersionForProfile("plone.pageletlayout:default"),
            before,
            "the handler must not apply the profile itself",
        )

    def test_upgrade_leaves_other_import_steps_alone(self):
        # ... and the fine half: a step the handler must not touch keeps the
        # site's own value. The FTI's default_view is profile-owned and
        # trivially observable, so customising it is the cheapest witness.
        fti = self.portal.portal_types["Document"]
        fti.default_view = "customised_view"
        upgrade(self.setup_tool)
        self.assertEqual(
            self.portal.portal_types["Document"].default_view,
            "customised_view",
            "the handler replayed the types step over a site customisation",
        )


class TestForeignElementsSurviveTheReimport(unittest.TestCase):
    """An add-on's own element must not be evicted by our order.

    profiles/default/viewlets.xml restates the whole sequence, and
    GenericSetup applies a restated order by removing each name and appending
    it — so every one of our twenty-one names lands *behind* an element some
    add-on anchored into the middle of the page. plonetheme.clara's
    sub-navigation and collective.blicca.footerblocks' footer were rendered
    above the logo after the 1003 step ran. See upgrades/viewlet_order.py.
    """

    layer = INTEGRATION_TESTING

    #: Two foreign elements at the anchors the real add-ons use: clara's
    #: sub-navigation directly after the body, footerblocks directly before
    #: the first footer row.
    SUBNAV = "plonetheme.clara.subnav"
    FOOTER = "collective.blicca.footerblocks.footerblocks"

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.setup_tool = self.portal.portal_setup
        self.storage = getUtility(IViewletSettingsStorage)

    def order(self):
        return tuple(self.storage.getOrder(MANAGER_NAME, SKINNAME))

    def store(self, order):
        self.storage.setOrder(MANAGER_NAME, SKINNAME, tuple(order))

    def with_foreign_elements(self):
        """The canonical order plus the two foreign elements at their anchors."""
        order = []
        for name in ELEMENTS:
            if name == "plone.pageletlayout.copyright":
                order.append(self.FOOTER)
            order.append(name)
            if name == "plone.pageletlayout.body":
                order.append(self.SUBNAV)
        return order

    def test_foreign_elements_keep_their_place(self):
        self.store(self.with_foreign_elements())

        upgrade(self.setup_tool)

        order = self.order()
        self.assertEqual(
            order.index(self.SUBNAV),
            order.index("plone.pageletlayout.body") + 1,
            "the sub-navigation left its anchor below the body",
        )
        self.assertEqual(
            order.index(self.FOOTER),
            order.index("plone.pageletlayout.copyright") - 1,
            "the footer left its anchor above the footer rows",
        )

    def test_our_own_order_is_still_the_canonical_one(self):
        self.store(self.with_foreign_elements())

        upgrade(self.setup_tool)

        ours = tuple(name for name in self.order() if name in ELEMENTS)
        self.assertEqual(ours, ELEMENTS)

    def test_it_stays_put_over_repeated_reimports(self):
        # Anchors are evaluated against the order as it stands mid-import, so
        # a scheme that re-anchored our own entries would let a foreign
        # element drift one place further on every run. This one does not.
        self.store(self.with_foreign_elements())

        upgrade(self.setup_tool)
        once = self.order()
        upgrade(self.setup_tool)

        self.assertEqual(self.order(), once)

    def test_an_element_ahead_of_ours_stays_ahead(self):
        # Nothing ships one, but the storage allows it: a foreign name with no
        # predecessor belongs at the front, not swept to the back.
        self.store([self.SUBNAV, *ELEMENTS])

        upgrade(self.setup_tool)

        self.assertEqual(self.order()[0], self.SUBNAV)

    def test_a_run_of_foreign_elements_keeps_its_sequence(self):
        first, second = "an.addon.first", "an.addon.second"
        order = []
        for name in ELEMENTS:
            order.append(name)
            if name == "plone.pageletlayout.body":
                order.extend([first, second])
        self.store(order)

        upgrade(self.setup_tool)

        restored = self.order()
        self.assertEqual(
            restored[restored.index("plone.pageletlayout.body") + 1 :][:2],
            (first, second),
        )
