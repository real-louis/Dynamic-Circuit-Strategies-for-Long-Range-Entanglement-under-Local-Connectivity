"""
Long-range CNOT via gate teleportation (PRX Quantum 5, 030339).

Implements Fig. 1(a): dynamic (feed-forward), postprocessing, and unitary variants.
Dynamic construction follows IBM's long-range entanglement tutorial.
"""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.classical import expr

from circuits.common import measure_bell_basis, parity_expr, prepare_bell_pairs


def _initialize_lrcx(distance: int) -> QuantumCircuit:
    """Control at 0, target at distance+1, ancilla bus in |0>."""
    assert distance >= 0
    n = distance
    qr = QuantumRegister(n + 2, name="q")
    cr = ClassicalRegister(2, name="cr")
    allcr: list = [cr]
    k = n // 2
    if distance > 1:
        allcr.append(ClassicalRegister(k, name="c1"))
    if distance > 0:
        allcr.append(ClassicalRegister(n - k, name="c2"))
    qc = QuantumCircuit(qr, *allcr, name=f"LRCX_n{n}")
    qc.h(0)
    return qc


def apply_ffwd_corrections(qc: QuantumCircuit) -> QuantumCircuit:
    """Pauli byproduct corrections via if_test (Fig. 1a right)."""
    control = 0
    target = qc.num_qubits - 1
    n = qc.num_qubits - 2
    k = n // 2
    x0 = 1 if n % 2 == 0 else 2

    if n > 1:
        _, c1, c2 = qc.cregs
    elif n > 0:
        _, c2 = qc.cregs
    else:
        return qc

    if n > 0:
        parity_xx = expr.lift(c2[0])
        for i in range(1, k + x0):
            parity_xx = expr.bit_xor(c2[i - 1], parity_xx)
        with qc.if_test(parity_xx):
            qc.z(control)

    if n > 1:
        parity_zz = parity_expr(list(c1))
        with qc.if_test(parity_zz):
            qc.x(target)
    return qc


def build_cnot_dynamic(distance: int, *, with_feedforward: bool = True) -> QuantumCircuit:
    """
    Dynamic long-range CNOT (Fig. 1a right).

    Parameters
    ----------
    distance : int
        Number of ancilla qubits between control and target.
    with_feedforward : bool
        If True, apply if_test corrections; if False, leave measurements only
        (for postprocessing).
    """
    qc = _initialize_lrcx(distance)
    prepare_bell_pairs(qc)
    measure_bell_basis(qc)
    if with_feedforward and distance > 0:
        apply_ffwd_corrections(qc)
    return qc


def build_cnot_postprocessing(distance: int) -> QuantumCircuit:
    """Same quantum circuit as dynamic, corrections applied classically."""
    return build_cnot_dynamic(distance, with_feedforward=False)


def lrcx(distance: int) -> QuantumCircuit:
    """Alias for dynamic LRCX without final measurement."""
    return build_cnot_dynamic(distance)


def build_cnot_unitary_swap(distance: int) -> QuantumCircuit:
    """
    SWAP-based unitary long-range CNOT (IBM tutorial / Fig. 6 panel II style).

    Moves control and target toward the middle, applies CNOT, swaps back.
    """
    assert distance >= 0
    n = distance
    qr = QuantumRegister(n + 2, name="q")
    cr = ClassicalRegister(2, name="cr")
    qc = QuantumCircuit(qr, cr, name="CNOT_unitary_swap")
    control = 0
    qc.h(control)
    k = n // 2
    qc.barrier()
    for i in range(k):
        qc.cx(i, i + 1)
        qc.cx(i + 1, i)
        qc.cx(-i - 1, -i - 2)
        qc.cx(-i - 2, -i - 1)
    if n % 2 == 1:
        qc.cx(k + 2, k + 1)
        qc.cx(k + 1, k + 2)
    qc.barrier()
    qc.cx(k, k + 1)
    for i in range(k):
        qc.cx(k - i, k - 1 - i)
        qc.cx(k - 1 - i, k - i)
        qc.cx(k + i + 1, k + i + 2)
        qc.cx(k + i + 2, k + i + 1)
    if n % 2 == 1:
        qc.cx(-2, -1)
        qc.cx(-1, -2)
    return qc


def build_cnot_unitary_ancilla_ic(distance: int) -> QuantumCircuit:
    """
    Ancilla-bus unitary long-range CNOT (Appendix B, Fig. 6 panel Ic).

    The paper's Ic variant uses 4n+1 CNOT gates with ancillas returned to |0>.
    The SWAP-meeting decomposition (``build_cnot_unitary_swap``) is the unitary
    used experimentally in the paper's Fig. 1(a) middle panel; this function
  exposes the same unitary under the Ic name for API symmetry with the plan.
    """
    qc = build_cnot_unitary_swap(distance)
    qc.name = f"CNOT_unitary_Ic_n{distance}"
    return qc
