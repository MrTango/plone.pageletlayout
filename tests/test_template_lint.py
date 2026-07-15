"""§7/§10 utility lint for the front-end markup contract.

Design principle #3: the layout templates carry NO Bootstrap spacing / grid /
flex utilities. Layout is done by the ``plone-*`` primitives + the layout grid;
a token change (never a template edit) restyles the site. This lint fails the
build on any forbidden utility so the ban can't rot as templates evolve — the
same discipline as Clara's token drift guard, kept file-based and fast (no
Plone layer, no browser).

Scope: the front-end markup contract in ``pagelets/templates/`` — the templates
bound for ``plone.app.layout`` upstream. The admin ``@@manage-layout-viewlets``
screens under ``templates/`` are self-contained Bootstrap admin pages (they pull
in the resource-registry CSS on purpose) and are NOT the contract surface, so
they are deliberately not scanned.

The check reads only ``class="..."`` attribute values, not comments or prose,
so a ``.row``/``.col`` mentioned in an explanatory comment (e.g. layout.pt) is
not a false positive — only a real class token is.
"""

import re
import unittest

import plone.pageletlayout


#: The template tree that is the markup contract (bound for plone.app.layout).
TEMPLATE_DIR = f"{plone.pageletlayout.__path__[0]}/pagelets/templates"

#: Every ``class="..."`` / ``class='...'`` attribute value in a template.
_CLASS_ATTR = re.compile(r"""class=(?P<q>["'])(?P<value>.*?)(?P=q)""", re.DOTALL)

#: A single class token is forbidden when it is a Bootstrap spacing/grid/flex
#: utility: m/p margins+paddings (mt-3, px-2, …), g gutters (g-4), d-flex, the
#: flex alignment utilities, and the .row/.col grid shells (bare or sized).
_FORBIDDEN_TOKEN = re.compile(
    r"""^(?:
        [mp][trblxyse]?-\d+          # m-3, mt-2, px-4, ms-1 …
        | g-\d+                      # g-4 grid gutter
        | d-flex                     # display flex
        | justify-content-[a-z]+     # justify-content-between …
        | align-items-[a-z]+         # align-items-center …
        | row                        # grid row shell
        | col(?:-[a-z0-9]+)*         # col, col-6, col-md-4 …
    )$""",
    re.VERBOSE,
)


def forbidden_in_markup(markup):
    """Return the list of (class-value, offending-token) pairs in ``markup``.

    Only class-attribute values are inspected; each is split on whitespace and
    each token matched against the forbidden set. TAL interpolations
    (``${python: …}``) tokenize into non-class fragments that never match.
    """
    hits = []
    for match in _CLASS_ATTR.finditer(markup):
        value = match.group("value")
        for token in value.split():
            if _FORBIDDEN_TOKEN.match(token):
                hits.append((value, token))
    return hits


def scan_template_tree():
    """Map each template path to its forbidden-utility hits (empty == clean)."""
    import os

    report = {}
    for name in sorted(os.listdir(TEMPLATE_DIR)):
        if not name.endswith(".pt"):
            continue
        path = f"{TEMPLATE_DIR}/{name}"
        with open(path, encoding="utf-8") as fh:
            hits = forbidden_in_markup(fh.read())
        if hits:
            report[name] = hits
    return report


class TestTemplateUtilityLint(unittest.TestCase):
    def test_no_forbidden_utilities_in_templates(self):
        report = scan_template_tree()
        self.assertEqual(
            report,
            {},
            f"Forbidden Bootstrap utilities in the markup contract: {report}. "
            "Layout belongs to the plone-* primitives + the layout grid, not "
            "utility classes (design principle #3 / §10).",
        )

    def test_lint_catches_planted_violation(self):
        # A planted violation must be caught (proves the lint has teeth).
        bad = '<div class="element-x mb-3 d-flex col-6 justify-content-between">'
        hits = {token for _value, token in forbidden_in_markup(bad)}
        self.assertEqual(hits, {"mb-3", "d-flex", "col-6", "justify-content-between"})

    def test_lint_ignores_clean_markup_and_comments(self):
        # plone-* primitives + reused Bootstrap component classes are allowed;
        # a .row/.col named inside a COMMENT is not a class token → not a hit.
        clean = (
            "<!-- No Bootstrap .container, no .row/.col here -->\n"
            '<ul class="plone-cluster element-globalnav">'
            '<input class="searchField form-control">'
            '<span class="column collapse">'
        )
        self.assertEqual(forbidden_in_markup(clean), [])
