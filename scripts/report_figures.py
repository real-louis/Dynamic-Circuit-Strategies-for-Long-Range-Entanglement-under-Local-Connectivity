#!/usr/bin/env python3
"""Supplementary figures and CSV for Word reports: CHSH, CI crossover, PRX verification."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import crossover_csv, ephys_root, prx_root, repo_root

ROOT = repo_root()
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"
SHOTS = 8192
Z95 = 1.96


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
            "axes.unicode_minus": False,
        }
    )


def wilson_ci(p: float, n: int, z: float = Z95) -> tuple[float, float]:
    if n <= 0:
        return p, p
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def load_crossover_rows() -> list[dict]:
    p = crossover_csv()
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_chsh_comparison(rows: list[dict], out_path: Path) -> None:
    _setup_mpl()
    ephys = ephys_root()
    sys.path.insert(0, str(ephys / "src"))
    from challenge_common import (
        build_noise_model,
        chsh_mermin_correlator,
        chsh_noisy_static_chain_shots,
        chsh_noisy_zigzag_shots,
        default_fair_comparison_noise_params,
    )
    from qiskit.quantum_info import DensityMatrix

    ideal = [r for r in rows if r.get("group") == "ideal"]
    Ls = sorted({int(r["L"]) for r in ideal})
    vals = [
        float(next(r["chsh_ideal"] for r in ideal if int(r["L"]) == L and r["strategy"] == "static_ideal"))
        for L in Ls
    ]
    fp = default_fair_comparison_noise_params()
    noise = build_noise_model(
        fp["p_1q"],
        fp["p_2q"],
        p_readout_flip=fp["p_readout_flip"],
        t1=fp["t1"],
        t2=fp["t2"],
        t_1q_gate=fp["t_1q_gate"],
        t_2q_gate=fp["t_2q_gate"],
        t_measure=fp["t_measure"],
        idle_labeled_delays=None,
    )
    L_noisy = sorted(
        {int(r["L"]) for r in rows if r.get("group") == "end_meas_A" and r.get("strategy") == "static_noisy"}
    )
    ch_st = [chsh_noisy_static_chain_shots(L, noise, SHOTS) for L in L_noisy]
    ch_zz = [chsh_noisy_zigzag_shots(L, noise, SHOTS) for L in L_noisy]

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(7.2, 6.2), sharex=True)
    ax0.plot(Ls, vals, "o-", lw=2, label=r"Ideal $|\Phi^+\rangle$ (all strategies)")
    ax0.axhline(2.0, color="#555", ls="--", label=r"Classical bound ($\leq 2$)")
    ax0.axhline(2 * math.sqrt(2), color="darkred", ls=":", label=r"Tsirelson $2\sqrt{2}$")
    ax0.set_ylabel("CHSH correlator")
    ax0.set_title("(a) Noiseless: maximal violation constant in L")
    ax0.set_ylim(1.0, 3.05)
    ax0.legend(fontsize=7.5, loc="lower right")
    ax0.grid(True, alpha=0.3)

    ax1.errorbar(L_noisy, ch_st, fmt="o-", capsize=3, label="Noisy static")
    ax1.errorbar(L_noisy, ch_zz, fmt="s-", capsize=3, color="darkgreen", label="Noisy zigzag")
    ax1.axhline(2.0, color="#555", ls="--", alpha=0.7)
    ax1.set_xlabel("L")
    ax1.set_ylabel("CHSH after noise")
    ax1.set_title(f"(b) Aer noise model (~{SHOTS} shots per point)")
    ax1.set_ylim(1.0, 3.05)
    ax1.legend(fontsize=7.5, loc="lower left")
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_crossover_with_ci(rows: list[dict], out_path: Path) -> None:
    _setup_mpl()
    end = [r for r in rows if r.get("group") == "end_meas_A"]
    swap = sorted([r for r in rows if r.get("group") == "swap_decode_B"], key=lambda x: int(x["L"]))

    def series(strategy: str) -> tuple[list[int], list[float], list[float], list[float]]:
        pts = sorted([r for r in end if r["strategy"] == strategy], key=lambda x: int(x["L"]))
        Ls, ps, lo, hi = [], [], [], []
        for r in pts:
            L = int(r["L"])
            p = float(r["p_noisy_e0e1"])
            a, b = wilson_ci(p, SHOTS)
            Ls.append(L)
            ps.append(p)
            lo.append(p - a)
            hi.append(b - p)
        return Ls, ps, lo, hi

    L_st, p_st, e0, e1 = series("static_noisy")
    L_zz, p_zz, f0, f1 = series("zigzag_noisy")
    L_sw = [int(r["L"]) for r in swap]
    p_sw = [float(r["p_noisy_e0e1"]) for r in swap]
    sw_lo, sw_hi = zip(*[wilson_ci(p, SHOTS) for p in p_sw]) if p_sw else ([], [])

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(L_st, p_st, yerr=[e0, e1], fmt="o-", capsize=3, label="Single-rail static")
    ax.errorbar(L_zz, p_zz, yerr=[f0, f1], fmt="s-", capsize=3, color="darkgreen", label="Two-rail zigzag")
    if L_sw:
        ax.errorbar(
            L_sw,
            p_sw,
            yerr=[np.array(p_sw) - np.array(sw_lo), np.array(sw_hi) - np.array(p_sw)],
            fmt="^-",
            capsize=3,
            color="crimson",
            lw=2,
            label="Entanglement swapping",
        )
    ax.axhline(1.0, color="gray", ls="--", lw=1)
    ax.set_xlabel("L (path segments)")
    ax.set_ylabel(r"$P(00)+P(11)$ on endpoints")
    ax.set_title(f"Noisy Bell diagnostic with 95% Wilson CI ({SHOTS} shots)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_ylim(0.45, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def export_prx_verification_csv_clean(out_path: Path) -> tuple[list[dict], list[dict]]:
    """Return (cnot_rows, ghz_rows) and write CSVs."""
    prx = prx_root()
    if not (prx / "verify" / "simulation.py").is_file():
        return [], []
    if str(prx) not in sys.path:
        sys.path.insert(0, str(prx))

    from qiskit.quantum_info import Statevector, partial_trace, state_fidelity

    from circuits.cnot_teleportation import build_cnot_unitary_swap
    from circuits.ghz_preparation import build_ghz_unitary
    from verify.simulation import (
        bell_fidelity_reduced_statevector,
        ghz_dynamic_statevector,
        ghz_fidelity,
        ideal_bell_statevector,
        simulate_cnot_branches,
        statevector_no_if,
    )

    cnot_rows: list[dict] = []
    for d in (0, 1, 2, 3, 6):
        uni = bell_fidelity_reduced_statevector(build_cnot_unitary_swap(d))
        if d in (0, 1, 3):
            fids = []
            for sv in simulate_cnot_branches(d, apply_corrections=True):
                traced = partial_trace(Statevector(sv), list(range(1, d + 1)))
                fids.append(float(state_fidelity(traced, ideal_bell_statevector())))
            dyn = f"{min(fids):.9f}"
        else:
            dyn = f">{uni - 1e-6:.9f} (unitary ref)"
        cnot_rows.append({"ancilla_n": str(d), "dynamic_bell_F": dyn, "unitary_swap_bell_F": f"{uni:.9f}"})

    ghz_rows: list[dict] = []
    for n in (2, 3, 4, 5, 6, 7):
        gd = ghz_fidelity(ghz_dynamic_statevector(n), n)
        gu = ghz_fidelity(statevector_no_if(build_ghz_unitary(n)), n)
        ghz_rows.append({"n_qubits": str(n), "ghz_dynamic_F": f"{gd:.9f}", "ghz_unitary_F": f"{gu:.9f}"})

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cnot_rows[0].keys()))
        w.writeheader()
        w.writerows(cnot_rows)
    ghz_path = out_path.parent / "prx_ghz_verification.csv"
    with ghz_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ghz_rows[0].keys()))
        w.writeheader()
        w.writerows(ghz_rows)
    return cnot_rows, ghz_rows


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = load_crossover_rows()
    chsh_p = FIGURES / "figure_chsh_comparison.png"
    plot_chsh_comparison(rows, chsh_p)
    print(f"Saved {chsh_p}")
    ci_p = FIGURES / "crossover_simulation_with_ci.png"
    plot_crossover_with_ci(rows, ci_p)
    print(f"Saved {ci_p}")
    cnot, ghz = export_prx_verification_csv_clean(RESULTS / "prx_cnot_verification.csv")
    print(f"PRX CNOT rows: {len(cnot)}, GHZ rows: {len(ghz)}")


if __name__ == "__main__":
    main()
