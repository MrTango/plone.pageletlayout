"""Render smoke tests for the whole-body pagelet layout.

Verifies the managed pagelet view renders end-to-end (no TAL errors in the
markup-contract templates), that the stable class hooks the theming contract
guarantees are present, and that the GS default order (viewlets.xml) stays in
parity with the canonical ``layout.ELEMENTS``.
"""

import re
import unittest

import transaction

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.pagelets.layout import ELEMENTS
from plone.pageletlayout.testing import FUNCTIONAL_TESTING


class TestLayoutRender(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.doc = api.content.create(
            container=self.portal,
            type="Document",
            id="a-page",
            title="A Page",
            description="A description",
        )
        transaction.commit()

    def _render(self, view_name):
        view = self.doc.restrictedTraverse(view_name)
        return view()

    def test_managed_view_renders_with_hooks(self):
        html = self._render("pagelet_view")
        # markup-contract hooks (§9)
        self.assertIn('class="plone-layout"', html)
        self.assertIn("element-contentheader", html)
        self.assertIn('class="plone-site-title"', html)
        self.assertRegex(html, r'<img alt=""[^>]+plone-logo\.svg')
        self.assertIn("documentFirstHeading", html)
        self.assertIn('id="content-core"', html)
        self.assertIn("element-body", html)
        self.assertIn("A Page", html)
        # The forbidden-utility ban is checked file-based, on our own
        # templates only (test_template_lint.py). It cannot be asserted over
        # rendered output any more: the page now carries stock viewlet markup
        # through the manager bridges (pagelets/managers.py) — CMFPlone's
        # plone.footer wraps the footer portlets in a Bootstrap .row — and
        # that markup is not ours to lint.


class TestOrderParity(unittest.TestCase):
    """The flat variant used to guarantee a fixed, config-immune element order;
    with it gone, this parity test keeps ``viewlets.xml`` (the GS default the
    managed manager imports) honest against the canonical ``layout.ELEMENTS``.
    """

    def test_viewlets_xml_matches_elements(self):
        import plone.pageletlayout

        package_dir = plone.pageletlayout.__path__[0]
        viewlets_xml = f"{package_dir}/profiles/default/viewlets.xml"
        with open(viewlets_xml, encoding="utf-8") as fh:
            xml = fh.read()
        # Only the <order> block: the file also carries <hidden> sets for the
        # stock viewlets our elements replace (pagelets/managers.py), whose
        # names are stock viewlet names, not layout elements.
        order_block = re.search(r"<order\b.*?</order>", xml, re.DOTALL).group(0)
        order = tuple(re.findall(r'<viewlet\s+name="([^"]+)"', order_block))
        self.assertEqual(
            order,
            ELEMENTS,
            "profiles/default/viewlets.xml order must mirror layout.ELEMENTS",
        )
