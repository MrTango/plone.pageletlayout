"""Sitemap + contact-info as pagelets (classic-coverage map, ticket 10).

The map's last two high-traffic site pages. Both are CMFPlone
``browser:page`` registrations with a class-bound template, so both convert
through the ticket-06 FramedPage mechanism:

* ``sitemap`` — a plain BrowserView whose ``index`` is the swapped template;
  its navtree HTML is built in *Python* (``_renderLevel``), which is where
  the classic hooks had to be replaced.
* ``contact-info`` — ``ContactForm``, an ``AutoExtensibleForm`` registered
  **directly** (not through ``plone.z3cform.layout.wrap_form``), so ticket
  05's S1 wrapped-form seam never saw it: it is a class-bound-template page
  like ``delete_confirmation``, and its ``template`` is the one to swap.

``contact-info`` is also a **modal action** (CMFPlone actions.xml carries a
``modal`` property on the ``contact`` site action), so the modal extraction
contract of ticket 09 applies to it — ``TestContactModalContract``.
"""

import unittest

import transaction
from Acquisition import aq_base
from zope.component import getUtility

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.base.interfaces.controlpanel import IMailSchema
from plone.pageletlayout.testing import FUNCTIONAL_TESTING
from plone.registry.interfaces import IRegistry
from plone.testing.zope import Browser

from .test_live_surface import classic_markup_in
from .test_live_surface import missing_frame_in


FORM_URLENCODED = "application/x-www-form-urlencoded"


class SitemapContactTestCase(unittest.TestCase):
    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        # plone.app.testing ships a chainless site; the sitemap's item hook
        # carries the workflow state, so the fixture needs a chain for
        # ``state-private`` to be more than ``state-missing-value``.
        self.portal.portal_workflow.setDefaultChain("simple_publication_workflow")
        self.folder = api.content.create(
            container=self.portal, type="Folder", id="tree-folder", title="Tree Folder"
        )
        self.doc = api.content.create(
            container=self.folder, type="Document", id="tree-doc", title="Tree Doc"
        )
        transaction.commit()
        self.portal_url = self.portal.absolute_url()

    def browser(self, anonymous=False):
        browser = Browser(self.layer["app"])
        browser.handleErrors = False
        if not anonymous:
            browser.addHeader("Authorization", f"Basic {SITE_OWNER_NAME}:{SITE_OWNER_PASSWORD}")
        return browser

    def open(self, path, browser=None):
        browser = browser or self.browser()
        browser.open(path)
        return browser.contents

    def assert_framed(self, html, url=""):
        self.assertEqual(classic_markup_in(html), (), f"{url} renders classic master markup")
        self.assertEqual(missing_frame_in(html), (), f"{url} did not render the pagelet frame")

    def set_debug_mode(self, value):
        from App.config import getConfiguration

        config = getConfiguration()
        old = getattr(config, "debug_mode", False)
        config.debug_mode = value
        self.addCleanup(setattr, config, "debug_mode", old)

    def assert_off_the_macro_path(self, path):
        """Frame markers alone can't tell a conversion from the bridge
        (which frames macro consumers too); the discriminator is the
        deprecation signal, which a real pagelet never emits."""
        self.set_debug_mode(True)
        browser = self.browser()
        with self.assertNoLogs("plone.pageletlayout.bridge", level="INFO"):
            self.open(path, browser=browser)
        self.assert_framed(browser.contents, path)


