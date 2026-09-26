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

    ``#content``, the modal extraction point (``pat-plone-modal`` extracts
    ``$("#content").html()`` from the plain default-layout response), is the
    frame's ``article`` around this element — its content header is shadowed
    empty, so the article holds just this body.
    """

    def render(self):
        return (
            '<div id="content-core" class="element-body">'
            f"{self.view.render_body()}</div>"
        )


class EmptyContentHeaderChromePagelet(ChromePagelet):
    """No contentheader for framed pages: the stock element renders the
    *context*'s title — the portal (or a tool) for this family of pages —
    and a framed page's real heading lives in its body template
    (docs/porting-main-template.md, the content-title slot row)."""

    def render(self):
        return ""
