"""Static ratchet: no new viewlets in managers nothing renders.

The verification harness' third meter, and the companion to the deprecation
signal in ``pagelets/managers.py``. That signal only fires for viewlets that
actually render — i.e. viewlets in a manager we bridge. A viewlet in an
*unbridged* manager is worse off: it disappears with no exception, no log
line, no marker in the page. Nothing would ever tell anyone. That silence is
what this ratchet meters.

It collects every reachable, unshadowed ``IViewlet`` registration whose
manager is neither the layout's own ``ILayoutManager`` nor one of the
managers ``managers.RENDERED_MANAGERS`` names, and compares the set against
the checked-in allowlist ``orphan_viewlets_allowlist.txt``.

- An entry **not** in the allowlist fails: a viewlet was added that will
  silently disappear. Either register it into ``ILayoutManager`` (see
  docs/porting-main-template.md) or bridge its manager.
- An allowlist entry no longer collected fails too: the viewlet was ported
  or its manager bridged — the ratchet clicks down, remove the stale line.

The registry walk mirrors tests/test_static_ratchet.py (read that one first;
it is the template this copies). One thing is specific here:
``browser:viewlet`` registers a **4-tuple** adapter
``(context, layer, view, manager)`` providing ``IViewlet``, so
``registration.required[3]`` *is* the target manager interface — no name
resolution needed for the manager the viewlet binds to. The manager
*names* in ``RENDERED_MANAGERS`` are turned into interfaces by walking the
``viewletManager`` registrations, so the two never drift.

Limitation, same shape as the other ratchet: the walk sees registrations,
so a viewlet registered at runtime (or one whose manager registration is
missing entirely) is invisible to it.
"""

import pathlib
import re
import unittest

from zope.component import getGlobalSiteManager
from zope.interface import Interface
from zope.interface import providedBy
from zope.viewlet.interfaces import IViewlet
from zope.viewlet.interfaces import IViewletManager

from plone.pageletlayout.pagelets.layout import ILayoutManager
from plone.pageletlayout.pagelets.managers import RENDERED_MANAGERS
from plone.pageletlayout.pagelets.managers import viewlet_class_origin
from plone.pageletlayout.testing import INTEGRATION_TESTING
from tests.test_static_ratchet import _iter_registrations
from tests.test_static_ratchet import _normalize as _relative_path
from tests.test_static_ratchet import load_allowlist


ALLOWLIST_PATH = pathlib.Path(__file__).parent / "orphan_viewlets_allowlist.txt"


def rendered_manager_interfaces():
    """The manager interfaces behind ``RENDERED_MANAGERS``, from the registry.

    ``browser:viewletManager`` registers the manager class as a named
    three-required adapter providing the manager's own interface, so the
    registry is the single source of truth for name -> interface. Resolving
    it here rather than importing plone.app.layout's interfaces keeps
    managers.py's table (names, which is what ZCML uses) authoritative.
    """
    found = {ILayoutManager}
    for registration in _iter_registrations(getGlobalSiteManager()):
        if len(registration.required) != 3 or registration.name not in RENDERED_MANAGERS:
            continue
        if not registration.provided.isOrExtends(IViewletManager):
            continue
        found.add(registration.provided)
    return found


#: Any absolute path embedded in a synthesized class name.
_ABSOLUTE_PATH = re.compile(r"/\S+")


def _allowlist_entry(factory, manager):
    """The allowlist entry for one orphaned viewlet registration.

    ``<manager interface> <viewlet class>``, the manager first so the file
    groups by manager when sorted. The class is the one the add-on wrote,
    not the one ``browser:viewlet`` synthesized (``viewlet_class_origin``);
    for a template-only viewlet the synthesized name embeds the template's
    absolute path, which is trimmed to the same site-packages-relative form
    the macro ratchet checks in.
    """
    name = viewlet_class_origin(factory)
    name = _ABSOLUTE_PATH.sub(lambda match: _relative_path(match.group(0)), name)
    return f"{manager.__identifier__} {name}"


