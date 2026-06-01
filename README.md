# Dynamic Circuit Strategies for Long-Range Entanglement under Local Connectivity

[![Reproducible](https://img.shields.io/badge/reproducible-yes-green)](REPRODUCE.md)

Research code for *Dynamic Circuit Strategies for Long-Range Entanglement under Local Connectivity* (Ephys Challenge 2026 + [PRX Quantum 5, 030339](https://doi.org/10.1103/PRXQuantum.5.030339) reproduction).

**Author:** Jian-Yi He  
**Advisor:** Prof. Hsiu-Chuan Hsu  
**Contact:** louse2121@gmail.com

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
