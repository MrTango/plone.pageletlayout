"""Pytest configuration for plone.pageletlayout tests."""
from pytest_plone import fixtures_factory

from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.pageletlayout.testing import INTEGRATION_TESTING


globals().update(
    fixtures_factory(
        (
            (INTEGRATION_TESTING, "integration"),
            (FUNCTIONAL_TESTING, "functional"),
        )
    )
)
