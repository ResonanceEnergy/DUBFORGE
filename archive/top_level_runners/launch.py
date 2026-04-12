#!/usr/bin/env python3
"""Compatibility shim.

Canonical entrypoint is forge.py:
    python forge.py --launch [--track ...] [--ui-only] [--render-only]

This wrapper is kept only so existing scripts/aliases do not break.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project = Path(__file__).resolve().parent
    forge = project / "forge.py"
    cmd = [sys.executable, str(forge), "--launch", *sys.argv[1:]]
    return subprocess.run(cmd, cwd=str(project)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
