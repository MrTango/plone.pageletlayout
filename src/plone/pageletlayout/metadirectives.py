"""Schema for the ``plone:chromepagelet`` directive (prototype, ticket 02)."""

from zope.configuration.fields import GlobalInterface
from zope.configuration.fields import GlobalObject
from zope.configuration.fields import Path
from zope.interface import Interface
from zope.schema import TextLine


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

    for_ = GlobalObject(
        title="Context interface",
        required=False,
    )

    layer = GlobalInterface(
        title="Browser layer",
        required=False,
    )

    view = GlobalInterface(
        title="View type the provider is available for",
        required=False,
    )
