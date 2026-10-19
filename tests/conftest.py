"""Default test run stays exactly 82 collected.

`tests/test_install_surface.py` builds a wheel and installs it into a scratch
venv (network + ~1 min). It is an opt-in contract gate, so it is not even
collected unless PROCESS_ATLAS_INSTALL_SURFACE=1 is set — that keeps the
default suite count stable and CI fast.

    PROCESS_ATLAS_INSTALL_SURFACE=1 python -m pytest tests/test_install_surface.py -q
"""

import os

collect_ignore = []

if os.environ.get("PROCESS_ATLAS_INSTALL_SURFACE") != "1":
    collect_ignore.append("test_install_surface.py")
