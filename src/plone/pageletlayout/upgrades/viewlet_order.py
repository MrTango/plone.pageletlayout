"""Re-import this package's viewlet order without evicting anybody else's.

``profiles/default/viewlets.xml`` states the layout manager's order in full —
it is the canonical sequence (``layout.ELEMENTS``), and a fresh install has to
get all of it. But GenericSetup's ``<order>`` importer, given entries with no
``insert-before``/``insert-after``, *removes each name and appends it*
(``plone.app.viewletmanager.exportimport.storage._computeValues``). So on a
site where an add-on has anchored an element of its own into the sequence —
``plonetheme.clara.subnav`` after the body,
``collective.blicca.footerblocks.footerblocks`` before the footer rows — a
plain re-import pushes all twenty-one of our names past it, and the add-on's
element ends up *first on the page*. ``OrderedViewletManager.sort`` renders
names it does not find in the stored order after the ones it does, but the
storage does hold these names, at position zero: the footer landed above the
logo.

Anchoring our own entries would not fix it either. Each anchor is evaluated
against the order as it stands mid-import, so a foreign element sitting on an
anchor is stepped over rather than carried along, and it drifts a little
further with every re-import.

What the foreign entries actually mean is "keep me next to *this* neighbour",
so that is what this preserves: snapshot the order, let the import restate our
sequence, then put every name that is not ours back behind the neighbour it
had. Their own profiles' ``insert-after``/``insert-before`` anchors say the
same thing and stay authoritative — re-running an add-on's ``viewlets`` step
still moves its element wherever that file wants it.
"""

from contextlib import contextmanager
from zope.component import getUtility

from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.pagelets.layout import ELEMENTS
from plone.pageletlayout.pagelets.layout import MANAGER_NAME


#: The skin the profile writes the order for (viewlets.xml, ``skinname=``).
SKINNAME = "Plone Default"


def _neighbours(order):
    """The foreign names in ``order``, each with the name it follows.

    Returns ``[(name, predecessor_or_None)]`` in stored order. The predecessor
    is whatever came directly before — foreign names included, so a run of them
    keeps its internal sequence when they are re-inserted in this same order.
    """
    neighbours = []
    previous = None
    for name in order:
        if name not in ELEMENTS:
            neighbours.append((name, previous))
        previous = name
    return neighbours


def _reinsert(order, neighbours):
    """Put each foreign name back behind its predecessor.

    Lifted out first: the import never touched these names — it removed and
    re-appended *ours*, which is precisely how they ended up in front — so
    they have to be moved, not merely restored if missing.
    """
    moving = {name for name, _ in neighbours}
    order = [name for name in order if name not in moving]
    for name, previous in neighbours:
        if previous is None or previous not in order:
            order.insert(0, name)
        else:
            order.insert(order.index(previous) + 1, name)
    return order


@contextmanager
def preserving_foreign_order(skinname=SKINNAME):
    """Run a ``viewlets`` re-import with foreign elements kept in place."""
    storage = getUtility(IViewletSettingsStorage)
    neighbours = _neighbours(storage.getOrder(MANAGER_NAME, skinname))
    yield
    order = storage.getOrder(MANAGER_NAME, skinname)
    restored = _reinsert(order, neighbours)
    if tuple(restored) != tuple(order):
        storage.setOrder(MANAGER_NAME, skinname, tuple(restored))
