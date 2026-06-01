#!/usr/bin/env python3
"""
Demo: PRX Quantum 5.030339 dynamic-circuit reproduction.

Run from the project root:
    python3 demo.py
    python3 demo.py --distance 6 --ghz-n 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from circuits.cnot_teleportation import (
    build_cnot_dynamic,
    build_cnot_postprocessing,
    build_cnot_unitary_swap,
)
from circuits.ghz_preparation import (
    build_ghz_dynamic,
    build_ghz_unitary,
    count_ghz_dynamic_resources,
)
from verify.simulation import (
    bell_fidelity_reduced_statevector,
    ghz_dynamic_statevector,
    ghz_fidelity,
    simulate_cnot_branches,
    statevector_no_if,
)


def _header(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}\n{title}\n{line}")


def _gate_counts(qc) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in qc.data:
        name = item.operation.name
        counts[name] = counts.get(name, 0) + 1
    return counts


def _print_circuit(qc, *, fold: int = 80) -> None:
    print(qc.draw(output="text", fold=fold, idle_wires=False))


def demo_cnot(distances: list[int], *, show_circuits: bool) -> None:
    _header("Part 1: Long-range CNOT (Fig. 1a)")

    for d in distances:
        print(f"\n--- distance = {d} (ancillas between control & target) ---")
        qc_dyn = build_cnot_dynamic(d)
        qc_uni = build_cnot_unitary_swap(d)
        qc_post = build_cnot_postprocessing(d)

        for label, qc in [
            ("dynamic (if_test)", qc_dyn),
            ("postprocessing (measure only)", qc_post),
            ("unitary SWAP baseline", qc_uni),
        ]:
            counts = _gate_counts(qc)
            cx = counts.get("cx", 0)
            meas = counts.get("measure", 0)
            ff = counts.get("if_else", 0) + counts.get("if_test", 0)
            print(f"  [{label}] qubits={qc.num_qubits}, CNOT={cx}, measure={meas}, feed-forward={ff}")

        f_uni = bell_fidelity_reduced_statevector(qc_uni)
        print(f"  Unitary SWAP → Bell fidelity (q0, q{d+1}) = {f_uni:.6f}")

        if d in (0, 1, 3):
            branches = simulate_cnot_branches(d, apply_corrections=True)
            f_min = min(
                _bell_fidelity_from_state(sv, d + 2) for sv in branches
            )
            print(
                f"  Dynamic/postprocessing (all meas. outcomes + corrections): "
                f"min branch fidelity = {f_min:.6f} ({len(branches)} branches)"
            )

        if show_circuits and d <= 2:
            print("\n  Dynamic circuit:")
            _print_circuit(qc_dyn, fold=-1)


def _bell_fidelity_from_state(sv, n_qubits: int) -> float:
    from qiskit.quantum_info import partial_trace, state_fidelity
    from verify.simulation import ideal_bell_statevector

    traced = partial_trace(sv, list(range(1, n_qubits - 1)))
    return float(state_fidelity(traced, ideal_bell_statevector()))


def demo_ghz(sizes: list[int], *, show_circuits: bool) -> None:
    _header("Part 2: GHZ state preparation (Fig. 2b)")

    for n in sizes:
        print(f"\n--- n = {n} qubits ---")
        qc_u = build_ghz_unitary(n)
        qc_d = build_ghz_dynamic(n)
        res = count_ghz_dynamic_resources(n)

        print(f"  Unitary:  CNOT={n - 1} (linear chain), depth O(n)")
        print(f"  Dynamic:  CNOT={res['cnot']}, measure={res['measure']}")

        f_u = ghz_fidelity(statevector_no_if(qc_u), n)
        f_d = ghz_fidelity(ghz_dynamic_statevector(n), n)
        print(f"  |<GHZ|ψ_unitary>|² = {f_u:.6f}")
        print(f"  |<GHZ|ψ_dynamic>|²  = {f_d:.6f}")

        if show_circuits and n <= 4:
            print("\n  Dynamic / shallow circuit:")
            _print_circuit(qc_d, fold=-1)


def demo_summary() -> None:
    _header("Summary")
    print(
        """
This project reproduces circuit *derivations* from:
  Bäumer et al., PRX Quantum 5, 030339 (2024)
  https://doi.org/10.1103/PRXQuantum.5.030339

Fidelity ≈ 1.0 means the constructed circuit prepares the expected
entangled state in noiseless simulation.

Full automated checks:
  python3 -m pytest verify/test_equivalence.py -v
"""
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--distance",
        type=int,
        nargs="+",
        default=[1, 2, 3],
        help="CNOT ancilla distances to demo (default: 1 2 3)",
    )
    parser.add_argument(
        "--ghz-n",
        type=int,
        nargs="+",
        default=[2, 4, 6],
        help="GHZ qubit counts to demo (default: 2 4 6)",
    )
    parser.add_argument(
        "--no-draw",
        action="store_true",
        help="Skip printing text circuit diagrams",
    )
    args = parser.parse_args()

    print("PRX Quantum 5.030339 — Dynamic circuit reproduction demo")
    print(f"Project root: {ROOT}")

    demo_cnot(args.distance, show_circuits=not args.no_draw)
    demo_ghz(args.ghz_n, show_circuits=not args.no_draw)
    demo_summary()


if __name__ == "__main__":
    main()
