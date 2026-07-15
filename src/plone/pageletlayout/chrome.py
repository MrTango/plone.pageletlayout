"""Chrome pagelet base class (prototype — wayfinder ticket 02).

A "chrome pagelet" is one visible chrome element (logo, nav, footer, …)
addressed as a *named content provider*: a layout template renders it with
``provider:<name>``. It keeps the pagelet templating story — computation in
``update()``, markup from the ``IContentTemplate`` adapter — but is looked
up like a viewlet manager, not traversed like a page.
"""

from z3c.pagelet.browser import BrowserPagelet
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import implementer


@implementer(IContentProvider)
class ChromePagelet(BrowserPagelet):
    """Two facets, one object.

    Pagelet facet: ``update()`` computes, the inherited
    ``BrowserPagelet.render()`` looks up ``IContentTemplate`` on
    (self, request) and renders it — and nothing else.

    Provider facet: registered as a named multi-adapter on
    (context, request, view); the ``provider:`` expression instantiates it
    and calls ``update()`` then ``render()`` — never ``__call__``. Layout
    lookup lives only in ``__call__``, so a chrome pagelet rendered as a
    provider can never recurse into layout-in-layout.

    Publishability is a property of the *registration*, not the class:
    the chrome registration alone is not traversable. Add a
    ``plone:pagelet`` registration for the same class when a standalone
    (layouted) page is wanted — e.g. for AJAX refresh of one element.
    """

    def __init__(self, context, request, view=None):
        super().__init__(context, request)
        self.view = view
        # IContentProvider contract: a provider knows the view it sits in.
        # Only set when present: BrowserView.__parent__ is a property that
        # falls back to self.context, and AccessControl evaluates the View
        # permission by walking __parent__ — setting it to None on the
        # published path would cut the chain and lock out everyone.
        if view is not None:
            self.__parent__ = view
