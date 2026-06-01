"""
整理版入口：一鍵產出 results/ 與 figures/。

執行:
  python competition_suite.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src() -> None:
    root = Path(__file__).resolve().parent
    src = root / "src"
    sys.path.insert(0, str(src))


def main() -> None:
    _bootstrap_src()
    from competition_suite_impl import main as impl_main

    impl_main()


if __name__ == "__main__":
    main()

