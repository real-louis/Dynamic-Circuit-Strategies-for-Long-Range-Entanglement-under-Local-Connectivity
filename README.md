# Dynamic Circuit Strategies for Long-Range Entanglement under Local Connectivity

[![Reproducible](https://img.shields.io/badge/reproducible-yes-green)](REPRODUCE.md)

Research code and English report for *Dynamic Circuit Strategies for Long-Range Entanglement under Local Connectivity*
(Ephys Challenge 2026 + [PRX Quantum 5, 030339](https://doi.org/10.1103/PRXQuantum.5.030339) reproduction).

**Author:** HE, CHIEN-YI  
**Advisor:** Prof. Hsiu-Chuan Hsu  
**Contact:** louse2121@gmail.com

## Contents

| Path | Description |
|------|-------------|
| `reports/Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx` | External English written report |
| `ephys/` | Ephys Challenge: static GHZ chain vs entanglement swapping |
| `prx/` | PRX Quantum LRCX / GHZ circuit reproduction + pytest |
| `scripts/` | Error budget, supplementary figures, one-click `reproduce.py` |
| `results/`, `figures/` | Precomputed outputs (regenerable via `reproduce.py`) |

## Quick start

```bash
python3 -m pip install -r requirements.txt
python3 scripts/reproduce.py
python3 -m pytest prx/verify/test_equivalence.py -q
```

See [REPRODUCE.md](REPRODUCE.md) for step-by-step instructions.
