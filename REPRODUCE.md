# Reproducibility

This repository bundles the Ephys Challenge 2026 simulations and PRX Quantum 5.030339 circuit verification in a single monorepo layout.

## Environment

```bash
python3 -m pip install -r requirements.txt
```

Requires Python 3.10+ with `numpy`, `matplotlib`, `qiskit`, `qiskit-aer`, and `pytest`.

## One-click reproduction (recommended)

```bash
python3 scripts/reproduce.py
```

This runs, in order:

1. `ephys/competition_suite.py` — crossover CSV and resource plots
2. `pytest prx/verify/test_equivalence.py` — PRX circuit equivalence tests
3. `scripts/error_budget_analysis.py` — error-budget tables and plots
4. `scripts/report_figures.py` — CHSH comparison, Wilson 95% CI crossover, PRX verification CSVs

## Step-by-step

### Step 1 — Ephys competition data

```bash
cd ephys
python3 competition_suite.py
```

Expected outputs (copied to repo root by `reproduce.py`):

- `results/crossover_and_resources.csv`
- `figures/crossover_p_success.png`
- `figures/resources_cx_vs_L.png`

### Step 2 — PRX Quantum circuit tests

```bash
python3 -m pytest prx/verify/test_equivalence.py -v
```

### Step 3 — Error budget and supplementary figures

```bash
python3 scripts/error_budget_analysis.py
python3 scripts/report_figures.py
```

Expected outputs:

- `results/error_budget_table.csv`
- `results/prx_cnot_verification.csv`, `results/prx_ghz_verification.csv`
- `figures/error_budget_bell_prep.png`, `figures/error_budget_lrcx.png`
- `figures/crossover_simulation_with_ci.png`, `figures/figure_chsh_comparison.png`

## English report

The written report is pre-built at:

`reports/Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx`

It embeds the figures above; regenerate figures first if you need an updated report.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Crossover plot panel (b) empty | Run Step 1 first |
| pytest failures | Use `qiskit>=2.0` (see `prx/requirements.txt`) |
| Import errors in scripts | Run commands from the repository root |
