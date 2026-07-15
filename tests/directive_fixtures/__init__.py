"""Fixture pagelet classes for the directive-grammar tests.

One class per test that registers one: registrations made at test time
outlive the test (the layer's registry is only stacked per layer), so
sharing a class between tests would let one test's template registration
leak into another's lookup.
"""

from z3c.pagelet.interfaces import IPagelet


class IFullScreenPagelet(IPagelet):
    """Marker for full-screen published pagelets (the view= fixture)."""


class SuppressingChromePagelet:
    """view=-scoped chrome override that renders nothing."""

    def render(self):
        return ""


class GreetingPagelet:
    """One-stroke class+template fixture."""

    def update(self):
        self.greeting = "computed-greeting"


class GreetingTwoPagelet:
    """Template-inheritance fixture (registered twice, template once)."""

    def update(self):
        self.greeting = "computed-greeting-two"


class DisjointDocPagelet:
    """Same-name/disjoint-for fixture: the IDocument implementation."""

    def update(self):
        self.greeting = "disjoint-doc"


class DisjointFolderPagelet:
    """Same-name/disjoint-for fixture: the IFolder implementation."""

    def update(self):
        self.greeting = "disjoint-folder"


class MultiTemplateAlpha:
    """First of two classes served by ONE plone:template stanza."""

    def update(self):
        self.greeting = "multi-template-alpha"


class MultiTemplateBeta:
    """Second of two classes served by ONE plone:template stanza."""

    def update(self):
        self.greeting = "multi-template-beta"


class MultiLayoutAlpha:
    """First of two classes served by ONE plone:layout stanza."""

    def update(self):
        self.greeting = "multi-layout-alpha"


class MultiLayoutBeta:
    """Second of two classes served by ONE plone:layout stanza."""

    def update(self):
        self.greeting = "multi-layout-beta"