class TestSitemap(SitemapContactTestCase):
    """``sitemap``: the stock SitemapView, framed."""

    @property
    def url(self):
        return f"{self.portal_url}/sitemap"

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open(self.url), self.url)

    def test_renders_off_the_macro_path(self):
        self.assert_off_the_macro_path(self.url)

    def test_shows_the_site_map_heading_and_description(self):
        html = self.open(self.url)
        self.assertIn("Site map", html)
        self.assertIn("An overview of the available content on this site", html)

    def test_lists_the_content_tree(self):
        html = self.open(self.url)
        self.assertIn("Tree Folder", html)
        self.assertIn("Tree Doc", html)
        self.assertIn(self.doc.absolute_url(), html)

    def test_nesting_survives_the_hook_swap(self):
        # The child list is rendered *inside* its parent's <li> — the whole
        # point of a sitemap. _renderLevel builds this in Python.
        html = self.open(self.url)
        tree = html.split('id="portal-sitemap"', 1)[1]
        parent = tree.index("Tree Folder")
        child = tree.index("Tree Doc")
        self.assertLess(parent, child)
        self.assertIn("<ul", tree[parent:child], "the child list is not nested")

    def test_navtree_hooks_are_replaced_by_pagelet_hooks(self):
        # navTree / navTreeItem / navTreeLevelN / visualNoMarker are classic
        # Barceloneta hooks with no rule left anywhere (_clara-classic.scss
        # is gone, ticket 03). The converted page emits its own instead.
        html = self.open(self.url)
        for dead in ("navTree", "visualNoMarker", "navTreeItem"):
            self.assertNotIn(dead, html, f"{dead} survived the conversion")
        self.assertIn("plone-sitemap", html)

    def test_item_keeps_its_state_and_type_classes(self):
        # state-* is a real hook (Clara's toolbar/megamenu colour by it) and
        # contenttype-* is the icon hook — both survive the swap.
        html = self.open(self.url)
        self.assertIn("state-private", html)
        self.assertIn("contenttype-document", html)

    def test_current_item_is_marked(self):
        # Classically `navTreeCurrentItem`, a dead class; the package's own
        # current-item hook is aria-current="page" (breadcrumbs.pt, and what
        # Clara styles for the global nav).
        tree = self.open(f"{self.doc.absolute_url()}/sitemap")
        tree = tree.split('id="portal-sitemap"', 1)[1]
        current = tree.split('aria-current="page"', 1)
        self.assertEqual(len(current), 2, "no current item is marked")
        self.assertIn("Tree Doc", current[1].split("</a>", 1)[0])

    def test_body_does_not_duplicate_the_frame_content_core(self):
        # The framed body element emits #content-core (framed.py); the stock
        # template wrapped the list in a second one.
        html = self.open(self.url)
        self.assertIn('<div id="content-core" class="element-body">', html)
        self.assertEqual(html.count('id="content-core"'), 1)

    def test_ajax_layout_renders_the_fragment(self):
        html = self.open(f"{self.url}?ajax_load=1")
        self.assertIn("pagelet-layout-ajax", html)
        self.assertIn("Tree Folder", html)


