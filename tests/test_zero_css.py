"""plone.pageletlayout ships ZERO CSS — the structural guard (wayfinder t.15).

The destination's final "Reached when" criterion: the integration base ships
zero CSS bundles. Ticket 04 removed the six theme bundles; ticket 15 removed the
last one (the editor-toolbar chrome, now theme-owned in plonetheme.clara). This
no-portal, no-browser guard pins that the base stays CSS-less end to end:

  * the default profile's registry.xml registers NO IBundleRegistry records;
  * no static resource directory / vendored stylesheet remains to register;
  * configure.zcml no longer serves ++resource++plone.pageletlayout/;
  * upgrades.py still purges BOTH relocated bundle families from installed
    sites (fresh installs get the trimmed profile; old sites get cleaned).
"""
import re
from pathlib import Path


PKG = Path(__file__).resolve().parent.parent / "src" / "plone" / "pageletlayout"
REGISTRY_XML = PKG / "profiles" / "default" / "registry.xml"
CONFIGURE_ZCML = PKG / "configure.zcml"
UPGRADES_PY = PKG / "upgrades.py"


def _strip_xml_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def test_registry_registers_zero_css_bundles():
    """The default profile registers no CSS bundle records at all."""
    body = _strip_xml_comments(REGISTRY_XML.read_text())
    assert "IBundleRegistry" not in body, "a bundle record survives in registry.xml"
    assert "csscompilation" not in body, "a CSS bundle csscompilation survives"
    assert "plone.bundles" not in body


def test_no_static_resource_directory_on_disk():
    """No static/ tree remains — nothing to serve, nothing to bundle."""
    assert not (PKG / "static").exists(), "the base still ships a static/ directory"
    # and specifically the vendored toolbar sheet is gone
    assert not list(PKG.glob("static/**/*.css"))


def test_configure_serves_no_resource_directory():
    """configure.zcml no longer registers a browser:resourceDirectory."""
    body = _strip_xml_comments(CONFIGURE_ZCML.read_text())
    assert "resourceDirectory" not in body
    assert "directory=\"static\"" not in body


def test_upgrades_purge_both_relocated_bundle_families():
    """Installed sites get every relocated bundle purged — the six theme
    bundles (ticket 04) AND the toolbar chrome (ticket 15)."""
    src = UPGRADES_PY.read_text()
    assert "pageletlayout-toolbar" in src, "no upgrade purges the toolbar bundle"
    assert "remove_toolbar_bundle" in src
    assert "remove_theme_css_bundles" in src
