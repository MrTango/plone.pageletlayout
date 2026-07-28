"""@@sharing as a pagelet (classic-coverage map, ticket 08).

plone.app.workflow's ``SharingView`` re-registered on the pageletlayout
layer through the FramedPage mechanism. The stock class keeps everything —
the role matrix, principal search, inheritance toggle, and the whole
``handle_form`` save path with its POST-only and ``_authenticator`` guards
— and only its class-bound ``template`` is swapped for a body-only twin.
It is a self-rendering view (``__call__`` renders the template on postback
and redirects on Cancel), which is exactly the shape FramedPage exists for.

**The macro the page publishes as a fragment.** ``updateSharingInfo`` is a
second registration on the same class: it renders the ``user-group-sharing``
macro *out of the page template* through plone.app.workflow's
``macro_wrapper`` and returns it as JSON. That is why ``FramedTemplate``
resolves to a BoundFramedTemplate whose ``macros`` are the body's (page.py)
— reaching for ``self.template.macros`` must find the matrix, not the frame.

The endpoint is **broken in stock Plone 6.2**: the macro reads ``icons``,
``portal_url`` and ``can_view_groups``, which the classic page inherited
from main_template's globals and the macro wrapper never supplied, so every
call raised ``NameError``. Nothing in the shipped JS calls it (verified
across plone.staticresources and CMFPlone's own bundles), which is why the
breakage went unnoticed. The converted template defines those names on the
macro element itself, so the fragment is self-contained and the endpoint
works — see tests/test_sharing.py::TestSharingUpdateSharingInfo.
"""

import os.path

from plone.app.workflow.browser.sharing import SharingView
from plone.pageletlayout.page import FramedPage
from plone.pageletlayout.page import FramedTemplate


def _path(filename):
    return os.path.join(os.path.dirname(__file__), "templates", filename)


class SharingPagelet(SharingView, FramedPage):
    """@@sharing: the stock SharingView, framed.

    ``SharingView.__call__`` stays in charge (handle_form, then either
    render or redirect to the item), so the framed render happens exactly
    where the stock page rendered — the FramedPage contract.
    """

    template = FramedTemplate(_path("sharing.pt"))


class SharingInfoFragment(SharingPagelet):
    """@@updateSharingInfo: the role matrix as JSON.

    A class of its own rather than the stock stanza's ``attribute=``:
    Five's ``browser:page`` implements ``attribute`` by mixing in a
    ``simple`` base whose ``browserDefault`` redirects publication to the
    named method — and that base loses the MRO race against the pagelet's
    own ``browserDefault``, so the page would publish its ``__call__`` (the
    whole framed page) instead. Making the fragment *be* ``__call__``
    sidesteps the collision entirely.
    """

    def __call__(self):
        """The role matrix as a JSON fragment (body + status messages)."""
        return self.updateSharingInfo()
