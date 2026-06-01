#!/usr/bin/env python3
"""
PRX Quantum 5.030339 error-budget analysis (task-split plots; no mixed metrics).

Outputs:
  results/error_budget_table.csv
  figures/error_budget_bell_prep.png
  figures/error_budget_lrcx.png
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import repo_root

ROOT = repo_root()
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

PAPER_MU = 3.65
PAPER_LAMBDA_IDLE = 0.03
PAPER_LAMBDA_CNOT = 0.02
PAPER_LAMBDA_MEAS = 0.03


def lambda_tot(t_idle: float, n_cnot: int, n_meas: int) -> float:
    return (
        max(0.0, t_idle) * PAPER_LAMBDA_IDLE
        + n_cnot * PAPER_LAMBDA_CNOT
        + n_meas * PAPER_LAMBDA_MEAS
    )


def process_fidelity_lower_bound(lam: float) -> float:
    return math.exp(-lam)


def unitary_ghz_idle(n: int) -> float:
    """Paper Table 2 unitary GHZ idle (CNOT-gate units); clamped at 0."""
    if n < 2:
        return 0.0
    return max(0.0, n * n / 4 - 1.5 * n + 2)


def static_ghz_budget(L: int) -> dict:
    n = L + 1
    n_cnot = 2 * L - 1
    t_idle = unitary_ghz_idle(n)
    lam = lambda_tot(t_idle, n_cnot, 0)
    return {
        "L": L,
        "task": "bell_prep",
        "strategy": "static_ghz_chain",
        "n_qubits": n,
        "N_CNOT": n_cnot,
        "N_meas": 0,
        "t_idle": round(t_idle, 4),
        "lambda_tot": round(lam, 6),
        "F_proc_lower": round(process_fidelity_lower_bound(lam), 6),
    }


def swapping_budget(L: int) -> dict:
    if L % 2 == 0 or L < 1:
        raise ValueError("swapping requires odd L >= 1")
    n = L + 1
    n_cnot = L
    n_meas = max(1, L - 1)
    t_idle = 1.0 + PAPER_MU * L / 2.0
    lam = lambda_tot(t_idle, n_cnot, n_meas)
    return {
        "L": L,
        "task": "bell_prep",
        "strategy": "entanglement_swapping",
        "n_qubits": n,
        "N_CNOT": n_cnot,
        "N_meas": n_meas,
        "t_idle": round(t_idle, 4),
        "lambda_tot": round(lam, 6),
        "F_proc_lower": round(process_fidelity_lower_bound(lam), 6),
    }


def lrcx_dynamic_budget(n_anc: int) -> dict:
    n_cnot = n_anc + 1
    n_meas = n_anc
    t_idle = 2.0 + PAPER_MU
    lam = lambda_tot(t_idle, n_cnot, n_meas)
    return {
        "L": n_anc,
        "task": "lrcx_gate",
        "strategy": "lrcx_dynamic",
        "n_qubits": n_anc + 2,
        "N_CNOT": n_cnot,
        "N_meas": n_meas,
        "t_idle": round(t_idle, 4),
        "lambda_tot": round(lam, 6),
        "F_proc_lower": round(process_fidelity_lower_bound(lam), 6),
    }


def lrcx_unitary_ic_budget(n_anc: int) -> dict:
    n_cnot = 4 * n_anc + 1
    lam = lambda_tot(0.0, n_cnot, 0)
    return {
        "L": n_anc,
        "task": "lrcx_gate",
        "strategy": "lrcx_unitary_ic",
        "n_qubits": n_anc + 2,
        "N_CNOT": n_cnot,
        "N_meas": 0,
        "t_idle": 0.0,
        "lambda_tot": round(lam, 6),
        "F_proc_lower": round(process_fidelity_lower_bound(lam), 6),
    }


def build_budget_table(L_max: int = 15) -> list[dict]:
    rows: list[dict] = []
    for L in range(1, L_max + 1):
        rows.append(static_ghz_budget(L))
        rows.append(lrcx_dynamic_budget(L))
        rows.append(lrcx_unitary_ic_budget(L))
        if L % 2 == 1:
            rows.append(swapping_budget(L))
    return rows


def _setup_mpl() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "legend.fontsize": 8,
            "figure.dpi": 120,
            "savefig.dpi": 175,
        }
    )


def plot_bell_prep_budget(L_max: int = 15) -> Path:
    _setup_mpl()
    Ls = list(range(1, L_max + 1))
    Ls_odd = [L for L in Ls if L % 2 == 1]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.semilogy(Ls, [static_ghz_budget(L)["F_proc_lower"] for L in Ls], "o-", label="Static GHZ (Strategy A)")
    ax.semilogy(
        Ls_odd,
        [swapping_budget(L)["F_proc_lower"] for L in Ls_odd],
        "d-",
        color="crimson",
        label="Entanglement swapping (Strategy B)",
    )
    ax.set_xlabel("L (Bell-prep path segments)")
    ax.set_ylabel(r"$e^{-\lambda_{\mathrm{tot}}}$ (lower bound)")
    ax.set_title("Bell-state preparation — paper error budget (Appendix B.2 params)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_ylim(1e-3, 1.05)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    path = FIGURES / "error_budget_bell_prep.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_lrcx_budget(L_max: int = 15) -> Path:
    _setup_mpl()
    Ls = list(range(0, L_max + 1))
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.semilogy(Ls, [lrcx_dynamic_budget(L)["F_proc_lower"] for L in Ls], "s-", label="LRCX dynamic (Fig. 1a right)")
    ax.semilogy(Ls, [lrcx_unitary_ic_budget(L)["F_proc_lower"] for L in Ls], "^-", label="LRCX unitary Ic (Fig. 1a middle)")
    ax.axhline(0.4, color="gray", ls=":", lw=1, label="Paper gate-F asymptote ~0.4")
    ax.set_xlabel("n (ancilla qubits between control and target)")
    ax.set_ylabel(r"$e^{-\lambda_{\mathrm{tot}}}$ (lower bound)")
    ax.set_title("Long-range CNOT teleportation — paper error budget")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_ylim(1e-3, 1.05)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    path = FIGURES / "error_budget_lrcx.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    rows = build_budget_table()
    csv_path = RESULTS / "error_budget_table.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {csv_path}")
    print(f"Saved {plot_bell_prep_budget()}")
    print(f"Saved {plot_lrcx_budget()}")


if __name__ == "__main__":
    main()
