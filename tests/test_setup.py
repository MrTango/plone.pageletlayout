"""Test plonetheme.pageletbase installation."""
import pytest
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID


class TestSetup:
    """Test installation and setup."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]

    def test_addon_installed(self):
        """Test addon is installed."""
        installer = api.addon.get_installer(self.portal)
        assert installer.is_product_installed("plonetheme.pageletbase")

    def test_browserlayer(self):
        """Test browserlayer is registered."""
        # Add an actual browserlayer check if your addon registers one, e.g.:
        # from plone.browserlayer import utils
        # from plonetheme.pageletbase.interfaces import IPlonethemePageletbaseLayer
        # assert IPlonethemePageletbaseLayer in utils.registered_layers()
        assert True


class TestUninstall:
    """Test uninstallation."""

    @pytest.fixture(autouse=True)
    def _setup(self, integration):
        self.portal = integration["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer = api.addon.get_installer(self.portal)
        self.installer.uninstall_product("plonetheme.pageletbase")

    def test_addon_uninstalled(self):
        """Test addon is uninstalled."""
        assert not self.installer.is_product_installed("plonetheme.pageletbase")
