#!/bin/bash
# i18ndude should be available in the current $PATH. Install it via:
#   uv tool install i18ndude
#
# For every language you want to translate into you need a
# locales/[language]/LC_MESSAGES/plone.pageletlayout.po
# (e.g. locales/de/LC_MESSAGES/plone.pageletlayout.po)

domain=plone.pageletlayout

i18ndude rebuild-pot --pot $domain.pot --create $domain ../
i18ndude sync --pot $domain.pot */LC_MESSAGES/$domain.po