class TestContactInfo(SitemapContactTestCase):
    """``contact-info``: the stock ContactForm, framed."""

    @property
    def url(self):
        return f"{self.portal_url}/contact-info"

    def configure_mailhost(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IMailSchema, prefix="plone")
        settings.email_from_address = "site@example.com"
        settings.email_from_name = "Site Owner"
        transaction.commit()

    def test_renders_in_pagelet_frame(self):
        self.assert_framed(self.open(self.url), self.url)

    def test_renders_off_the_macro_path(self):
        self.assert_off_the_macro_path(self.url)

    def test_is_not_a_wrapped_form(self):
        # The S1 seam (ticket 05) adapts IFormWrapper; ContactForm is
        # registered directly, so it never reached that seam — which is why
        # this page needed converting at all.
        from plone.z3cform.interfaces import IFormWrapper

        view = self.portal.restrictedTraverse("contact-info")
        self.assertFalse(IFormWrapper.providedBy(view))

    def test_warns_when_no_mailhost_is_configured(self):
        html = self.open(self.url)
        self.assertIn("This site doesn't have a valid email setup", html)
        self.assertNotIn("form.widgets.subject", html)

    def test_renders_the_form_when_the_mailhost_is_configured(self):
        self.configure_mailhost()
        html = self.open(self.url)
        self.assertIn("Fill in this form to contact the site owners", html)
        self.assertIn("form.widgets.subject", html)
        self.assertIn("form.widgets.message", html)
        self.assertIn("form.buttons.send", html)

    def test_form_carries_the_csrf_token(self):
        self.configure_mailhost()
        self.assertIn('name="_authenticator"', self.open(self.url))

    def test_shows_the_contact_form_heading(self):
        self.assertIn("Contact form", self.open(self.url))

    def test_body_does_not_duplicate_the_frame_content_core(self):
        self.configure_mailhost()
        html = self.open(self.url)
        self.assertIn('<div id="content-core" class="element-body">', html)
        self.assertEqual(html.count('id="content-core"'), 1)

    def test_submitting_sends_the_message_and_thanks_the_visitor(self):
        self.configure_mailhost()
        # Patch the MailHost *class*: the publisher serves the POST from its
        # own ZODB connection, so an attribute set on this thread's instance
        # would not be the object that sends (and a real send would try to
        # open a socket).
        sent = []
        mailhost_class = type(aq_base(self.portal.MailHost))
        original = mailhost_class.send

        def record(self_, *args, **kwargs):
            sent.append((args, kwargs))

        mailhost_class.send = record
        self.addCleanup(setattr, mailhost_class, "send", original)

        browser = self.browser()
        html = self.open(self.url, browser=browser)
        token = html.split('name="_authenticator"', 1)[1]
        token = token.split('value="', 1)[1].split('"', 1)[0]
        browser.post(
            self.url,
            "&".join([
                "form.widgets.subject=Probe+subject",
                "form.widgets.sender_fullname=Probe+Sender",
                "form.widgets.sender_from_address=probe%40example.com",
                "form.widgets.message=Probe+message",
                "form.buttons.send=Send",
                f"_authenticator={token}",
            ]),
            FORM_URLENCODED,
        )
        self.assertTrue(sent, "no mail was handed to the MailHost")
        self.assertIn("Thank you for your feedback", browser.contents)
        self.assert_framed(browser.contents, "contact-info (sent)")

    def test_validation_errors_render_framed(self):
        self.configure_mailhost()
        browser = self.browser()
        html = self.open(self.url, browser=browser)
        token = html.split('name="_authenticator"', 1)[1]
        token = token.split('value="', 1)[1].split('"', 1)[0]
        browser.post(
            self.url,
            "&".join(["form.buttons.send=Send", f"_authenticator={token}"]),
            FORM_URLENCODED,
        )
        self.assertIn("Required input is missing", browser.contents)
        self.assert_framed(browser.contents, "contact-info (errors)")


class TestContactModalContract(SitemapContactTestCase):
    """What ``pat-plone-modal`` needs from ``contact-info``.

    The ``contact`` site action carries a ``modal`` property, and the modal
    parses the *default*-layout response — ``$("#content").html()`` as the
    body, ``h1:first`` as the title (removed from the body),
    ``.formControls`` for the button bar (ticket 09,
    docs/porting-main-template.md "Modal consumers").
    """

    @property
    def url(self):
        return f"{self.portal_url}/contact-info"

    def setUp(self):
        super().setUp()
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IMailSchema, prefix="plone")
        settings.email_from_address = "site@example.com"
        settings.email_from_name = "Site Owner"
        transaction.commit()

    def extracted(self, html):
        """What ``$("#content").html()`` would hand the modal."""
        self.assertIn('<article id="content">', html, "no #content: the modal body is empty")
        return html.split('<article id="content">', 1)[1].split("</article>", 1)[0]

    def test_content_is_the_modal_extraction_point(self):
        self.assertIn("form.widgets.message", self.extracted(self.open(self.url)))

    def test_page_heading_is_the_first_h1(self):
        html = self.open(self.url)
        self.assertIn("<h1", html)
        self.assertLess(
            html.index('<article id="content">'),
            html.index("<h1"),
            "an h1 renders above #content — it would hijack the modal title",
        )

    def test_submit_button_is_in_form_controls(self):
        self.assertIn("formControls", self.extracted(self.open(self.url)))

    def test_ajax_layout_does_not_duplicate_the_content_id(self):
        html = self.open(f"{self.url}?ajax_load=1")
        self.assertEqual(html.count('id="content"'), 1)
        self.assertIn("form.widgets.message", html)
        self.assertIn("pagelet-layout-ajax", html)
