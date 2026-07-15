"""Invoke tasks for plone.pageletlayout."""
from invoke import task


@task
def install(c):
    """Install project dependencies."""
    c.run("uv sync")


@task
def start(c, instance="instance"):
    """Start a Plone instance."""
    c.run(f"uv run runwsgi var/{instance}/etc/zope.ini")


@task
def debug(c, instance="instance"):
    """Start a Plone instance in debug mode."""
    c.run(f"uv run runwsgi -d var/{instance}/etc/zope.ini")


@task
def shell(c, instance="instance"):
    """Open a Zope debug shell."""
    c.run(f"uv run zconsole debug var/{instance}/etc/zope.conf")


@task
def test(c, verbose=False):
    """Run tests."""
    cmd = "uv run --extra test pytest"
    if verbose:
        cmd += " -v"
    c.run(cmd)


@task
def create_instance(c, name="instance", port=8080):
    """Create a new Zope instance using the zope_instance template."""
    cmd = (
        f"copier copy --trust --defaults "
        f"--data instance_name={name} "
        f"--data port={port} "
    )
    cmd += "~/.copier-templates/plone-copier-templates/zope_instance ."
    c.run(cmd)


RECONFIGURE_TARGETS = {
    "addon": {
        "answers_file": ".copier-answers.yml",
        "template": "~/.copier-templates/plone-copier-templates/backend_addon",
    },
    "zope-setup": {
        "answers_file": ".copier-answers.zope-setup.yml",
        "template": "~/.copier-templates/plone-copier-templates/zope-setup",
    },
    "instance": {
        "answers_file": ".copier-answers.zope-instance-{name}.yml",
        "template": "~/.copier-templates/plone-copier-templates/zope_instance",
    },
}


@task
def reconfigure(c, target="instance", name="instance"):
    """Reconfigure a template target (re-asks all questions).

    Targets: addon, zope-setup, instance
    Use --name for instance targets (e.g. --name=instance2).
    """
    if target not in RECONFIGURE_TARGETS:
        print(f"Unknown target: {target}")
        print(f"Available targets: {', '.join(RECONFIGURE_TARGETS)}")
        return
    config = RECONFIGURE_TARGETS[target]
    answers_file = config["answers_file"].format(name=name)
    cmd = (
        f"copier recopy --trust --overwrite "
        f"-a {answers_file} "
        f"{config['template']} ."
    )
    c.run(cmd, pty=True)


@task
def create_site(c, site_id="Plone", instance="instance"):
    """Create a new Plone site."""
    import os
    import tempfile

    script = '''
from Testing.makerequest import makerequest
import transaction
app = makerequest(app)
from plone.distribution.api import site as site_api
site_api.create(
    app,
    "classic",
    {
        "site_id": "SITE_ID",
        "title": "Plonetheme Pagelet Base",
        "description": "A Plone theme base for themes based on pagelets",
        "default_language": "en",
        "portal_timezone": "UTC",
        "setup_content": False,
    },
)
transaction.commit()
print("Created site: SITE_ID")
'''.replace("SITE_ID", site_id)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name
    try:
        c.run(f"uv run zconsole run var/{instance}/etc/zope.conf {script_path}")
    finally:
        os.unlink(script_path)


@task
def format(c):
    """Format code with ruff."""
    c.run("uv run ruff format .")
    c.run("uv run ruff check --fix .")


@task
def lint(c):
    """Run linting checks."""
    c.run("uv run ruff check .")
