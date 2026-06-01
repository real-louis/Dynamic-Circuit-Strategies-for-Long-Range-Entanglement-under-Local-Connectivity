#!/usr/bin/env python3
"""
Package a monorepo layout ready for GitHub upload (external submission).

Creates:
  github_release/
    README.md
    REPRODUCE.md
    requirements.txt
    config/submission.json
    ephys/          (from ../2026:5:5, trimmed)
    prx/            (from ../2026:5:18)
    scripts/
    results/
    figures/
    reports/
    docs/

Run:
  python3 scripts/package_github_submission.py
  cd github_release && git init && git add . && git commit -m "Initial release"
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "github_release"
EPHYS = ROOT.parent / "2026:5:5"
PRX = ROOT.parent / "2026:5:18"

EPHYS_COPY = [
    "competition_suite.py",
    "compare_models.py",
    "requirements.txt",
    "requirements-lock.txt",
    "report_bell_table.md",
    "REPRODUCE.md",
    "src",
    "scripts/statevector_demo.py",
    "scripts/entanglement_swapping_demo.py",
]

PRX_COPY = [
    "circuits",
    "verify",
    "requirements.txt",
    "pytest.ini",
    "README.md",
    "demo.py",
]

SKIP_DIRS = {".pytest_cache", ".idea", "__pycache__", ".venv", "submission", "reports", "figures"}


def _copy_tree(src: Path, dst: Path, allow_files: list[str] | None = None) -> None:
    if allow_files is not None:
        dst.mkdir(parents=True, exist_ok=True)
        for name in allow_files:
            s = src / name
            d = dst / name
            if s.is_dir():
                shutil.copytree(s, d, ignore=shutil.ignore_patterns(*SKIP_DIRS), dirs_exist_ok=True)
            elif s.is_file():
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
        return
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(*SKIP_DIRS),
        dirs_exist_ok=True,
    )


def write_github_readme(cfg: dict) -> None:
    text = f"""# Dynamic Circuit Strategies for Long-Range Entanglement under Local Connectivity

[![Reproducible](https://img.shields.io/badge/reproducible-yes-green)](REPRODUCE.md)

Research code for *Dynamic Circuit Strategies for Long-Range Entanglement under Local Connectivity* (Ephys Challenge 2026 + [PRX Quantum 5, 030339](https://doi.org/10.1103/PRXQuantum.5.030339) reproduction).

**Author:** {cfg.get('author_name_en', 'Jian-Yi He')}  
**Advisor:** {cfg.get('advisor_en', 'Prof. Hsiu-Chuan Hsu')}  
**Contact:** {cfg.get('contact_email', '')}

## Overview

| Component | Directory | Description |
|-----------|-----------|-------------|
| Ephys Challenge 2026 | `ephys/` | Static GHZ chain vs entanglement swapping |
| PRX Quantum 5.030339 | `prx/` | LRCX / GHZ circuit reproduction + pytest |
| Integration | `scripts/` | Error budget, Word reports, one-click build |

## Quick start

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_graduate_package.py
python3 -m pytest prx/verify/test_equivalence.py -q
```

See [REPRODUCE.md](REPRODUCE.md). English report: `reports/Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx`
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    cfg = json.loads((ROOT / "config" / "submission.json").read_text(encoding="utf-8"))

    _copy_tree(EPHYS, OUT / "ephys", EPHYS_COPY)
    _copy_tree(PRX, OUT / "prx", PRX_COPY)

    for item in ("scripts", "config", "docs"):
        src = ROOT / item
        if src.is_dir():
            _copy_tree(src, OUT / item)

    for item in ("results", "figures", "reports"):
        src = ROOT / item
        if src.is_dir():
            _copy_tree(src, OUT / item)

    shutil.copy2(ROOT / "requirements.txt", OUT / "requirements.txt")
    shutil.copy2(ROOT / "REPRODUCE.md", OUT / "REPRODUCE.md")

    write_github_readme(cfg)

    print(f"Packaged GitHub release at: {OUT}")
    print("Next steps:")
    print(f"  1. Edit {ROOT / 'config/submission.json'} — set github_repository_url")
    print(f"  2. cd {OUT} && git init && git add . && git commit -m 'Initial release'")
    print("  3. Create GitHub repo and: git remote add origin <url> && git push -u origin main")


if __name__ == "__main__":
    main()
