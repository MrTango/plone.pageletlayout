"""The login/password family as pagelets (classic-coverage map, ticket 06).

Every view of CMFPlone's browser/login package, re-registered on the
pageletlayout layer via the FramedPage mechanism: the stock view classes
keep their whole control flow — login POST handling, came_from redirects,
the pwreset four-template dispatch — and only the class-bound templates
are swapped for FramedTemplates wrapping body-only twins of the stock
templates (master-macro wrapper stripped, headings kept in the body).

Not converted: ``logout`` / ``require_login`` (pure redirects, no
template), ``failsafe_login`` (deliberately main_template-free),
``mail_password`` (returns the converted ``mail_password_response``
view's render), and the two ``*_template`` email bodies (not pages).
"""

import os.path

from Products.CMFPlone.browser.login.login import ForcedPasswordChange
from Products.CMFPlone.browser.login.login import InitialLoginPasswordChange
from Products.CMFPlone.browser.login.login import InsufficientPrivilegesView
from Products.CMFPlone.browser.login.login import LoginForm
from Products.CMFPlone.browser.login.login_help import LoginHelpForm
from Products.CMFPlone.browser.login.logout import LoggedOutView
from Products.CMFPlone.browser.login.password_reset import ExplainPWResetToolView
from Products.CMFPlone.browser.login.password_reset import PasswordResetView

from plone.pageletlayout.page import FramedPage
from plone.pageletlayout.page import FramedTemplate


def _path(filename):
    return os.path.join(os.path.dirname(__file__), "templates", filename)


class LoginPagelet(LoginForm, FramedPage):
    """@@login (and the BBB @@login_form): the stock z3c.form flow —
    ``Form.__call__`` update/redirect-check, external-login handling and
    no-cache headers in ``render()`` — with the framed login card as
    ``index``."""

    index = FramedTemplate(_path("login.pt"))


class LoginHelpPagelet(LoginHelpForm, FramedPage):
    """@@login-help: the stock subform machinery (reset-password /
    retrieve-username), framed."""

    index = FramedTemplate(_path("login_help.pt"))


class LoggedOutPagelet(LoggedOutView, FramedPage):
    """@@logged-out: the stock anonymous-redirect check; the framed page
    only ever renders for the still-authenticated (Zope-user) case."""

    index = FramedTemplate(_path("logged_out.pt"))


class InsufficientPrivilegesPagelet(InsufficientPrivilegesView, FramedPage):
    """@@insufficient-privileges, framed (no control flow of its own)."""

    index = FramedTemplate(_path("insufficient_privileges.pt"))


class MailPasswordFormPagelet(FramedPage):
    """@@mail_password_form: stock is template-only; the body carries the
    hand-written reset-request form."""

    index = FramedTemplate(_path("mail_password_form.pt"))


class MailPasswordResponsePagelet(FramedPage):
    """@@mail_password_response: also what @@mail_password returns —
    RegistrationTool.mailPassword looks this view up by name and returns
    its render, so converting it converts that flow too."""

    index = FramedTemplate(_path("mail_password_response.pt"))


class PasswordResetPagelet(PasswordResetView, FramedPage):
    """@@passwordreset: the stock four-template dispatch (``__call__`` +
    ``_reset_password`` choose between form / invalid / expired / finish,
    POST handling and the autologin redirect untouched), every branch
    framed. These four are exactly the registry-walk-invisible templates
    the ticket-04 harness noted — converted here, they never existed on
    the allowlist; the live corpus is their meter."""

    form = FramedTemplate(_path("pwreset_form.pt"))
    invalid = FramedTemplate(_path("pwreset_invalid.pt"))
    expired = FramedTemplate(_path("pwreset_expired.pt"))
    finish = FramedTemplate(_path("pwreset_finish.pt"))


class InitialLoginPasswordChangePagelet(InitialLoginPasswordChange, FramedPage):
    """@@initial-login-password-change: the stock PasswordPanel form,
    framed."""

    index = FramedTemplate(_path("initial_login_password_change.pt"))


class ForcedPasswordChangePagelet(ForcedPasswordChange, FramedPage):
    """@@forced-password-change: the stock PasswordPanel form, framed."""

    index = FramedTemplate(_path("forced_password_change.pt"))


class ExplainPWResetToolPagelet(ExplainPWResetToolView, FramedPage):
    """portal_password_reset/explainPWResetTool: the tool's settings page
    (stock POST handling in ``__call__``), framed on the tool context."""

    index = FramedTemplate(_path("explain_pwreset_tool.pt"))
