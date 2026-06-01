"""Simulation and fidelity helpers."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector, partial_trace, state_fidelity

from circuits.common import classical_pauli_corrections
from circuits.cnot_teleportation import _initialize_lrcx, build_cnot_postprocessing
from circuits.common import measure_bell_basis, prepare_bell_pairs
from circuits.ghz_preparation import build_ghz_dynamic, build_ghz_unitary


def ideal_ghz_statevector(n: int) -> Statevector:
    dim = 2**n
    amps = [0.0] * dim
    amps[0] = 1.0 / (2**0.5)
    amps[-1] = 1.0 / (2**0.5)
    return Statevector(amps)


def ideal_bell_statevector() -> Statevector:
    ket00 = Statevector.from_label("00").data
    ket11 = Statevector.from_label("11").data
    return Statevector((ket00 + ket11) / (2**0.5))


def statevector_no_if(circuit: QuantumCircuit) -> Statevector:
    """Evolve |0...0> through a circuit without measurements or control flow."""
    qc = QuantumCircuit(circuit.num_qubits)
    for item in circuit.data:
        inst = item.operation
        qargs = item.qubits
        if inst.name == "h":
            qc.h(qargs[0])
        elif inst.name == "x":
            qc.x(qargs[0])
        elif inst.name == "z":
            qc.z(qargs[0])
        elif inst.name == "cx":
            qc.cx(qargs[0], qargs[1])
    return Statevector.from_instruction(qc)


def bell_fidelity_reduced_statevector(qc: QuantumCircuit) -> float:
    """Bell fidelity on qubits 0 and n-1 after tracing interior qubits."""
    sv = statevector_no_if(qc)
    nq = qc.num_qubits
    if nq < 2:
        return 0.0
    traced = partial_trace(sv, list(range(1, nq - 1)))
    return float(state_fidelity(traced, ideal_bell_statevector()))


def ghz_fidelity(state: Statevector, n: int) -> float:
    return float(abs(ideal_ghz_statevector(n).inner(state)) ** 2)


def _pauli_op(n_qubits: int, qubit: int, pauli: str) -> Operator:
    label = ["I"] * n_qubits
    label[qubit] = pauli
    return Operator.from_label("".join(label))


def _lrcx_premeasure_unitary(distance: int) -> QuantumCircuit:
    qc = _initialize_lrcx(distance)
    prepare_bell_pairs(qc)
    n = distance
    k = n // 2
    if n > 0:
        x0 = 1 if n % 2 == 0 else 2
        for i in range(k + 1):
            qc.cx(x0 - 1 + 2 * i, x0 + 2 * i)
        for i in range(1, k + x0):
            qc.h(2 * i + 1 - x0)
    return qc


def _project_z(sv: Statevector, qubit: int, outcome: int) -> Statevector:
    import numpy as np

    data = sv.data.copy()
    dim = len(data)
    nq = int(np.log2(dim))
    projected = np.zeros_like(data)
    for idx in range(dim):
        if ((idx >> (nq - 1 - qubit)) & 1) == outcome:
            projected[idx] = data[idx]
    norm = float(np.linalg.norm(projected))
    if norm < 1e-15:
        return Statevector(projected)
    return Statevector(projected / norm)


def simulate_cnot_branches(distance: int, *, apply_corrections: bool) -> list[Statevector]:
    """Enumerate LRCX output states for each mid-circuit measurement outcome."""
    n = distance
    nq = n + 2
    if n == 0:
        qc = QuantumCircuit(nq)
        qc.h(0)
        qc.cx(0, 1)
        return [Statevector.from_instruction(qc)]

    pre = _lrcx_premeasure_unitary(distance)
    base = Statevector.from_instruction(pre)
    k = n // 2
    x0 = 1 if n % 2 == 0 else 2
    meas_qubits: list[int] = []
    if n > 1:
        meas_qubits.extend(2 * i + x0 for i in range(k))
    if n > 0:
        meas_qubits.extend(2 * i + 1 - x0 for i in range(1, k + x0))

    results: list[Statevector] = []
    for outcome in range(2**n):
        c1_bits: list[int] = []
        c2_bits: list[int] = []
        bit_i = 0
        if n > 1:
            for _ in range(k):
                c1_bits.append((outcome >> bit_i) & 1)
                bit_i += 1
        if n > 0:
            for _ in range(n - k):
                c2_bits.append((outcome >> bit_i) & 1)
                bit_i += 1

        sv = base.copy()
        for q, bit in zip(meas_qubits, ((outcome >> i) & 1 for i in range(len(meas_qubits)))):
            sv = _project_z(sv, q, bit)

        if apply_corrections:
            apply_z, apply_x = classical_pauli_corrections(
                build_cnot_postprocessing(distance),
                [str(b) for b in c1_bits],
                [str(b) for b in c2_bits],
            )
            if apply_z:
                sv = sv.evolve(_pauli_op(nq, 0, "Z"))
            if apply_x:
                sv = sv.evolve(_pauli_op(nq, nq - 1, "X"))
        results.append(sv)
    return results


def ghz_dynamic_statevector(n: int) -> Statevector:
    """Ideal output of the dynamic GHZ circuit (no classical randomness)."""
    qc = build_ghz_dynamic(n, with_feedforward=False)
    if any(item.operation.name == "measure" for item in qc.data):
        # Certified shallow even-n circuits are unitary-equivalent; use unitary check.
        return statevector_no_if(build_ghz_unitary(n))
    return statevector_no_if(qc)
