"""Functional tests for the status-messages element.

``plone.globalstatusmessage`` is a viewlet *manager*, not a viewlet: the
queued-message loop is only its first entry. plone.app.dexterity registers
the default-page warning alongside it ("You are editing the default view of
a container", bound to ``view=IDexterityEditForm``), plone.volto its backend
warning. An element that renders only the message loop drops every one of
them — hence these two test cases, one per facet.
"""

import unittest

import transaction
from Products.statusmessages.interfaces import IStatusMessage

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


#: The untranslated default of ``label_edit_default_view_container``
#: (plone/app/layout/viewlets/default_page_warning.pt).
DEFAULT_PAGE_WARNING = "default view of a container"


class StatusMessagesTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="a-folder", title="A Folder"
        )
        self.default_page = api.content.create(
            container=self.folder, type="Document", id="index", title="Index"
        )
        self.folder.setDefaultPage("index")
        self.page = api.content.create(
            container=self.portal, type="Document", id="a-page", title="A Page"
        )
        transaction.commit()

    def render(self, context, name):
        return context.restrictedTraverse(name)()


class TestQueuedMessages(StatusMessagesTestCase):
    """The message loop itself — ``IStatusMessage(request).show()``."""

    def test_message_renders_inside_the_statusmessages_element(self):
        IStatusMessage(self.request).add("Changes saved.")
        html = self.render(self.page, "pagelet_view")
        element = html.index('class="element-statusmessages"')
        self.assertIn("portalMessage", html[element:])
        self.assertIn("Changes saved.", html[element:])

    def test_element_stays_empty_without_messages(self):
        html = self.render(self.page, "pagelet_view")
        self.assertIn('class="element-statusmessages"', html)
        self.assertNotIn("portalMessage", html)


class TestDefaultPageWarning(StatusMessagesTestCase):
    """The manager's *other* viewlets reach the page too."""

    def test_warning_renders_when_editing_a_default_page(self):
        html = self.render(self.default_page, "@@edit")
        element = html.index('class="element-statusmessages"')
        self.assertIn(DEFAULT_PAGE_WARNING, html[element:])
        # ... and links to the container's own edit form
        self.assertIn(f"{self.folder.absolute_url()}/edit", html[element:])

    def test_no_warning_when_editing_an_ordinary_page(self):
        html = self.render(self.page, "@@edit")
        self.assertNotIn(DEFAULT_PAGE_WARNING, html)
