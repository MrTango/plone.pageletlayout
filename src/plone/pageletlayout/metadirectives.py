"""Schemas for the five ``plone:`` directives (the directive grammar).

All five schemas live here — ``meta.zcml`` references no z3c schema. The
``pagelet`` ergonomics (optional class, inline ``template=``, and Tokens
``for``) re-derive ideas from gocept.pagelet (prior art), forked off
z3c.pagelet's and z3c.template's directive schemas.
"""

import z3c.template.zcml
from z3c.pagelet.interfaces import IPagelet
from zope.component.zcml import IBasicViewInformation
from zope.configuration.fields import GlobalInterface
from zope.configuration.fields import GlobalObject
from zope.configuration.fields import Path
from zope.configuration.fields import Tokens
from zope.interface import Interface
from zope.schema import TextLine
from zope.security.zcml import Permission


class IPageletDirective(IBasicViewInformation):
    """Register a published (layouted) pagelet.

    Forked from z3c.pagelet.zcml.IPageletDirective. Like that one, the
    directive also accepts arbitrary keyword arguments, set as attributes
    on the registered class.
    """

    name = TextLine(
        title="Name",
        description="The view name the pagelet is traversed under.",
        required=True,
    )

    class_ = GlobalObject(
        title="Class",
        description=(
            "Pagelet class; mixed with PageletPage on registration. "
            "Omit for a template-only pagelet (requires 'template')."
        ),
        required=False,
    )

    template = Path(
        title="Content template",
        description=(
            "Registered as the IContentTemplate adapter for the class "
            "(same machinery as plone:template) — one stanza registers "
            "pagelet and body template together. The layout template is "
            "never declared here; it is registered standalone with "
            "plone:layout."
        ),
        required=False,
    )

    permission = Permission(
        title="Permission",
        description=(
            "The permission needed to traverse the pagelet "
            "(enforced by AccessControl, like browser:page)."
        ),
        required=True,
    )

    for_ = Tokens(
        title="Context interfaces",
        description="One or more content interfaces or classes the pagelet is for.",
        required=False,
        value_type=GlobalObject(),
    )

    layer = GlobalInterface(
        title="Browser layer",
        required=False,
    )

    provides = GlobalInterface(
        title="Interface the pagelet provides",
        description="Must inherit z3c.pagelet.interfaces.IPagelet.",
        required=False,
        default=IPagelet,
    )


# Arbitrary keys and values may be passed and land as class attributes
# (z3c.pagelet's contract, kept).
IPageletDirective.setTaggedValue("keyword_arguments", True)


class ITemplateDirective(z3c.template.zcml.ITemplateDirective):
    """Register a content template (z3c:template cognate, Five factory)."""

    for_ = Tokens(
        title="Registered for",
        description=(
            "One or more classes or interfaces the template adapter is "
            "registered for — usually a view class."
        ),
        required=False,
        value_type=GlobalObject(),
    )


class ILayoutTemplateDirective(z3c.template.zcml.ILayoutTemplateDirective):
    """Register a layout template (z3c:layout cognate, Five factory)."""

    for_ = Tokens(
        title="Registered for",
        description=(
            "One or more classes or interfaces the template adapter is "
            "registered for — usually a view class."
        ),
        required=False,
        value_type=GlobalObject(),
    )


class IChromePageletDirective(Interface):
    """Register a chrome pagelet: named IContentProvider + content template,
    in one stroke."""

    name = TextLine(
        title="Provider name",
        description="The name the provider: expression looks up.",
        required=True,
    )

    class_ = GlobalObject(
        title="Class",
        description=(
            "Chrome pagelet class; mixed with ChromePagelet if it does not "
            "already subclass it. Omit for a template-only chrome element."
        ),
        required=False,
    )

    template = Path(
        title="Content template",
        description=(
            "Registered as the IContentTemplate adapter for the class "
            "(same machinery as plone:template). Omit to register the "
            "template separately."
        ),
        required=False,
    )

    for_ = Tokens(
        title="Context interfaces",
        description="One or more content interfaces or classes the chrome pagelet is for.",
        required=False,
        value_type=GlobalObject(),
    )

    layer = GlobalInterface(
        title="Browser layer",
        required=False,
    )

    view = GlobalInterface(
        title="View type the provider is available for",
        required=False,
    )


class IPageLayoutDirective(Interface):
    """Declare a named page layout: one layout-registry entry.

    The directive *binds* an existing hand-written layer interface, never
    mints one (docs/request-layouts.md, section 3).
    """

    name = TextLine(
        title="Layout name",
        description=(
            "Registry key, pagelet_layout param value, layout_name value, "
            "and body-class suffix. 'default' is reserved — the default "
            "layout is the absence of a layout layer."
        ),
        required=True,
    )

    layer = GlobalInterface(
        title="Layout layer",
        description=(
            "The request-marker interface the trigger chain applies; must "
            "extend IPlonePageletlayoutLayer."
        ),
        required=True,
    )

    view_marker = GlobalInterface(
        title="Static view marker",
        description=(
            "Marker (extending IPagelet) that triggers this layout as a "
            "published view's default. Omit for request-only layouts."
        ),
        required=False,
    )
