"""Directive-grammar tests (pagelet-directive-grammar map, ticket 03).

The seam is the ZCML itself: each test loads a stanza through the package's
``meta.zcml`` exactly the way an add-on would, then observes the registered
component through traversal and adapter lookup — never through the handler
internals. Registrations land in the layer's stacked component registry and
use unique per-ticket names (``ticket03-*``, ``ticket05-*``, ``ticket07-*``)
so they cannot shadow package registrations.
"""

import os.path
import unittest

from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.configuration import xmlconfig
from zope.configuration.config import ConfigurationConflictError
from zope.configuration.exceptions import ConfigurationError
from zope.contentprovider.interfaces import IContentProvider

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.interfaces import IPageLayout
from plone.pageletlayout.testing import INTEGRATION_TESTING


FIXTURES = os.path.join(os.path.dirname(__file__), "directive_fixtures")

ZCML_WRAPPER = """\
<configure
    xmlns="http://namespaces.zope.org/zope"
    xmlns:plone="http://namespaces.plone.org/plone">
  <include package="plone.pageletlayout" file="meta.zcml" />
  {}
</configure>
"""


def load(snippet):
    """Load a directive snippet through the package's meta.zcml.

    ``{fixtures}`` expands to the absolute path of the fixture-template
    directory. Each call uses a fresh configuration machine, so conflict
    detection is per-call — exactly like one add-on's configure.zcml.
    """
    xmlconfig.string(ZCML_WRAPPER.format(snippet.format(fixtures=FIXTURES)))


