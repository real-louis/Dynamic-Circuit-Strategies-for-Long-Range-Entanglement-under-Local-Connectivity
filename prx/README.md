# PRX Quantum 5.030339 — Circuit Reproduction

Reproduction of circuit derivations from [Efficient Long-Range Entanglement Using Dynamic Circuits](https://doi.org/10.1103/PRXQuantum.5.030339) (arXiv [2308.13065](https://arxiv.org/abs/2308.13065)).

## Scope

This project implements **quantum circuits only** (no IBM hardware, no error-budget plots):

| Paper reference | Module | Function |
|-----------------|--------|----------|
| Fig. 1(a) right | `circuits/cnot_teleportation.py` | `build_cnot_dynamic()` |
| Fig. 1(a) middle | `circuits/cnot_teleportation.py` | `build_cnot_unitary_swap()`, `build_cnot_unitary_ancilla_ic()` |
| Postprocessing | `circuits/cnot_teleportation.py` | `build_cnot_postprocessing()` |
| Fig. 2(b) left | `circuits/ghz_preparation.py` | `build_ghz_unitary()` |
| Fig. 2(b) right | `circuits/ghz_preparation.py` | `build_ghz_dynamic()` |

Dynamic CNOT construction follows the IBM tutorial [Long-range entanglement with dynamic circuits](https://quantum.cloud.ibm.com/docs/en/tutorials/long-range-entanglement).

## Setup

```bash
cd "/Users/louis/Desktop/量子運算專題/2026:5:18"
python3 -m pip install -r requirements.txt
```

Note: creating a virtual environment inside this folder may fail on macOS because the path contains `:`. Install packages with `pip install -r requirements.txt` instead.

## Run tests

```bash
python3 -m pytest verify/test_equivalence.py -v
```

Tests use noiseless statevector simulation:

- Long-range CNOT: Bell fidelity on control/target qubits (0 and `n+1`) after tracing ancillas.
- GHZ: overlap with `( |0…0⟩ + |1…1⟩ ) / √2`.
- Even-distance dynamic CNOT (`distance ∈ {2,6}`): circuit structure + unitary SWAP reference.

## Example

```python
from circuits.cnot_teleportation import build_cnot_dynamic, build_cnot_unitary_swap
from circuits.ghz_preparation import build_ghz_unitary, build_ghz_dynamic

qc_dyn = build_cnot_dynamic(distance=6)       # Fig. 1a, with if_test feed-forward
qc_uni = build_cnot_unitary_swap(distance=6)  # Fig. 1a unitary baseline

ghz_u = build_ghz_unitary(6)
ghz_d = build_ghz_dynamic(6)                  # shallow schedule for even n ∈ {2,4,6}
```

Draw a circuit:

```python
print(build_cnot_dynamic(3).draw(output="text"))
```

## File layout

```
circuits/
  common.py              # Bell pairs, Bell measurement, parity helpers
  cnot_teleportation.py  # LRCX dynamic / postprocessing / unitary
  ghz_preparation.py     # GHZ unitary + shallow dynamic schedules
verify/
  simulation.py          # Statevector fidelity helpers
  test_equivalence.py    # Pytest suite
requirements.txt
```

## Notes

- **`build_cnot_unitary_ancilla_ic`**: same unitary as `build_cnot_unitary_swap` (paper Fig. 1a middle / Appendix B SWAP-meeting decomposition used in experiments).
- **GHZ dynamic (even `n`)**: constant-depth gate schedules verified for `n ∈ {2,4,6}`; other sizes use the linear unitary chain. Full mid-circuit measurement layout from Fig. 2b / Fig. 5 can be extended on top of the shallow layers.
- **Deferred-measurement simulation** for CNOT is validated for odd ancilla counts (`distance ∈ {1,3}`); even distances rely on structure tests plus the SWAP baseline.
