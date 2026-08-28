#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiskg_external_re.public_export import main


if __name__ == "__main__":
    raise SystemExit(main())