def collect_orphan_viewlets(request):
    """Viewlet registrations reachable on ``request`` that nothing renders.

    Reachable: the request's provided interfaces satisfy the registration's
    layer requirement. Unshadowed: the same factory still wins a lookup for
    a context providing exactly its own requirement — a viewlet whose
    registration is overridden by a more specific one cannot render, so it
    is not an orphan.
    """
    gsm = getGlobalSiteManager()
    request_spec = providedBy(request)
    rendered = rendered_manager_interfaces()
    orphans = set()
    for registration in _iter_registrations(gsm):
        if len(registration.required) != 4 or registration.provided is not IViewlet:
            continue
        context_req, layer_req, view_req, manager_req = (
            spec if spec is not None else Interface for spec in registration.required
        )
        if not request_spec.isOrExtends(layer_req):
            continue  # never reachable with our layer stack
        if manager_req in rendered:
            continue  # its manager reaches the page
        factory = registration.factory
        if factory is None:
            continue
        winner = gsm.adapters.lookup(
            (context_req, request_spec, view_req, manager_req),
            IViewlet,
            registration.name,
        )
        if winner is not factory:
            continue  # shadowed by a more specific registration
        orphans.add(_allowlist_entry(factory, manager_req))
    return orphans


class TestViewletRatchet(unittest.TestCase):
    """The collected orphan set matches the checked-in allowlist exactly."""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.actual = collect_orphan_viewlets(self.layer["request"])
        self.allowlisted = load_allowlist(ALLOWLIST_PATH)

    def test_no_unexpected_orphan_viewlets(self):
        new = sorted(self.actual - self.allowlisted)
        self.assertEqual(
            new,
            [],
            "\nThese viewlets will silently disappear — their manager is "
            "never rendered by the pagelet layout:\n  "
            + "\n  ".join(new)
            + "\nRegister the viewlet into "
            "plone.pageletlayout.pagelets.layout.ILayoutManager (see "
            "docs/porting-main-template.md), or bridge its manager in "
            "pagelets/managers.py. If it is genuinely out of scope, add it "
            "to tests/orphan_viewlets_allowlist.txt with a comment.",
        )

    def test_ratchet_clicks_down(self):
        stale = sorted(self.allowlisted - self.actual)
        self.assertEqual(
            stale,
            [],
            "\nAllowlist entries are no longer orphaned (ported, bridged or "
            "shadowed) — the ratchet clicks down, remove these lines from "
            "tests/orphan_viewlets_allowlist.txt:\n  "
            + "\n  ".join(stale),
        )


class TestOrphanCollector(unittest.TestCase):
    """The registry walk has teeth: it sees orphans, and only orphans."""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.request = self.layer["request"]

    def test_bridged_managers_contribute_no_orphans(self):
        # Every manager the bridges render must be excluded wholesale — a
        # viewlet in one of them is reachable, not orphaned.
        orphans = collect_orphan_viewlets(self.request)
        for manager in ("IBelowContentBody", "IPortalFooter", "IAboveContentBody"):
            with self.subTest(manager=manager):
                self.assertFalse(
                    [
                        entry
                        for entry in orphans
                        if entry.startswith(
                            f"plone.app.layout.viewlets.interfaces.{manager} "
                        )
                    ],
                    f"{manager} is bridged, so its viewlets are not orphans",
                )

    def test_layout_manager_contributes_no_orphans(self):
        # The layout's own thirteen-plus elements are the destination the
        # ratchet points at; they must never be reported as orphans.
        orphans = collect_orphan_viewlets(self.request)
        self.assertFalse(
            [entry for entry in orphans if "ILayoutManager" in entry],
            "the layout's own elements were collected as orphans",
        )

    def test_head_managers_are_the_known_orphans(self):
        # The walk is not vacuous: the head managers are reimplemented, not
        # bridged (head.py wraps individual renderers), so their viewlets are
        # genuinely orphaned — and they must be visible to the walk or the
        # ratchet means nothing.
        orphans = collect_orphan_viewlets(self.request)
        self.assertTrue(
            [
                entry
                for entry in orphans
                if entry.startswith("plone.app.layout.viewlets.interfaces.IHtmlHead ")
            ],
            f"walk missed the IHtmlHead viewlets — collected {len(orphans)} entries",
        )

    def test_entries_are_environment_independent(self):
        # Entries are checked in. A template-only viewlet is named after its
        # template, so a path is expected — but never an absolute one, which
        # would embed this environment's venv location.
        orphans = collect_orphan_viewlets(self.request)
        self.assertEqual(
            [entry for entry in orphans if re.search(r"(?:^|\s)/", entry)],
            [],
            "allowlist entries leak absolute paths",
        )
