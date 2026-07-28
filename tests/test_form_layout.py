"""Functional tests for the S1 wrapped-form layout seam (map ticket 05).

``plone.app.z3cform`` resolves every ``FormWrapper``'s outer shell through
its ``layout_factory`` — ``layout.pt`` → ``main_template`` — so all wrapped
z3c.forms (Dexterity ``@@edit``, ``++add++``, ``wrap_form`` add-on forms)
render via the bridge's deprecated macro path. The seam registers a more
specific layout template for ``(IFormWrapper, IPlonePageletlayoutLayer)``
that renders the pagelet frame directly: no macro path, no bridge, no
deprecation signal.
"""

import unittest

import transaction

from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.pageletlayout.testing import FUNCTIONAL_TESTING

BRIDGE_LOGGER = "plone.pageletlayout.bridge"


class FormLayoutTestCase(unittest.TestCase):
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
        )
        transaction.commit()

    def _set_debug(self, value):
        from App.config import getConfiguration

        config = getConfiguration()
        old = getattr(config, "debug_mode", False)
        config.debug_mode = value
        self.addCleanup(setattr, config, "debug_mode", old)

    def _render(self, context, view_name):
        return context.restrictedTraverse(view_name)()

    def assert_pagelet_frame(self, html, page):
        self.assertIn('class="plone-layout"', html, f"{page}: no pagelet frame")
        self.assertNotIn(
            "visual-portal-wrapper", html, f"{page}: classic master markup"
        )
        self.assertNotIn(
            "portal-column-content", html, f"{page}: classic master markup"
        )


class TestEditFormRendersWithoutMacroPath(FormLayoutTestCase):
    """@@edit renders the pagelet frame directly — the macro path stays
    silent even in development mode, where every bridged render warns."""

    def test_edit_renders_pagelet_frame_without_deprecation_signal(self):
        self._set_debug(True)
        with self.assertNoLogs(BRIDGE_LOGGER, level="INFO"):
            html = self._render(self.doc, "@@edit")
        self.assert_pagelet_frame(html, "@@edit")
        # the wrapped form itself landed in the frame
        self.assertIn("form.widgets.IDublinCore.title", html)

    def test_add_renders_pagelet_frame_without_deprecation_signal(self):
        self._set_debug(True)
        with self.assertNoLogs(BRIDGE_LOGGER, level="INFO"):
            html = self._render(self.portal, "++add++Document")
        self.assert_pagelet_frame(html, "++add++Document")
        self.assertIn("form.widgets.IDublinCore.title", html)

    def test_form_lands_in_body_element(self):
        # the form renders inside the frame's body element, between the
        # header chrome and the footer — not appended outside the layout
        html = self._render(self.doc, "@@edit")
        body_element = html.index('id="content-core"')
        form = html.index("form.widgets.IDublinCore.title")
        footer = html.index("element-copyright")
        self.assertTrue(
            body_element < form < footer,
            "edit form did not land inside the body element",
        )

    def test_content_header_is_the_form_label(self):
        # classic layout.pt added <h1>view/label</h1> around the form; the
        # frame's content-header element must carry it (not the context
        # title alone: an add form has no context title at all)
        html = self._render(self.doc, "@@edit")
        header = html.split('class="element-contentheader"', 1)[1].split(
            "</header>", 1
        )[0]
        self.assertIn("Edit", header, "content header does not show the form label")


class TestFormResources(FormLayoutTestCase):
    """The pattern/widget plumbing survives the frame swap."""

    def test_patterns_settings_on_body(self):
        # mockup patterns read their settings off the <body> data attributes
        html = self._render(self.doc, "@@edit")
        body_tag = html.split("<body", 1)[1].split(">", 1)[0]
        self.assertIn("data-pat-plone-modal", body_tag)
        self.assertIn("data-base-url", body_tag)

    def test_tinymce_initializes_on_edit(self):
        # the richtext widget boots TinyMCE through the mimetype-selector
        # pattern, whose config names the tinymce pattern for text/html
        html = self._render(self.doc, "@@edit")
        self.assertIn("pat-textareamimetypeselector", html)
        self.assertIn("&quot;pattern&quot;: &quot;tinymce&quot;", html)

    def test_head_has_resource_registry(self):
        # the styles/scripts providers render the resource registry in the
        # frame head, so widget JS/CSS loads
        html = self._render(self.doc, "@@edit")
        head = html.split("</head>", 1)[0]
        self.assertIn("<script", head)
        self.assertIn("stylesheet", head)


class TestAjaxFormRequests(FormLayoutTestCase):
    """ajax_load / ?pagelet_layout=ajax on a wrapped form keeps the
    fragment contract the bridge preserved: the charset-only ajax frame,
    not the full chrome around an ajax region."""

    def test_ajax_layer_swaps_the_whole_frame(self):
        from zope.interface import alsoProvides

        from plone.pageletlayout.interfaces import IAjaxLayoutLayer

        alsoProvides(self.request, IAjaxLayoutLayer)
        html = self._render(self.doc, "@@edit")
        # the fragment frame: no chrome wrapper, charset-only head
        self.assertNotIn('class="plone-layout"', html)
        head = html.split("</head>", 1)[0]
        self.assertNotIn("stylesheet", head)
        # the fragment element set, form as the body
        self.assertIn('<article id="content">', html)
        self.assertIn("form.widgets.IDublinCore.title", html)


class TestWrapFormAddonSurface(FormLayoutTestCase):
    """An add-on form built with layout.wrap_form gets the frame too."""

    def test_wrap_form_renders_pagelet_frame(self):
        from plone.z3cform import layout
        from z3c.form import button
        from z3c.form import field
        from z3c.form import form
        from zope import schema
        from zope.interface import Interface

        class IAddonSchema(Interface):
            note = schema.TextLine(title="Note")

        class AddonForm(form.Form):
            fields = field.Fields(IAddonSchema)
            ignoreContext = True
            label = "An Add-on Form"

            @button.buttonAndHandler("Save")
            def handle_save(self, action):
                pass

        wrapper_class = layout.wrap_form(AddonForm)
        wrapper = wrapper_class(self.portal, self.request)
        wrapper.__name__ = "addon-form"
        self._set_debug(True)
        with self.assertNoLogs(BRIDGE_LOGGER, level="INFO"):
            html = wrapper()
        self.assert_pagelet_frame(html, "wrap_form")
        self.assertIn("form.widgets.note", html)
        self.assertIn("An Add-on Form", html)
