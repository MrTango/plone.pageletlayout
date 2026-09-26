"""Render the layout elements in the stock viewlet managers."""
import logging

from zope.component import getUtility

from plone.app.viewletmanager.interfaces import IViewletSettingsStorage
from plone.pageletlayout.pagelets.slots import slot_assignments


logger = logging.getLogger(__name__)

#: The retired whole-body manager every element used to render in.
FLAT_MANAGER = "plone.pageletlayout.layout"
SKINNAME = "Plone Default"


def carry_hidden_elements():
    """Hide each element in its new slot if it was hidden in the flat manager."""
    storage = getUtility(IViewletSettingsStorage)
    assignments = slot_assignments()
    for name in storage.getHidden(FLAT_MANAGER, SKINNAME):
        slot = assignments.get(name)
        if slot is None:
            continue
        hidden = storage.getHidden(slot, SKINNAME)
        if name not in hidden:
            storage.setHidden(slot, SKINNAME, hidden + (name,))
            logger.info("%s stays hidden, now in %s", name, slot)


def upgrade(context):
    """Upgrade from profile version 1003 to 1004.

    The 1004 profile (imported before this handler) brings the slot
    assignments and the elements' places in the stock managers.
    """
    carry_hidden_elements()
