"""Bypass engine/__init__.py eager imports for V9 pipeline scripts.

engine/__init__.py imports ALL 202 engine modules (~2.3 MB of Python),
which takes 2+ minutes on cold start. V9 pipeline scripts only need
specific submodules, so we pre-register a lightweight engine package
stub to prevent __init__.py from executing.

Import this module BEFORE any `from engine.*` or `from make_apology`
or `from make_full_track` imports.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

if "engine" not in sys.modules:
    _stub = types.ModuleType("engine")
    _stub.__path__ = [str(Path(__file__).resolve().parent / "engine")]
    _stub.__package__ = "engine"
    sys.modules["engine"] = _stub
