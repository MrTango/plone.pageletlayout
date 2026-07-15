"""Render tests for the per-item content views (wayfinder ticket 11).

Each of the five remaining default types (News Item, Event, File, Image, Link)
gets ``pagelet_view`` as its default view, rendering its content-core through a
body-only content pagelet that reuses Plone's own per-type hooks. These tests
create one instance of every type and render the whole-body pagelet layout end
to end, asserting the type-appropriate hooks land and no TAL error escapes.
"""

import base64
import unittest
from datetime import datetime
from datetime import timedelta

import pytz
import transaction

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.textfield.value import RichTextValue
from plone.namedfile.file import NamedBlobFile
from plone.namedfile.file import NamedBlobImage
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


# A real 1x1 PNG so Image's ``getImageSize()`` / scale machinery work.
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class ContentViewTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

    def _render(self, obj):
        return obj.restrictedTraverse("pagelet_view")()

    def _create(self, **kw):
        obj = api.content.create(container=self.portal, **kw)
        transaction.commit()
        return obj

    # -- the shared shell + title chrome is present for every type ---------
    def _assert_shell(self, html, title):
        self.assertIn('class="plone-layout"', html)
        self.assertIn("element-body", html)
        self.assertIn('id="content-core"', html)
        self.assertIn(title, html)


class TestNewsItemView(ContentViewTestCase):
    def test_renders_text_core(self):
        obj = self._create(
            type="News Item",
            id="a-news",
            title="Breaking News",
            text=RichTextValue("<p>The news body.</p>", "text/html", "text/x-html-safe"),
        )
        html = self._render(obj)
        self._assert_shell(html, "Breaking News")
        self.assertIn('id="section-text"', html)
        self.assertIn("parent-fieldname-text", html)
        self.assertIn("The news body.", html)


class TestEventView(ContentViewTestCase):
    def test_renders_event_core(self):
        # Real events carry a pytz timezone (plone.event's recurrence calls
        # tz.localize()); a tz-naive or stdlib-tz start fails the same way in
        # classic ``event_view``.
        start = pytz.timezone("UTC").localize(datetime(2026, 8, 1, 10, 0))
        obj = self._create(
            type="Event",
            id="an-event",
            title="Plone Conf",
            start=start,
            end=start + timedelta(hours=2),
            timezone="UTC",
        )
        html = self._render(obj)
        self._assert_shell(html, "Plone Conf")
        # our own schema.org wrapper hook + the reused @@event_summary output
        self.assertIn('class="event plone-stack"', html)


class TestFileView(ContentViewTestCase):
    def test_renders_download_ui(self):
        obj = self._create(
            type="File",
            id="a-file",
            title="A File",
            file=NamedBlobFile(
                data=b"hello world",
                filename="notes.txt",
                contentType="text/plain",
            ),
        )
        html = self._render(obj)
        self._assert_shell(html, "A File")
        self.assertIn("section-main", html)
        self.assertIn("section-actions", html)
        self.assertIn("notes.txt", html)
        self.assertIn("text/plain", html)
        self.assertIn("btn btn-primary download", html)


class TestImageView(ContentViewTestCase):
    def test_renders_figure_and_actions(self):
        obj = self._create(
            type="Image",
            id="an-image",
            title="An Image",
            image=NamedBlobImage(data=PNG_1x1, filename="pixel.png", contentType="image/png"),
        )
        html = self._render(obj)
        self._assert_shell(html, "An Image")
        self.assertIn('class="figure"', html)
        self.assertIn("section-actions", html)
        self.assertIn("pixel.png", html)
        self.assertIn("1x1", html)
        self.assertIn("fullscreen", html)


class TestLinkView(ContentViewTestCase):
    def test_renders_target_link(self):
        obj = self._create(
            type="Link",
            id="a-link",
            title="A Link",
            remoteUrl="https://plone.org",
        )
        html = self._render(obj)
        self._assert_shell(html, "A Link")
        self.assertIn("link-title", html)
        self.assertIn("https://plone.org", html)


class TestDefaultViewFlip(ContentViewTestCase):
    """The GS profile half: every per-item type's FTI now defaults to the
    whole-body ``pagelet_view`` (the classic view stays addressable)."""

    TYPES = ("News Item", "Event", "File", "Image", "Link")

    def test_ftis_default_to_pagelet_view(self):
        types_tool = self.portal.portal_types
        for type_name in self.TYPES:
            fti = types_tool[type_name]
            self.assertEqual(
                fti.default_view,
                "pagelet_view",
                f"{type_name} FTI must default to pagelet_view",
            )
            self.assertIn("pagelet_view", fti.view_methods)

    def test_document_default_view_traverses_to_pagelet_layout(self):
        # The user-facing path: visiting the object with no view name renders
        # the whole-body pagelet layout (not just the explicit @@pagelet_view).
        obj = self._create(type="News Item", id="dv-news", title="Default View")
        html = obj()
        self.assertIn('class="plone-layout"', html)
        self.assertIn("element-body", html)
        self.assertIn("Default View", html)
