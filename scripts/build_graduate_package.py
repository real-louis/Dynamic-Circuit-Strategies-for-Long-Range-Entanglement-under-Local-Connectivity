#!/usr/bin/env python3
"""One-click build for graduate-application deliverables."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ephys_root, prx_root, repo_root

ROOT = repo_root()
EPHYS = ephys_root()
PRX = prx_root()
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"


def _run(cmd: list[str], cwd: Path, label: str) -> bool:
    print(f"\n=== {label} ===")
    print(" ".join(cmd))
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Skipped or failed: {e}")
        return False


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"Copied {src.name} -> {dst}")


def main() -> int:
    FIGURES.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)

    if EPHYS.is_dir() and (EPHYS / "competition_suite.py").is_file():
        _run([sys.executable, "competition_suite.py"], EPHYS, "Ephys competition_suite")
        for name in ("crossover_p_success.png", "resources_cx_vs_L.png"):
            _copy_if_exists(EPHYS / "figures" / name, FIGURES / name)
        _copy_if_exists(EPHYS / "results" / "crossover_and_resources.csv", RESULTS / "crossover_and_resources.csv")
        _copy_if_exists(EPHYS / "results" / "resource_formula_table.csv", RESULTS / "resource_formula_table.csv")
    else:
        print(f"Ephys not found at {EPHYS}")

    if PRX.is_dir() and (PRX / "verify" / "test_equivalence.py").is_file():
        _run([sys.executable, "-m", "pytest", "verify/test_equivalence.py", "-q"], PRX, "PRX Quantum circuit tests")
    else:
        print(f"PRX not found at {PRX}")

    _run([sys.executable, "scripts/error_budget_analysis.py"], ROOT, "Error budget analysis")
    _run([sys.executable, "scripts/report_figures.py"], ROOT, "CHSH / CI / PRX verification figures")
    _run([sys.executable, "scripts/generate_word_reports.py"], ROOT, "Word reports (EN + ZH)")

    print("\n=== Graduate package ready ===")
    print(f"  Report (EN):  {ROOT / 'reports' / 'Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx'}")
    print(f"  Report (ZH):  {ROOT / 'reports' / '局域連接下長程糾纏動態電路策略_專題報告_ZH.docx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
