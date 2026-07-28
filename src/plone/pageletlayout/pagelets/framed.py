"""The framed-page chrome shadows (see ``IFramedPage``, ``page.FramedPage``).

Converting a classic self-rendering page keeps the stock control flow and
binds body-only templates on the class (``FramedTemplate``); these two
elements shadow the stock chrome on the ``view=IFramedPage`` dimension —
the ticket-05 pattern (``view=IFormWrapper``), one registration pair for
every framed page, present and future.
"""

from plone.pageletlayout.chrome import ChromePagelet


class FramedBodyChromePagelet(ChromePagelet):
    """The body element for framed pages: ``#content-core`` around the
    bound body template. Shadows the stock body element (which renders the
    published pagelet's registered content template — a framed page has
    none, its bodies live on the class).

    **The element carries ``#content`` too** — the modal extraction point
    (ticket 09). ``pat-plone-modal`` fetches the link's plain ``href``,
    never appending ``ajax_load`` (of the shipped patterns only search and
    manageportlets do), and extracts ``$("#content").html()``; so the
    *default*-layout response is what a modal parses, not the ajax
    fragment. Five stock actions open in a modal — login, delete, rename,
    contact, join — and every one of them is or becomes a framed page.

    A framed page can carry the id without the content-group element
    request-layouts.md rejected for the managed layout: its content header
    is shadowed empty, so this element *is* the whole content region and
    the wrapper groups nothing. ``.element-body`` stays on the inner div,
    where Clara's direct-child typography rules need it, and the nesting
    matches stock main_template, AjaxRegion and the bridge frame exactly.
    """

    def render(self):
        core = (
            '<div id="content-core" class="element-body">'
            f"{self.view.render_body()}</div>"
        )
        if self.view.layout_name == "ajax":
            # AjaxRegion already wraps the fixed element set in #content
            # (layout.py); a second one here would duplicate the id.
            return core
        return f'<article id="content">{core}</article>'


class EmptyContentHeaderChromePagelet(ChromePagelet):
    """No contentheader for framed pages: the stock element renders the
    *context*'s title — the portal (or a tool) for this family of pages —
    and a framed page's real heading lives in its body template
    (docs/porting-main-template.md, the content-title slot row)."""

    def render(self):
        return ""
