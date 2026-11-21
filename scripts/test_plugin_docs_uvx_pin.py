"""Plugin docs launch the Python servers on Python 3.13.

n24q02m-crg, n24q02m-mnemo, n24q02m-telegram and n24q02m-wet all declare
``Requires-Python ==3.13.*``. Without ``--python 3.13`` uvx uses the default
interpreter: below 3.13 the install fails, and on 3.14 or newer uv ignores the
upper bound and runs the server on a Python it does not support.

Only the pages at ``plugins/<name>/*.md`` are written here; manifests, hooks and
skills under each plugin are synced from the server repositories.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNPINNED = re.compile(r"uvx (--from )?n24q02m-(crg|mnemo|telegram|wet)\b")


def test_plugin_pages_pin_python_3_13_for_uvx_launches():
    hits = [
        f"{page.relative_to(ROOT).as_posix()}:{number}: {line.strip()}"
        for page in sorted(ROOT.glob("plugins/*/*.md"))
        for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1)
        if UNPINNED.search(line)
    ]
    assert not hits, "uvx launch without --python 3.13:\n" + "\n".join(hits)
