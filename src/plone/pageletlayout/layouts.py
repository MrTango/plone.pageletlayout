"""The trigger chain: request-time layout selection.

One post-traversal subscriber applies **at most one** layout layer per
request via ``alsoProvides`` — everything a layout changes is then ordinary
adapter specificity on that layer. ``IPubAfterTraversal`` is effectively
forced: the static-marker trigger reads ``request['PUBLISHED']``, which
exists only after traversal. Consequence, by design: a layout can never
influence which view is published — it re-dresses the page, it never swaps
the view. Normative model: docs/request-layouts.md, section 4.

The module name matters: ``__name__`` is the dedicated logger
``plone.pageletlayout.layouts`` — the unknown-name warning fires on
attacker-controlled input, so an operator being spammed can silence exactly
this logger.
"""

import logging

from plone.base.utils import is_truthy
from zope.component import adapter
from zope.component import getUtilitiesFor
from zope.component import queryUtility
from zope.interface import alsoProvides
from ZPublisher.interfaces import IPubAfterTraversal

from plone.pageletlayout.interfaces import IPageLayout


logger = logging.getLogger(__name__)

#: The layout name the stock ``ajax_load`` param aliases. The alias resolves
#: through the registry like any other trigger — inert until an ``ajax``
#: layout is registered, live the moment one is.
AJAX_LAYOUT_NAME = "ajax"


@adapter(IPubAfterTraversal)
def apply_layout(event):
    """Apply the first-firing trigger's layout layer; trigger order *is* the
    layout precedence (param > alias > static view marker > default)."""
    request = event.request
    form = getattr(request, "form", None)
    if form is None:  # not a browser request (e.g. test doubles)
        return

    # 1. The pagelet_layout param.
    name = form.get("pagelet_layout")
    if name:
        if name == "default":
            # The escape hatch: the default layout is the absence of a
            # layer, so a statically-marked view renders default too.
            return
        entry = (
            queryUtility(IPageLayout, name=name) if isinstance(name, str) else None
        )
        if entry is not None:
            alsoProvides(request, entry.layer)
            return
        # Unknown name: warn, then fall through as if the param were
        # absent — no 404, unknown values collapse onto the variant the
        # remaining triggers select.
        logger.warning(
            "Unknown pagelet_layout name %r requested at %s — ignoring it.",
            name,
            request.get("ACTUAL_URL", request.get("PATH_INFO", "?")),
        )

    # 2. The ajax_load alias (stock compatibility). A pure rewrite to the
    #    ajax layout; explicit falsy applies nothing and forces nothing.
    ajax_load = form.get("ajax_load")
    if ajax_load is not None and is_truthy(ajax_load):
        entry = queryUtility(IPageLayout, name=AJAX_LAYOUT_NAME)
        if entry is not None:
            alsoProvides(request, entry.layer)
            return

    # 3. A registry entry's static view marker on the published view.
    published = request.get("PUBLISHED")
    if published is not None:
        for _name, entry in sorted(getUtilitiesFor(IPageLayout)):
            marker = entry.view_marker
            if marker is not None and marker.providedBy(published):
                alsoProvides(request, entry.layer)
                return

    # 4. Nothing fired: no layer, the default layout renders.
