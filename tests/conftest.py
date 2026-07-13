"""Pytest configuration for plonetheme.pageletbase tests."""
from pytest_plone import fixtures_factory

from plonetheme.pageletbase.testing import FUNCTIONAL_TESTING
from plonetheme.pageletbase.testing import INTEGRATION_TESTING


globals().update(
    fixtures_factory(
        (
            (INTEGRATION_TESTING, "integration"),
            (FUNCTIONAL_TESTING, "functional"),
        )
    )
)
