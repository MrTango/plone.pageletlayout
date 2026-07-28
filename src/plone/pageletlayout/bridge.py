"""The main_template compatibility bridge.

A permanent, undocumented shim: the ``main_template`` view is overridden on
the pageletlayout layer with a pagelet-frame template exposing a compatible
``master`` macro (and the nested ``content`` macro the control-panel
``prefs_main_template`` chain binds), so every unconverted classic consumer
— add-ons included — renders pagelet chrome without being touched. Macros
keep *working* here but are never documented or recommended; everything new
is built on ``plone:pagelet``, and every macro-path render logs a
deprecation signal (``warn_macro_use``) pointing at
docs/porting-main-template.md.

Subclassing CMFPlone's MainTemplate keeps the whole classic contract for
free: ``__call__``, the ``macros`` property consumers bind via
``context/@@main_template/macros/master``, and the ajax_load switch to the
stock ajax_main_template. Only the full-frame template is ours.
"""

import logging

from App.config import getConfiguration
from Products.CMFPlone.browser.main_template import MainTemplate
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.pageletlayout.page import resolve_layout_name

logger = logging.getLogger(__name__)

#: Consumers already logged in this process — the production rate limit
#: (once per consumer per process; development mode logs every render).
_warned_consumers = set()

PORTING_DOCS = "docs/porting-main-template.md in plone.pageletlayout"


class BridgedMainTemplate(MainTemplate):
    """MainTemplate with the pagelet frame as its full template."""

    main_template = ViewPageTemplateFile("templates/main_template.pt")

    @property
    def layout_name(self):
        """The applied layout's name, for the frame's body-class stamp —
        consumer views are plain BrowserViews without ``layout_name``, so
        the bridge template reaches it via ``context/@@main_template``."""
        return resolve_layout_name(self.request)

    def warn_macro_use(self, template=None):
        """The deprecation signal, called by the frame's master macro.

        ``template`` is the TAL ``template`` variable at macro-render
        time — the root template being rendered, i.e. the consumer that
        bound the macro (the same object classic main_template passes to
        ``plone_layout.bodyClass``), not the frame.
        """
        name = getattr(template, "filename", None) or repr(template)
        message = (
            f"{name} renders through the deprecated main_template macro "
            f"path, kept working by the plone.pageletlayout compatibility "
            f"bridge. Build new pages with plone:pagelet and port this "
            f"one — see {PORTING_DOCS}."
        )
        if getConfiguration().debug_mode:
            logger.warning(message)
        elif name not in _warned_consumers:
            _warned_consumers.add(name)
            logger.info(message)
