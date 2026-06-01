"""
整理版入口：多策略同雜訊比較（組 A：單腳靜態／雙腳之字形靜態；組 B：糾纏交換 L=3）。

執行:
  python compare_models.py
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
    from compare_models_impl import main as impl_main

    impl_main()


if __name__ == "__main__":
    main()

