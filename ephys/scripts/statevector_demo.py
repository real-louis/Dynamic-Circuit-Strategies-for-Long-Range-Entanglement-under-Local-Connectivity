from __future__ import annotations

from qiskit.quantum_info import Statevector

from challenge_common import generate_ladder_bell_circuit


def main() -> None:
    # L：e0 到 e1 沿單腳鏈的段數；位元數 N = L + 1。可改 L 驗證可擴充性。
    L_value = 5
    target = "Phi+"
    circuit = generate_ladder_bell_circuit(L_value, target_state=target)

    print(f"正在製備長度 L={L_value} 的 {target} 態（e0=q0, e1=q{L_value}）...")
    print(circuit.draw(output="text"))

    state = Statevector.from_instruction(circuit)
    probs = state.probabilities_dict()

    print("\n--- 測量結果驗證（全體 Z 基，理想）---")
    print(f"目標貝爾態: {target}")
    for outcome, prob in probs.items():
        if prob > 0.01:
            print(f"測量到 |{outcome}> 的機率: {prob:.4f}")


if __name__ == "__main__":
    main()

