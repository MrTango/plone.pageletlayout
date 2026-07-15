"""A Five-compatible ``plone:pagelet`` ZCML directive.

z3c.pagelet's own ``z3c:pagelet`` directive wires security with
zope.security checkers, which the Zope 2 publisher never consults —
in Plone the permission is silently ignored (verified in
tests/test_pagelet_hello.py). This directive keeps z3c.pagelet's
registration semantics but applies AccessControl security the same way
Products.Five's ``browser:page`` does: protectClass + protectName +
InitializeClass.
"""

import os.path

import zope.component.zcml
import zope.interface
from AccessControl.security import getSecurityInfo
from Products.Five.browser.metaconfigure import _configure_z2security
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.pagelet import interfaces
from z3c.template.interfaces import IContentTemplate
from z3c.template.interfaces import ILayoutTemplate
from z3c.template.template import TemplateFactory
from zope.browserpage import metaconfigure as viewmeta
from zope.configuration.exceptions import ConfigurationError
from zope.contentprovider.interfaces import IContentProvider
from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from plone.pageletlayout.chrome import ChromePagelet
from plone.pageletlayout.page import PageletPage


# The attributes ZPublisher may touch on a published pagelet.
PUBLISH_ATTRIBUTES = ("__call__", "browserDefault", "update", "render", "publishTraverse")


def pageletDirective(
    _context,
    class_,
    name,
    permission,
    for_=zope.interface.Interface,
    layer=IDefaultBrowserLayer,
    provides=interfaces.IPagelet,
    allowed_interface=None,
    allowed_attributes=None,
    **kwargs,
):
    permission = viewmeta._handle_permission(_context, permission)

    ifaces = list(zope.interface.Declaration(provides).flattened())
    if interfaces.IPagelet not in ifaces:
        raise ConfigurationError("Provides interface must inherit IPagelet.")

    # Same class construction as z3c.pagelet.zcml, plus the class's own
    # AccessControl declarations (ClassSecurityInfo), like Five's page().
    # PageletPage instead of plain BrowserPagelet: every published pagelet
    # gets the response headers + post-render Diazo bypass (ticket 07).
    cdict = {"__name__": name}
    cdict.update(kwargs)
    cdict.update(getSecurityInfo(class_))
    new_class = type(class_.__name__, (class_, PageletPage), cdict)

    if not provides.implementedBy(new_class):
        zope.interface.classImplements(new_class, provides)

    # Security map: class default ('') plus every publishable attribute.
    required = {}
    for attr in ("",) + PUBLISH_ATTRIBUTES:
        required[attr] = permission
    viewmeta._handle_allowed_interface(_context, allowed_interface, permission, required)
    viewmeta._handle_allowed_attributes(_context, allowed_attributes, permission, required)
    viewmeta._handle_allowed_attributes(_context, kwargs.keys(), permission, required)

    viewmeta._handle_for(_context, for_)

    # The bridge: Zope 2 / AccessControl security instead of zope.security.
    _configure_z2security(_context, new_class, required)

    _context.action(
        discriminator=("pagelet", for_, layer, name),
        callable=zope.component.zcml.handler,
        args=("registerAdapter", new_class, (for_, layer), provides, name, _context.info),
    )


def chromePageletDirective(
    _context,
    name,
    class_=None,
    template=None,
    for_=zope.interface.Interface,
    layer=IDefaultBrowserLayer,
    view=IBrowserView,
):
    """Register both facets of a chrome pagelet in one stroke.

    Provider facet: named IContentProvider multi-adapter on
    (for_, layer, view) — what the ``provider:`` expression looks up.
    Template facet: the content template as IContentTemplate adapter,
    registered for the *user's* class so any further subclass (e.g. the
    one plone:pagelet synthesizes to publish the same element) inherits it.

    Deliberately no permission attribute: a provider adapter is never
    traversed by ZPublisher, so there is nothing that would enforce one
    (the z3c:pagelet lesson again). Conditional visibility belongs in
    update()/render().
    """
    if class_ is None and template is None:
        raise ConfigurationError(
            "plone:chromepagelet needs 'class' and/or 'template'."
        )

    bases = () if class_ is None else (class_,)
    if class_ is None or not issubclass(class_, ChromePagelet):
        bases += (ChromePagelet,)
    new_class = type(bases[0].__name__, bases, {"__name__": name})

    _context.action(
        discriminator=("chromePagelet", for_, layer, view, name),
        callable=zope.component.zcml.handler,
        args=(
            "registerAdapter",
            new_class,
            (for_, layer, view),
            IContentProvider,
            name,
            _context.info,
        ),
    )

    if template is not None:
        template_for = class_ if class_ is not None else new_class
        templateDirective(_context, template, for_=template_for, layer=layer)


class FiveTemplateFactory(TemplateFactory):
    """z3c.template factory rendering with Zope's own template machinery.

    z3c.template's TemplateFactory uses zope.browserpage's
    ViewPageTemplateFile, whose engine has no ``provider:`` expression
    (LookupError at compile time) — another component from the Zope 3
    world. Products.Five's ViewPageTemplateFile is the class every
    ``browser:page`` template in Plone uses: trusted Zope engine,
    Chameleon-compiled, ``provider:`` registered.
    """

    def __init__(self, filename, contentType, macro=None):
        self.contentType = contentType
        self.template = ViewPageTemplateFile(filename, content_type=contentType)
        self.macro = macro


def templateDirective(
    _context,
    template,
    name="",
    for_=zope.interface.Interface,
    layer=IDefaultBrowserLayer,
    provides=IContentTemplate,
    contentType="text/html",
    macro=None,
    context=None,
):
    # Same registration semantics as z3c.template.zcml.templateDirective,
    # different factory.
    template = os.path.abspath(str(_context.path(template)))
    if not os.path.isfile(template):
        raise ConfigurationError("No such file", template)

    factory = FiveTemplateFactory(template, contentType, macro)
    zope.interface.directlyProvides(factory, provides)

    if context is not None:
        for_ = (for_, layer, context)
    else:
        for_ = (for_, layer)

    if name:
        zope.component.zcml.adapter(_context, (factory,), provides, for_, name=name)
    else:
        zope.component.zcml.adapter(_context, (factory,), provides, for_)


def layoutTemplateDirective(
    _context,
    template,
    name="",
    for_=zope.interface.Interface,
    layer=IDefaultBrowserLayer,
    provides=ILayoutTemplate,
    contentType="text/html",
    macro=None,
    context=None,
):
    templateDirective(
        _context, template, name, for_, layer, provides, contentType, macro, context
    )
