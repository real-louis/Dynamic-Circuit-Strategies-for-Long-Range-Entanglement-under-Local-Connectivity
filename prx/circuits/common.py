"""Shared helpers for parity and Bell-state preparation."""

from __future__ import annotations

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.classical import expr


def check_even(n: int) -> int:
    """Return 1 if n is even, else 2 (IBM tutorial convention)."""
    return 1 if n % 2 == 0 else 2


def parity_expr(bits: list) -> expr.Expr:
    """XOR parity of classical bits as a Qiskit classical expression."""
    if not bits:
        raise ValueError("need at least one classical bit for parity")
    result = expr.lift(bits[0])
    for bit in bits[1:]:
        result = expr.bit_xor(bit, result)
    return result


def prepare_bell_pairs(qc: QuantumCircuit, add_barriers: bool = False) -> QuantumCircuit:
    """Create Bell pairs along the ancilla bus (PRX Quantum Fig. 1a / IBM tutorial)."""
    n = qc.num_qubits - 2
    k = n // 2
    if add_barriers:
        qc.barrier()
    x0 = check_even(n)
    if n % 2 != 0:
        qc.cx(0, 1)
    for i in range(k):
        qc.h(x0 + 2 * i)
        qc.cx(x0 + 2 * i, x0 + 2 * i + 1)
    return qc


def measure_bell_basis(qc: QuantumCircuit, add_barriers: bool = False) -> QuantumCircuit:
    """Bell-basis measurements for gate teleportation; stores outcomes in c1, c2."""
    n = qc.num_qubits - 2
    k = n // 2
    if n > 1:
        _, c1, c2 = qc.cregs
    elif n > 0:
        _, c2 = qc.cregs
    else:
        return qc

    x0 = 1 if n % 2 == 0 else 2
    for i in range(k + 1):
        qc.cx(x0 - 1 + 2 * i, x0 + 2 * i)

    for i in range(1, k + x0):
        qc.h(2 * i + 1 - x0)

    if add_barriers:
        qc.barrier()

    if n > 1:
        for i in range(k):
            qc.measure(2 * i + x0, c1[i])
    if n > 0:
        for i in range(1, k + x0):
            qc.measure(2 * i + 1 - x0, c2[i - 1])
    return qc


def classical_pauli_corrections(
    qc: QuantumCircuit, c1_bits: list, c2_bits: list
) -> tuple[bool, bool]:
    """Return (apply_z_on_control, apply_x_on_target) from measurement parities."""
    n = qc.num_qubits - 2
    k = n // 2
    x0 = check_even(n)
    apply_z = False
    if n > 0 and c2_bits:
        apply_z = sum(int(b) for b in c2_bits) % 2 == 1
    apply_x = False
    if n > 1 and c1_bits:
        apply_x = sum(int(b) for b in c1_bits) % 2 == 1
    return apply_z, apply_x
