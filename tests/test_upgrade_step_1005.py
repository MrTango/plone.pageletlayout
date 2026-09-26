"""Upgrade step 1004 -> 1005: the content header becomes a layout element."""

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
NAME = "plone.pageletlayout.contentheader"
SLOT = "plone.abovecontentbody"


class TestUpgrade1005:
    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.setup_tool = self.portal.portal_setup
        self.storage = getUtility(IViewletSettingsStorage)
        self.simulate_1004_site()

    def simulate_1004_site(self):
        assignments = dict(api.portal.get_registry_record(ASSIGNMENTS_RECORD))
        del assignments[NAME]
        assignments["acme.banner"] = "plone.portalfooter"
        api.portal.set_registry_record(ASSIGNMENTS_RECORD, assignments)
        order = self.storage.getOrder(SLOT, SKINNAME)
        self.storage.setOrder(SLOT, SKINNAME, tuple(n for n in order if n != NAME))
        self.setup_tool.setLastVersionForProfile(PROFILE, "1004")

    def test_the_content_header_is_assigned(self):
        self.setup_tool.upgradeProfile(PROFILE)
        assert api.portal.get_registry_record(ASSIGNMENTS_RECORD)[NAME] == SLOT

    def test_other_assignments_are_kept(self):
        self.setup_tool.upgradeProfile(PROFILE)
        assignments = api.portal.get_registry_record(ASSIGNMENTS_RECORD)
        assert assignments["acme.banner"] == "plone.portalfooter"
        for name, slot in DEFAULT_ASSIGNMENTS.items():
            assert assignments[name] == slot

    def test_it_comes_first_in_its_slot(self):
        self.setup_tool.upgradeProfile(PROFILE)
        assert self.storage.getOrder(SLOT, SKINNAME)[0] == NAME

    def test_profile_version(self):
        self.setup_tool.upgradeProfile(PROFILE)
        assert self.setup_tool.getLastVersionForProfile(PROFILE) == ("1005",)
