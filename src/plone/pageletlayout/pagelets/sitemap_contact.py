"""Sitemap + contact-info as pagelets (classic-coverage map, ticket 10).

The map's last two high-traffic site pages, both CMFPlone ``browser:page``
registrations with a class-bound template — so both are ticket-06 FramedPage
conversions, stock view classes reused whole.

**contact-info is not a wrapped form.** The ticket asked whether ticket 05's
S1 seam already covered it: it does not. ``ContactForm`` is a bare
``AutoExtensibleForm``/``form.Form`` registered *directly* as a
``browser:page`` (Products/CMFPlone/browser/configure.zcml) — never passed
through ``plone.z3cform.layout.wrap_form`` — so no ``FormWrapper``, no
``ILayoutTemplate`` lookup, no S1. It is the ``delete_confirmation`` shape
from ticket 09: swap the class-bound ``template`` and the page is framed.
That also settles the map's open fog patch — the S1 seam is *not* on the
modal path here, because contact-info never took it.

**The sitemap's markup is built in Python.** ``SitemapView._renderLevel``
emits the ``<li>``/``<ul>`` scaffolding as a string and delegates the link
to ``item_template``; the classic hooks it wrote (``navTree``,
``navTreeLevelN``, ``navTreeItem``, ``visualNoMarker``,
``navTreeCurrentItem``) are Barceloneta's, and nothing has styled them since
``_clara-classic.scss`` was retired (ticket 03). Both are overridden below,
so the tree carries this package's own hooks instead.
"""

import os.path

from Products.CMFPlone.browser.contact_info import ContactForm
from Products.CMFPlone.browser.sitemap import SitemapView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.pageletlayout.page import FramedPage
from plone.pageletlayout.page import FramedTemplate


def _path(filename):
    return os.path.join(os.path.dirname(__file__), "templates", filename)


class SitemapPagelet(SitemapView, FramedPage):
    """``sitemap``: the stock SitemapView, framed.

    A template-only view — no ``__call__`` of its own — so FramedPage's
    inherited one (render the bound ``index``) is exactly what Five's page
    class did. ``createSiteMap`` and its catalog walk are untouched; only
    the two markup producers below are ours.
    """

    index = FramedTemplate(_path("sitemap.pt"))

    #: One tree link, rendered once per node. Deliberately comment-free: an
    #: HTML comment in here is emitted for every item on the page. The two
    #: classes that survive the hook swap are the ones with rules behind
    #: them — ``state-*`` (Clara colours by workflow state) and
    #: ``contenttype-*`` (the icon hook); ``navTreeCurrentItem`` is replaced
    #: by ``aria-current="page"``, this package's current-item hook (the one
    #: breadcrumbs.pt emits and Clara styles on the global nav).
    item_template = ViewPageTemplateFile(_path("sitemap_item.pt"))

    def _renderLevel(self, children=(), level=2):
        """The nested list, with this package's hooks.

        Same recursion as the stock method (children render *inside* their
        parent's ``<li>``, which is what makes it a tree); the dead classic
        classes are dropped and the nesting level rides on a data attribute
        instead of a class per depth — a selector nobody writes against
        ``navTreeLevel7``. ``createSiteMap`` always passes ``children``, so
        the empty default is only the stock signature kept (immutable here).
        """
        output = ""
        for node in children:
            output += "<li>\n"
            output += self.item_template(node=node)
            nested = node.get("children", ())
            if nested:
                inner = self._renderLevel(nested, level + 1)
                output += (
                    f'<ul class="plone-sitemap__level" data-level="{level}">\n{inner}\n</ul>\n'
                )
            output += "</li>\n"

        return output


class ContactInfoPagelet(ContactForm, FramedPage):
    """``contact-info``: the stock ContactForm, framed.

    ``form.Form.__call__`` stays in charge — ``update()`` runs the button
    handler (which sends the mail and sets ``success``), then ``render()``
    calls ``self.template``, which is where the frame takes over.

    It is a **modal action** (the ``contact`` site action carries a ``modal``
    property in CMFPlone's actions.xml), so it needs the ``#content``
    extraction point — supplied for every framed page by the framed body
    element (pagelets/framed.py), plus the ``<h1>`` and ``.formControls`` the
    body template keeps. See docs/porting-main-template.md, "Modal
    consumers".
    """

    template = FramedTemplate(_path("contact_info.pt"))
