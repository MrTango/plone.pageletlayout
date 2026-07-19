"""Render tests for the full-screen folder_contents pagelet.

``folder_contents`` — the pat-structure management UI — is the first view
shipped through the full-screen recipe (docs/directives.md): the published
pagelet carries ``IFullScreenPagelet`` via its registration's ``provides=``,
which flips the ``plone.pageletlayout.pagelayout`` region provider to
``BodyOnlyRegion`` — the body element alone, no logo/nav/breadcrumbs/footer,
while the ``<head>`` plumbing stays with the shell. The options JSON delegates
to the stock ``FolderContentsView``. These tests pin the shipped wiring; the
directive mechanics themselves are pinned by
``test_directives.TestChromePageletViewDimension``.
"""

import unittest

import transaction
from AccessControl import Unauthorized

from plone import api
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.interfaces import IFullScreenPagelet
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


class FolderContentsTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="a-folder", title="A Folder"
        )
        api.content.create(
            container=self.folder, type="Document", id="a-doc", title="Child Document"
        )
        transaction.commit()


class TestFolderContentsView(FolderContentsTestCase):
    def test_view_is_the_fullscreen_pagelet(self):
        view = self.folder.restrictedTraverse("folder_contents")
        self.assertTrue(IFullScreenPagelet.providedBy(view))

    def test_renders_pat_structure_through_the_shell(self):
        html = self.folder.restrictedTraverse("folder_contents")()
        # the shared shell: head plumbing + the layout container + body element
        self.assertIn('<meta name="generator"', html)
        self.assertIn('class="plone-layout"', html)
        self.assertIn('id="content-core"', html)
        # the management UI boot: CSRF token + the pattern div with the
        # stock FolderContentsView's options JSON
        self.assertIn('name="_authenticator"', html)
        self.assertIn("pat-structure", html)
        self.assertIn("data-pat-structure", html)
        self.assertIn("urlStructure", html)
        self.assertIn("folder_contents", html)

    def test_fullscreen_region_drops_the_chrome(self):
        html = self.folder.restrictedTraverse("folder_contents")()
        # body-only: no logo, no navigation, no footer rows
        self.assertNotIn("element-logo", html)
        self.assertNotIn("element-globalnav", html)
        self.assertNotIn("element-breadcrumbs", html)
        self.assertNotIn("element-colophon", html)

    def test_regular_views_keep_the_managed_region(self):
        # the region shadow is scoped to the marker: an ordinary published
        # pagelet on the same layer still renders the full managed layout
        html = self.folder.restrictedTraverse("listing_view")()
        self.assertIn("element-logo", html)
        self.assertIn("element-colophon", html)

    def test_site_root_folder_contents_renders(self):
        html = self.portal.restrictedTraverse("folder_contents")()
        self.assertIn("pat-structure", html)
        self.assertIn('class="plone-layout"', html)

    def test_anonymous_is_unauthorized(self):
        logout()
        with self.assertRaises(Unauthorized):
            self.folder.restrictedTraverse("folder_contents")
