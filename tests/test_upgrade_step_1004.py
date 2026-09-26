"""Upgrade step 1003 -> 1004: the elements move into the stock managers."""

import pytest
from zope.component import getUtility

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.pagelets.slots import ASSIGNMENTS_RECORD
from plone.pageletlayout.pagelets.slots import DEFAULT_ASSIGNMENTS


PROFILE = "plone.pageletlayout:default"
SKINNAME = "Plone Default"
FLAT_MANAGER = "plone.pageletlayout.layout"


class TestUpgrade1004:
    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.setup_tool = self.portal.portal_setup
        self.storage = getUtility(IViewletSettingsStorage)
        self.simulate_1003_site()

    def simulate_1003_site(self):
        api.portal.get_tool("portal_registry").records.__delitem__(ASSIGNMENTS_RECORD)
        for slot in set(DEFAULT_ASSIGNMENTS.values()):
            order = self.storage.getOrder(slot, SKINNAME)
            self.storage.setOrder(
                slot, SKINNAME, tuple(n for n in order if n not in DEFAULT_ASSIGNMENTS)
            )
        self.storage.setHidden(FLAT_MANAGER, SKINNAME, ("plone.pageletlayout.copyright",))
        self.setup_tool.setLastVersionForProfile(PROFILE, "1003")

    def upgrade(self):
        self.setup_tool.upgradeProfile(PROFILE)

    def test_assignments_are_installed(self):
        self.upgrade()
        assignments = api.portal.get_registry_record(ASSIGNMENTS_RECORD)
        for name, slot in DEFAULT_ASSIGNMENTS.items():
            assert assignments[name] == slot

    def test_elements_get_their_place_in_the_slots(self):
        self.upgrade()
        for name, slot in DEFAULT_ASSIGNMENTS.items():
            assert name in self.storage.getOrder(slot, SKINNAME), name

    def test_hidden_elements_stay_hidden(self):
        self.upgrade()
        hidden = self.storage.getHidden("plone.portalfooter", SKINNAME)
        assert "plone.pageletlayout.copyright" in hidden
        assert "plone.pageletlayout.colophon" not in hidden

    def test_other_import_steps_are_left_alone(self):
        self.portal.portal_types["Document"].default_view = "customised_view"
        self.upgrade()
        assert self.portal.portal_types["Document"].default_view == "customised_view"
