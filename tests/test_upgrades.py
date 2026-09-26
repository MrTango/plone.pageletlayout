"""Upgrade steps: the 1002 -> 1003 viewlets re-import.

An installed site keeps the hidden set it imported at install time, so the
hidden stock duplicates only reach it through this step. Two things matter:
it actually applies the new profile state, and re-running it changes nothing
(GenericSetup import steps are re-run whenever an integrator reinstalls).
"""

import unittest

from zope.component import getUtility

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.testing import INTEGRATION_TESTING
from plone.pageletlayout.upgrades.v1003 import upgrade


SKINNAME = "Plone Default"

class TestViewletsUpgrade(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.setup_tool = self.portal.portal_setup
        self.storage = getUtility(IViewletSettingsStorage)

    def hidden(self, manager):
        return set(self.storage.getHidden(manager, SKINNAME))

    def test_upgrade_restores_the_hidden_set(self):
        # Simulate a 1002 site: nothing hidden.
        self.storage.setHidden("plone.portalfooter", SKINNAME, ())
        upgrade(self.setup_tool)
        self.assertIn("plone.colophon", self.hidden("plone.portalfooter"))

    def test_upgrade_is_idempotent(self):
        upgrade(self.setup_tool)
        once = self.hidden("plone.portalfooter")
        upgrade(self.setup_tool)
        self.assertEqual(self.hidden("plone.portalfooter"), once)

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
