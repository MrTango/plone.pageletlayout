"""The content actions as pagelets (classic-coverage map, ticket 09).

The map's high-traffic cut of the admin-action surface: ``delete``,
``rename``, the workflow "Advanced…" screen and the history entry page.
Four stock view classes, reused whole through the ticket-06 FramedPage
mechanism — only their class-bound templates are swapped for body-only
twins, so every guard, redirect and write path is the stock one.

Two of them are plain ``z3c.form.form.Form`` subclasses registered
*directly* as ``browser:page`` — NOT wrapped in a ``FormWrapper`` — so
ticket 05's S1 seam (an ``ILayoutTemplate`` for ``IFormWrapper``) never saw
them; they are class-bound-template pages like any other framed page, and
their ``template`` attribute is the one to swap, as with ``@@sharing``.

**The modal path.** Delete, rename and "Advanced…" are all opened by
``pat-plone-modal`` (CMFPlone's actions.xml carries a ``modal`` property on
the first two, plone.app.contentmenu builds the third). Contrary to what
tickets 06-08 assumed, the modal does **not** request the ajax layout: it
fetches the link's plain ``href`` and extracts ``$("#content").html()`` out
of the *default*-layout document. The extraction point is supplied by the
framed body element for every framed page — see pagelets/framed.py, which
this ticket had to fix before converting anything (login, shipped in ticket
06, was opening an empty modal).
"""

import os.path

from plone.app.content.browser.actions import DeleteConfirmationForm
from plone.app.content.browser.actions import RenameForm
from plone.app.content.browser.content_status_history import ContentStatusHistoryView
from plone.app.layout.viewlets.content import HistoryByLineView
from plone.pageletlayout.page import FramedPage
from plone.pageletlayout.page import FramedTemplate


def _path(filename):
    return os.path.join(os.path.dirname(__file__), "templates", filename)


class DeleteConfirmationPagelet(DeleteConfirmationForm, FramedPage):
    """``delete_confirmation``: the stock form, framed.

    ``form.Form.__call__`` stays in charge — update(), then the button
    handler's redirect (Delete deletes and goes to the parent, Cancel goes
    back to the item) or ``render()``, which is where the framed template
    takes over.
    """

    template = FramedTemplate(_path("delete_confirmation.pt"))


class RenamePagelet(RenameForm, FramedPage):
    """``object_rename`` (and ``folder_rename``): the stock form, framed."""

    template = FramedTemplate(_path("object_rename.pt"))


class ContentStatusHistoryPagelet(ContentStatusHistoryView, FramedPage):
    """``content_status_history``: the workflow "Advanced…" screen.

    A plain BrowserView whose ``__call__`` takes the form values as named
    arguments (``workflow_action``, ``paths``, …) for ZPublisher to marshal
    — so it is inherited untouched: an override with a ``*args`` signature
    would silently stop the marshalling and leave every field None.
    """

    template = FramedTemplate(_path("content_status_history.pt"))

    def _set_http_headers(self):
        """Keep the classic page's no-store policy.

        The stock template set this from ``top_slot`` — a converted page
        has no slots, so the view owns it. Seat: the header hook the
        FramedTemplate calls before rendering, so it fires exactly where
        the classic one did (on a render, not on the Cancel redirect).
        """
        super()._set_http_headers()
        self.request.response.setHeader(
            "Cache-Control",
            "no-cache, no-store, must-revalidate, post-check=0, pre-check=0",
        )


class HistoryViewPagelet(HistoryByLineView, FramedPage):
    """``@@historyview``: the workflow/version history entry page.

    Bound as ``index`` here, not ``template`` — the stock class' own
    ``__call__`` is ``update()`` then ``self.index()``. The deeper
    CMFEditions screens it links to stay on the bridge (out of scope).
    """

    index = FramedTemplate(_path("history_view.pt"))
