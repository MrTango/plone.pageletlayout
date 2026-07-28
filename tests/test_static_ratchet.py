"""Static ratchet: no new main_template macro consumers on our layer.

The verification harness' second meter (classic-coverage map, ticket 04).
The bridge keeps the macro path *working* forever, but it must not spread:
this test walks the component registry for template-bearing registrations
reachable with the pageletlayout layer active whose template file still
references ``main_template`` — i.e. everything that renders via the
bridge's macro path — and compares the set against the checked-in
allowlist ``main_template_allowlist.txt``.

- An entry **not** in the allowlist fails: someone added a new macro
  consumer. Build the page on ``plone:pagelet`` instead (see
  docs/porting-main-template.md).
- An allowlist entry that is no longer collected fails too: a consumer was
  converted (or its registration shadowed by a layer-specific override) —
  the ratchet clicks down, remove the stale line.

With the bridge permanent, the steady state of the list is the
out-of-scope admin long tail; conversions (map tickets 05-10) shrink it.

Registry walk, not filesystem grep (in-ticket decision): the registry
knows what is *reachable* — a registration shadowed by a more specific
one on our layer (e.g. classic ``main_template`` behind the bridge, or
the S1 ``layout.pt`` once ticket 05 registers the layer-specific
``ILayoutTemplate``) drops out of the collection automatically, which is
exactly the click-down signal the ratchet meters. Limitations: the walk
sees template *files*, so a new registration reusing an already-
allowlisted template file does not trip it; and only registrations whose
factory carries the template as an ``index``/``template`` attribute are
seen (skin templates and code-built templates are not — the live-surface
walk is the companion meter covering rendered output).
"""

import functools
import pathlib
import unittest

from zope.component import getGlobalSiteManager
from zope.interface import Interface
from zope.interface import providedBy

from plone.pageletlayout.bridge import BridgedMainTemplate
from plone.pageletlayout.testing import INTEGRATION_TESTING


def _template_filenames(factory):
    """The page-template file paths a registration's factory carries."""
    filenames = set()
    for attr in ("index", "template"):
        template = getattr(factory, attr, None)
        filename = getattr(template, "filename", None)
        if filename:
            filenames.add(str(filename))
    return filenames


@functools.lru_cache(maxsize=None)
def _references_main_template(filename):
    try:
        with open(filename, encoding="utf-8") as fh:
            return "main_template" in fh.read()
    except OSError:
        return False


def _normalize(filename):
    """Environment-independent allowlist entry for a template path."""
    path = filename.replace("\\", "/")
    for marker in ("/site-packages/", "/src/"):
        if marker in path:
            return path.rsplit(marker, 1)[1]
    return path


def _is_bridge(factory):
    return isinstance(factory, type) and issubclass(factory, BridgedMainTemplate)


def _iter_registrations(site_manager):
    """All adapter registrations, including the stacked bases.

    plone.testing stacks global registries (zca.pushGlobalRegistry), and
    ``registeredAdapters()`` yields only a registry's own registrations —
    the Plone core ones live in the bases, so walk the whole chain.
    """
    seen = set()
    stack = [site_manager]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield from current.registeredAdapters()
        stack.extend(getattr(current, "__bases__", ()))


def collect_macro_consumers(request):
    """The normalized template paths rendering via the bridged macro path.

    Walks the global component registry for two-required adapter
    registrations (context-ish, layer-ish) that are reachable on
    ``request`` (its provided interfaces satisfy the registration's
    requirements), carry a page template file (``index`` or ``template``
    attribute), and whose template source references ``main_template`` —
    excluding registrations shadowed by a more specific one for the same
    (context requirement, provided, name), and excluding the bridge
    itself (the macro *provider*, not a consumer).
    """
    gsm = getGlobalSiteManager()
    request_spec = providedBy(request)
    consumers = set()
    for registration in _iter_registrations(gsm):
        if len(registration.required) != 2:
            continue
        context_req, layer_req = (
            spec if spec is not None else Interface
            for spec in registration.required
        )
        if not request_spec.isOrExtends(layer_req):
            continue  # never reachable with our layer stack
        factory = registration.factory
        if factory is None or _is_bridge(factory):
            continue
        filenames = {
            filename
            for filename in _template_filenames(factory)
            if _references_main_template(filename)
        }
        if not filenames:
            continue
        # Shadow check: would this factory still win for a context
        # providing exactly its requirement, on our actual request?
        winner = gsm.adapters.lookup(
            (context_req, request_spec), registration.provided, registration.name
        )
        if winner is not factory:
            continue
        consumers.update(_normalize(filename) for filename in filenames)
    return consumers


ALLOWLIST_PATH = pathlib.Path(__file__).parent / "main_template_allowlist.txt"


def load_allowlist():
    """The checked-in allowlist: one entry per line, ``#`` comments."""
    if not ALLOWLIST_PATH.exists():
        return set()
    entries = set()
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.add(line)
    return entries