class DirectiveTestCase(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.doc = api.content.create(
            container=self.portal, type="Document", id="doc", title="Doc"
        )


class TestTemplateOnlyPagelet(DirectiveTestCase):
    """<plone:pagelet template=... /> without class synthesizes the pagelet."""

    def test_template_only_pagelet_renders_in_frame(self):
        load("""
          <plone:pagelet
              name="ticket03-hello"
              template="{fixtures}/hello.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        html = self.doc.restrictedTraverse("ticket03-hello")()
        self.assertIn('id="ticket03-hello"', html)
        self.assertIn('id="ticket03-frame"', html)

    def test_template_only_pagelet_keeps_page_contract(self):
        # The synthesized class must sit on PageletPage (never plain object):
        # response headers and the post-render Diazo bypass still apply.
        load("""
          <plone:pagelet
              name="ticket03-contract"
              template="{fixtures}/hello.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        self.doc.restrictedTraverse("ticket03-contract")()
        response = self.request.response
        self.assertEqual(response.getHeader("X-Theme-Disabled"), "1")
        self.assertIn("text/html", response.getHeader("Content-Type"))
        self.assertTrue(response.getHeader("Content-Language"))


class TestOneStrokePagelet(DirectiveTestCase):
    """<plone:pagelet class=... template=... /> registers both in one stroke."""

    def test_inline_template_renders_for_the_class(self):
        load("""
          <plone:pagelet
              name="ticket03-greeting"
              class="tests.directive_fixtures.GreetingPagelet"
              template="{fixtures}/greeting.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        html = self.doc.restrictedTraverse("ticket03-greeting")()
        self.assertIn("computed-greeting", html)

    def test_inline_template_inherited_by_further_registrations(self):
        # The template binds to the *user's* class, so a second stanza
        # registering the same class under another name — without its own
        # template — inherits it (the chromepagelet subtlety).
        load("""
          <plone:pagelet
              name="ticket03-two"
              class="tests.directive_fixtures.GreetingTwoPagelet"
              template="{fixtures}/greeting.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:pagelet
              name="ticket03-two-alias"
              class="tests.directive_fixtures.GreetingTwoPagelet"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        html = self.doc.restrictedTraverse("ticket03-two-alias")()
        self.assertIn("computed-greeting-two", html)


class TestMultiFor(DirectiveTestCase):
    """for= takes one or more interfaces; one stanza, N registrations."""

    def setUp(self):
        super().setUp()
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="folder", title="Folder"
        )

    def test_one_stanza_registers_for_each_interface(self):
        load("""
          <plone:pagelet
              name="ticket03-multi"
              template="{fixtures}/hello.pt"
              for="plone.app.contenttypes.interfaces.IDocument
                   plone.app.contenttypes.interfaces.IFolder"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        self.assertIn('id="ticket03-hello"', self.doc.restrictedTraverse("ticket03-multi")())
        self.assertIn('id="ticket03-hello"', self.folder.restrictedTraverse("ticket03-multi")())

    def test_conflicts_are_detected_per_interface(self):
        # A second stanza claiming the same name for ONE of the interfaces
        # must conflict — not silently override.
        with self.assertRaises(ConfigurationConflictError):
            load("""
              <plone:pagelet
                  name="ticket03-conflict"
                  template="{fixtures}/hello.pt"
                  for="plone.app.contenttypes.interfaces.IDocument
                       plone.app.contenttypes.interfaces.IFolder"
                  permission="zope2.View"
                  />
              <plone:pagelet
                  name="ticket03-conflict"
                  template="{fixtures}/greeting.pt"
                  for="plone.app.contenttypes.interfaces.IFolder"
                  permission="zope2.View"
                  />
            """)

    def test_same_name_for_disjoint_interfaces_coexists(self):
        # The browser:page rule, kept: conflicts are per (interface, layer,
        # name), so the same name may be claimed for disjoint interfaces —
        # each context gets its own implementation.
        load("""
          <plone:pagelet
              name="ticket03-shared-name"
              class="tests.directive_fixtures.DisjointDocPagelet"
              template="{fixtures}/greeting.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:pagelet
              name="ticket03-shared-name"
              class="tests.directive_fixtures.DisjointFolderPagelet"
              template="{fixtures}/greeting.pt"
              for="plone.app.contenttypes.interfaces.IFolder"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        self.assertIn("disjoint-doc", self.doc.restrictedTraverse("ticket03-shared-name")())
        self.assertIn(
            "disjoint-folder", self.folder.restrictedTraverse("ticket03-shared-name")()
        )


class TestPageletRefusals(DirectiveTestCase):
    """At least one of class= / template= — the directive refuses neither."""

    def test_pagelet_without_class_and_template_is_an_error(self):
        with self.assertRaises(ConfigurationError):
            load("""
              <plone:pagelet
                  name="ticket03-neither"
                  for="plone.app.contenttypes.interfaces.IDocument"
                  permission="zope2.View"
                  />
            """)


class TestTemplateAndLayoutMultiFor(DirectiveTestCase):
    """plone:template / plone:layout expand Tokens for= to N registrations."""

    def test_one_template_stanza_serves_two_classes(self):
        load("""
          <plone:pagelet
              name="ticket03-t-alpha"
              class="tests.directive_fixtures.MultiTemplateAlpha"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:pagelet
              name="ticket03-t-beta"
              class="tests.directive_fixtures.MultiTemplateBeta"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:template
              template="{fixtures}/greeting.pt"
              for="tests.directive_fixtures.MultiTemplateAlpha
                   tests.directive_fixtures.MultiTemplateBeta"
              />
          <plone:layout
              template="{fixtures}/frame.pt"
              for="z3c.pagelet.interfaces.IPagelet"
              />
        """)
        self.assertIn(
            "multi-template-alpha", self.doc.restrictedTraverse("ticket03-t-alpha")()
        )
        self.assertIn(
            "multi-template-beta", self.doc.restrictedTraverse("ticket03-t-beta")()
        )

    def test_one_layout_stanza_serves_two_classes(self):
        # frame2.pt is registered for the two classes only — its id showing
        # up proves the class-specific layout won, not a leaked IPagelet one.
        load("""
          <plone:pagelet
              name="ticket03-l-alpha"
              class="tests.directive_fixtures.MultiLayoutAlpha"
              template="{fixtures}/greeting.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:pagelet
              name="ticket03-l-beta"
              class="tests.directive_fixtures.MultiLayoutBeta"
              template="{fixtures}/greeting.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:layout
              template="{fixtures}/frame2.pt"
              for="tests.directive_fixtures.MultiLayoutAlpha
                   tests.directive_fixtures.MultiLayoutBeta"
              />
        """)
        html_alpha = self.doc.restrictedTraverse("ticket03-l-alpha")()
        html_beta = self.doc.restrictedTraverse("ticket03-l-beta")()
        self.assertIn('id="ticket03-frame2"', html_alpha)
        self.assertIn("multi-layout-alpha", html_alpha)
        self.assertIn('id="ticket03-frame2"', html_beta)
        self.assertIn("multi-layout-beta", html_beta)


class TestChromePageletViewDimension(DirectiveTestCase):
    """view= scopes a chrome part to the published views providing a marker.

    The full-screen recipe in docs/directives.md rests on this: a pagelet
    stanza's provides= puts a marker on the published view, and a second
    chromepagelet stanza with view=<marker> shadows the default registration
    of the same name there — the specific registration wins, everywhere else
    keeps the default, and the provider name never fails to resolve (so no
    ContentProviderLookupError guard is needed in the layout template).
    """

    def test_view_marker_overrides_part_per_published_view(self):
        load("""
          <plone:pagelet
              name="ticket05-fullscreen"
              template="{fixtures}/hello.pt"
              provides="tests.directive_fixtures.IFullScreenPagelet"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:pagelet
              name="ticket05-regular"
              template="{fixtures}/hello.pt"
              for="plone.app.contenttypes.interfaces.IDocument"
              permission="zope2.View"
              />
          <plone:chromepagelet
              name="ticket05-part"
              template="{fixtures}/hello.pt"
              />
          <plone:chromepagelet
              name="ticket05-part"
              class="tests.directive_fixtures.SuppressingChromePagelet"
              view="tests.directive_fixtures.IFullScreenPagelet"
              />
        """)
        from tests.directive_fixtures import IFullScreenPagelet

        regular = self.doc.restrictedTraverse("ticket05-regular")
        fullscreen = self.doc.restrictedTraverse("ticket05-fullscreen")
        self.assertTrue(IFullScreenPagelet.providedBy(fullscreen))

        def part(view):
            provider = getMultiAdapter(
                (self.doc, self.request, view), IContentProvider, name="ticket05-part"
            )
            provider.update()
            return provider.render()

        self.assertIn('id="ticket03-hello"', part(regular))
        self.assertEqual("", part(fullscreen))


class TestChromePageletMultiFor(DirectiveTestCase):
    """plone:chromepagelet takes Tokens for= like the other three."""

    def setUp(self):
        super().setUp()
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="chromefolder", title="Folder"
        )

    def _provider(self, context, name):
        # The provider facet's public contract: looked up as a named
        # IContentProvider on (context, request, view), then update/render —
        # exactly what the provider: expression does.
        view = context.restrictedTraverse("@@plone_context_state")
        provider = getMultiAdapter(
            (context, self.request, view), IContentProvider, name=name
        )
        provider.update()
        return provider.render()

    def test_one_stanza_serves_two_contexts(self):
        load("""
          <plone:chromepagelet
              name="ticket03-chrome"
              template="{fixtures}/hello.pt"
              for="plone.app.contenttypes.interfaces.IDocument
                   plone.app.contenttypes.interfaces.IFolder"
              />
        """)
        self.assertIn('id="ticket03-hello"', self._provider(self.doc, "ticket03-chrome"))
        self.assertIn('id="ticket03-hello"', self._provider(self.folder, "ticket03-chrome"))

    def test_conflicts_are_detected_per_interface(self):
        with self.assertRaises(ConfigurationConflictError):
            load("""
              <plone:chromepagelet
                  name="ticket03-chrome-conflict"
                  template="{fixtures}/hello.pt"
                  for="plone.app.contenttypes.interfaces.IDocument
                       plone.app.contenttypes.interfaces.IFolder"
                  />
              <plone:chromepagelet
                  name="ticket03-chrome-conflict"
                  template="{fixtures}/greeting.pt"
                  for="plone.app.contenttypes.interfaces.IFolder"
                  />
            """)


class TestPageLayoutDirective(DirectiveTestCase):
    """plone:pagelayout binds a layout name to a hand-written layout layer
    (request-layouts map, ticket 07).

    One stanza registers one IPageLayout named utility — utility name =
    layout name — and mistakes surface at ZCML load, never at request time:
    the reserved name 'default', a layer that doesn't extend the package
    browser layer, and a view_marker that doesn't extend IPagelet are each
    config-time errors.
    """

    def _layouts(self):
        return dict(getUtilitiesFor(IPageLayout))

    def test_stanza_lands_in_registry_with_declared_fields(self):
        load("""
          <plone:pagelayout
              name="ticket07-split"
              layer="tests.directive_fixtures.ITicket07SplitLayer"
              view_marker="tests.directive_fixtures.IFullScreenPagelet"
              />
        """)
        from tests.directive_fixtures import IFullScreenPagelet
        from tests.directive_fixtures import ITicket07SplitLayer

        entry = self._layouts()["ticket07-split"]
        self.assertEqual(entry.name, "ticket07-split")
        self.assertIs(entry.layer, ITicket07SplitLayer)
        self.assertIs(entry.view_marker, IFullScreenPagelet)

    def test_view_marker_is_optional(self):
        load("""
          <plone:pagelayout
              name="ticket07-bare"
              layer="tests.directive_fixtures.ITicket07BareLayer"
              />
        """)
        self.assertIsNone(self._layouts()["ticket07-bare"].view_marker)

    def test_reserved_name_default_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            load("""
              <plone:pagelayout
                  name="default"
                  layer="tests.directive_fixtures.ITicket07SplitLayer"
                  />
            """)

    def test_layer_outside_the_package_layer_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            load("""
              <plone:pagelayout
                  name="ticket07-foreign"
                  layer="tests.directive_fixtures.ITicket07ForeignLayer"
                  />
            """)

    def test_view_marker_not_a_pagelet_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            load("""
              <plone:pagelayout
                  name="ticket07-badmarker"
                  layer="tests.directive_fixtures.ITicket07SplitLayer"
                  view_marker="tests.directive_fixtures.ITicket07ForeignLayer"
                  />
            """)

    def test_duplicate_layout_names_conflict(self):
        with self.assertRaises(ConfigurationConflictError):
            load("""
              <plone:pagelayout
                  name="ticket07-dup"
                  layer="tests.directive_fixtures.ITicket07SplitLayer"
                  />
              <plone:pagelayout
                  name="ticket07-dup"
                  layer="tests.directive_fixtures.ITicket07BareLayer"
                  />
            """)
