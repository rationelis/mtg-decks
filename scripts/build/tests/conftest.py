import sys
from pathlib import Path

_BUILD_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _BUILD_DIR.parent

for p in (str(_BUILD_DIR), str(_SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
