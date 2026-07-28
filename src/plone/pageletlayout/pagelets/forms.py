"""The S1 wrapped-form layout seam (classic-coverage map, ticket 05).

``plone.app.z3cform`` resolves every ``FormWrapper``'s outer shell through
its ``layout_factory`` — ``layout.pt`` → the deprecated main_template macro
path. The factories here register a more specific layout for the
pageletlayout layer: the pagelet frame rendered directly, the form's
``view/contents`` as the body element. ONE registration converts the whole
wrapped-form surface — Dexterity ``@@edit``, ``++add++``, registry record
forms, any ``layout.wrap_form(...)`` add-on form. ``ControlPanelFormWrapper``
sets ``index`` directly, bypassing the adapter lookup — the control-panel
surface intentionally stays on the bridge (out of scope).
"""

import os.path

from plone.z3cform.interfaces import IFormWrapper
from plone.z3cform.templates import ZopeTwoFormTemplateFactory

from plone.pageletlayout.chrome import ChromePagelet
from plone.pageletlayout.interfaces import IAjaxLayoutLayer
from plone.pageletlayout.interfaces import IPlonePageletlayoutLayer
from plone.pageletlayout.page import resolve_layout_name


def _path(filename):
    return os.path.join(os.path.dirname(__file__), "templates", filename)


class FormFrameTemplateFactory(ZopeTwoFormTemplateFactory):
    """Layout-template factory that stamps ``layout_name`` on the wrapper.

    The frame templates stamp the layout body class from
    ``view/layout_name`` (the PageletPage contract); a FormWrapper knows
    nothing of layouts, so the factory resolves the name at lookup time —
    the frame files stay identical in shape to layout.pt/ajax.pt instead
    of growing traversal helpers.
    """

    def __call__(self, form, request):
        form.layout_name = resolve_layout_name(request)
        return super().__call__(form, request)


#: The seam itself: (IFormWrapper, IPlonePageletlayoutLayer) → the pagelet
#: frame. Beats plone.app.z3cform's (IFormWrapper, IPloneFormLayer) because
#: our layer extends the form layer (see interfaces.py). Registered in
#: forms.zcml; the adapter dimensions ride on the factory's declarations.
form_layout_factory = FormFrameTemplateFactory(
    _path("form_layout.pt"),
    form=IFormWrapper,
    request=IPlonePageletlayoutLayer,
)

#: ajax_load / ?pagelet_layout=ajax on a wrapped form: the same fragment
#: contract as pagelet pages — the same file, even (the canonical ajax
#: frame is view-agnostic; AjaxRegion sets both ajax response headers in
#: its update()). The ajax layer extends the pageletlayout layer, so this
#: registration beats the full-frame one on ajax requests.
form_ajax_layout_factory = FormFrameTemplateFactory(
    _path("ajax.pt"),
    form=IFormWrapper,
    request=IAjaxLayoutLayer,
)


class FormBodyChromePagelet(ChromePagelet):
    """The body element for wrapped forms: ``#content-core`` around the
    rendered form. Shadows the stock body element (which renders the
    published *pagelet*'s content template — recursion for a FormWrapper)
    on the ``view=IFormWrapper`` dimension. ``view.contents`` is computed
    by ``FormWrapper.update()`` before the frame renders."""

    def render(self):
        return (
            '<div id="content-core" class="element-body">'
            f"{self.view.contents}</div>"
        )
