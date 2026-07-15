"""Update message catalogs using i18ndude.

Usage:
    python update.py
"""

import glob
import os
import subprocess
from importlib.resources import files


domain = "plone.pageletlayout"
os.chdir(str(files(domain)))
os.chdir("../../../")
target_path = "src/plone/pageletlayout/"
locale_path = target_path + "locales/"
i18ndude = "i18ndude"

# ignore node_modules files resulting in errors
excludes = "*.html *json-schema*.xml"


def locale_folder_setup():
    os.chdir(locale_path)
    languages = [d for d in os.listdir(".") if os.path.isdir(d)]
    for lang in languages:
        folder = os.listdir(lang)
        if "LC_MESSAGES" in folder:
            continue
        lc_messages_path = lang + "/LC_MESSAGES/"
        os.mkdir(lc_messages_path)
        subprocess.call(
            [
                "msginit",
                f"--locale={lang}",
                f"--input={domain}.pot",
                f"--output={lang}/LC_MESSAGES/{domain}.po",
            ]
        )
    os.chdir("../../../../")


def _rebuild():
    subprocess.call(
        [
            i18ndude,
            "rebuild-pot",
            "--pot",
            f"{locale_path}/{domain}.pot",
            "--exclude",
            excludes,
            "--create",
            domain,
            target_path,
        ]
    )


def _sync():
    po_files = glob.glob(f"{locale_path}*/LC_MESSAGES/{domain}.po")
    subprocess.call(
        [i18ndude, "sync", "--pot", f"{locale_path}/{domain}.pot", *po_files]
    )


def update_locale():
    locale_folder_setup()
    _sync()
    _rebuild()


if __name__ == "__main__":
    update_locale()
