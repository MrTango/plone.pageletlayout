"""Render tests for the shared folderish listing views (wayfinder ticket 12).

The five folderish formats — ``listing_view`` / ``summary_view`` /
``tabular_view`` / ``full_view`` / ``album_view`` — render Folder, Collection
and the site root through the whole-body pagelet layout, delegating the data to
Plone's own ``FolderView`` / ``CollectionView`` and emitting the reused ticket-10
hooks (``.entries`` / ``.item`` / ``.summary`` / ``.card`` / ``.table`` /
``.album``) with the Bootstrap utility soup stripped. These tests build a folder
of mixed content and a collection, then render every format end to end, asserting
the hooks land, the item data shows and no TAL error escapes.
"""

import base64
import unittest

import transaction

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.textfield.value import RichTextValue
from plone.namedfile.file import NamedBlobImage
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


# A real 1x1 PNG so the Image type's scale machinery works in album_view.
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class FolderishViewTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        # A folder with mixed content: a document (with body, for full_view),
        # a sub-folder (a container child) and an image (for album_view).
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="a-folder", title="A Folder"
        )
        self.doc = api.content.create(
            container=self.folder,
            type="Document",
            id="a-doc",
            title="Child Document",
            description="A child description",
            text=RichTextValue("<p>The document body text.</p>", "text/html", "text/x-html-safe"),
        )
        api.content.create(
            container=self.folder, type="Folder", id="a-subfolder", title="Child Folder"
        )
        api.content.create(
            container=self.folder,
            type="Image",
            id="an-image",
            title="Child Image",
            image=NamedBlobImage(data=PNG_1x1, filename="pixel.png", contentType="image/png"),
        )
        # A collection selecting the documents in the site.
        self.collection = api.content.create(
            container=self.portal,
            type="Collection",
            id="a-collection",
            title="A Collection",
            query=[
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.any",
                    "v": ["Document"],
                }
            ],
        )
        transaction.commit()

    def _render(self, obj, view_name):
        return obj.restrictedTraverse(view_name)()

    def _assert_shell(self, html, title):
        # every format renders through the shared whole-body pagelet layout
        self.assertIn('class="plone-layout"', html)
        self.assertIn("element-body", html)
        self.assertIn('id="content-core"', html)
        self.assertIn(title, html)


class TestListingView(FolderishViewTestCase):
    def test_folder_listing(self):
        html = self._render(self.folder, "listing_view")
        self._assert_shell(html, "A Folder")
        self.assertIn('class="entries"', html)
        self.assertIn('class="item"', html)
        self.assertIn('class="url"', html)
        self.assertIn("Child Document", html)

    def test_collection_listing(self):
        html = self._render(self.collection, "listing_view")
        self._assert_shell(html, "A Collection")
        self.assertIn('class="entries"', html)
        # the collection's query selects the child document
        self.assertIn("Child Document", html)


class TestSummaryView(FolderishViewTestCase):
    def test_folder_summary(self):
        html = self._render(self.folder, "summary_view")
        self._assert_shell(html, "A Folder")
        self.assertIn('class="entries"', html)
        self.assertIn('class="summary"', html)
        self.assertIn("summary url", html)
        self.assertIn("read-more", html)
        self.assertIn("Child Document", html)


class TestTabularView(FolderishViewTestCase):
    def test_folder_tabular(self):
        html = self._render(self.folder, "tabular_view")
        self._assert_shell(html, "A Folder")
        self.assertIn('class="table table-striped"', html)
        self.assertIn("<thead>", html)
        self.assertIn("Child Document", html)


class TestFullView(FolderishViewTestCase):
    def test_folder_full(self):
        html = self._render(self.folder, "full_view")
        self._assert_shell(html, "A Folder")
        self.assertIn('class="entries"', html)
        self.assertIn('class="item"', html)
        self.assertIn("Child Document", html)
        # full_view stacks each item's OWN body pagelet (the document's text)
        self.assertIn("The document body text.", html)


class TestAlbumView(FolderishViewTestCase):
    def test_folder_album(self):
        html = self._render(self.folder, "album_view")
        self._assert_shell(html, "A Folder")
        self.assertIn("entries album", html)
        self.assertIn('class="card"', html)
        self.assertIn("card-body", html)
        # the image child is an album tile; the sub-folder is a .card.album tile
        self.assertIn("Child Image", html)
        self.assertIn("card album", html)
        self.assertIn("Child Folder", html)


class TestSiteRootListing(FolderishViewTestCase):
    def test_site_root_listing_renders(self):
        html = self._render(self.portal, "listing_view")
        self.assertIn('class="plone-layout"', html)
        self.assertIn('class="entries"', html)
        # the folder and collection are top-level children of the site root
        self.assertIn("A Folder", html)


ALL_FORMATS = ("listing_view", "summary_view", "tabular_view", "full_view", "album_view")


class TestEveryFormatRenders(FolderishViewTestCase):
    """The load-bearing case: every format renders end to end through both data
    paths (FolderView for folder/site root, CollectionView for the collection)
    with the shared shell and no TAL error."""

    def test_collection_renders_every_format(self):
        for name in ALL_FORMATS:
            html = self._render(self.collection, name)
            self._assert_shell(html, "A Collection")

    def test_site_root_renders_every_format(self):
        for name in ALL_FORMATS:
            html = self._render(self.portal, name)
            self.assertIn('class="plone-layout"', html)
            self.assertIn("element-body", html)


class TestDefaultViews(FolderishViewTestCase):
    """The GS half: the site root defaults to the shared listing_view, and the
    stock Folder/Collection defaults (already listing_view) resolve to our
    pagelet views on this layer."""

    def test_site_root_fti_defaults_to_listing_view(self):
        fti = self.portal.portal_types["Plone Site"]
        self.assertEqual(fti.default_view, "listing_view")
        for name in ("listing_view", "summary_view", "tabular_view", "full_view", "album_view"):
            self.assertIn(name, fti.view_methods)

    def test_folder_default_view_renders_pagelet_layout(self):
        # visiting the folder with no view name renders the whole-body pagelet
        # layout (default_view listing_view → our shadowing pagelet).
        html = self.folder()
        self.assertIn('class="plone-layout"', html)
        self.assertIn('class="entries"', html)
        self.assertIn("element-body", html)