class TestStaticRatchet(unittest.TestCase):
    """The collected consumer set matches the checked-in allowlist exactly."""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.actual = collect_macro_consumers(self.layer["request"])
        self.allowlisted = load_allowlist()

    def test_no_unexpected_macro_consumers(self):
        new = sorted(self.actual - self.allowlisted)
        self.assertEqual(
            new,
            [],
            "\nNew main_template macro consumers reachable on the "
            "pageletlayout layer:\n  "
            + "\n  ".join(new)
            + "\nBuild new pages with plone:pagelet instead of the deprecated "
            "macro path (see docs/porting-main-template.md). If a consumer is "
            "genuinely unavoidable long-tail, add it to "
            "tests/main_template_allowlist.txt with a comment.",
        )

    def test_ratchet_clicks_down(self):
        stale = sorted(self.allowlisted - self.actual)
        self.assertEqual(
            stale,
            [],
            "\nAllowlist entries no longer render via the macro path "
            "(converted or shadowed) — the ratchet clicks down, remove these "
            "lines from tests/main_template_allowlist.txt:\n  "
            + "\n  ".join(stale),
        )


class TestMacroConsumerCollector(unittest.TestCase):
    """The registry walk has teeth: finds real consumers, skips shadows."""

    layer = INTEGRATION_TESTING

    def setUp(self):
        self.request = self.layer["request"]

    def collect(self):
        return collect_macro_consumers(self.request)

    def test_finds_known_macro_consumers(self):
        # accessibility-info.pt (steady-state long tail, bridged forever) is
        # a live-verified macro consumer — if the walk misses it the walk is
        # vacuous and the ratchet is meaningless. (login.pt stood here until
        # ticket 06 converted it, search.pt until ticket 07.)
        consumers = self.collect()
        self.assertTrue(
            any(
                path.endswith("/templates/accessibility-info.pt")
                for path in consumers
            ),
            f"walk missed accessibility-info.pt — collected {len(consumers)} entries",
        )

    def test_search_conversion_shadowed(self):
        # Ticket 07's plone:pagelet registration for `search` on our layer
        # beats CMFPlone's browser:page, so the classic search.pt drops out
        # of the walk: the ticket-07 click-down, pinned.
        consumers = self.collect()
        self.assertFalse(
            [
                path
                for path in consumers
                if path.endswith("CMFPlone/browser/templates/search.pt")
            ],
            "the converted @@search no longer shadows the classic search.pt",
        )

    def test_sharing_conversion_shadowed(self):
        # Ticket 08 shadows BOTH stock registrations carrying sharing.pt —
        # the `sharing` page and the `updateSharingInfo` fragment, which is
        # the same class and so the same template attribute. Missing either
        # would leave the file in the walk: the click-down needs both.
        consumers = self.collect()
        self.assertFalse(
            [
                path
                for path in consumers
                if path.endswith("plone/app/workflow/browser/sharing.pt")
            ],
            "the converted @@sharing no longer shadows the classic sharing.pt",
        )

    def test_content_actions_conversion_shadowed(self):
        # Ticket 09's four pages. object_rename.pt needs BOTH stock names
        # shadowed — `object_rename` and `folder_rename` are one class and
        # so one `template` attribute (the ticket-08 lesson again).
        consumers = self.collect()
        for template in (
            "plone/app/content/browser/templates/delete_confirmation.pt",
            "plone/app/content/browser/templates/object_rename.pt",
            "plone/app/content/browser/templates/content_status_history.pt",
            "plone/app/layout/viewlets/history_view.pt",
        ):
            with self.subTest(template=template):
                self.assertFalse(
                    [path for path in consumers if path.endswith(template)],
                    f"the conversion no longer shadows the classic {template}",
                )

    def test_s1_form_layout_shadowed(self):
        # Ticket 05's seam (pagelets/forms.py) registers the wrapped-form
        # frame for (IFormWrapper, IPlonePageletlayoutLayer) — more
        # specific than plone.app.z3cform's layout_factory on the form
        # layer (ours extends it), so the macro-path layout.pt is shadowed
        # out of the collection: the S1 ratchet click-down, pinned.
        consumers = self.collect()
        self.assertFalse(
            [
                path
                for path in consumers
                if path.endswith("plone/app/z3cform/templates/layout.pt")
            ],
            "the S1 seam no longer shadows plone.app.z3cform's layout.pt",
        )
        # ... and the doubly-shadowed base (plone.z3cform's own layout.pt)
        # must not surface either.
        self.assertFalse(
            [
                path
                for path in consumers
                if path.endswith("plone/z3cform/pagetemplates/layout.pt")
            ],
            "shadowed plone.z3cform layout.pt was collected",
        )

    def test_shadowed_classic_master_not_listed(self):
        # CMFPlone's own main_template registration is shadowed by the
        # bridge on our layer — a shadowed registration cannot render, so
        # it must not pollute the allowlist.
        consumers = self.collect()
        self.assertFalse(
            [
                path
                for path in consumers
                if path.endswith("CMFPlone/browser/templates/main_template.pt")
            ],
            "shadowed classic main_template registration was collected",
        )

    def test_bridge_provider_not_listed(self):
        # The bridge frame mentions main_template in its comments but is
        # the shim itself, not a consumer.
        consumers = self.collect()
        self.assertFalse(
            [
                path
                for path in consumers
                if path.endswith("pageletlayout/templates/main_template.pt")
            ],
            "the bridge's own frame was collected as a consumer",
        )

    def test_paths_are_environment_independent(self):
        # Entries are checked into the allowlist, so they must not embed
        # the venv location: everything is relative to site-packages (or
        # the package src root for editable installs).
        consumers = self.collect()
        absolute = [path for path in consumers if path.startswith("/")]
        self.assertEqual(absolute, [], "allowlist entries leak absolute paths")
