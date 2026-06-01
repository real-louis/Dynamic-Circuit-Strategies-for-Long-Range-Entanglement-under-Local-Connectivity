"""
糾纏交換（Entanglement Swapping）示範 — 與靜態鏈式策略對照。

含雜訊與靜態鏈的「相同 noise」比較請執行：python compare_models.py
"""

from __future__ import annotations

from qiskit import transpile
from qiskit_aer import AerSimulator

from challenge_common import (
    generate_swapping_circuit,
    postprocess_swapping_shot_general,
    swapping_ideal_end_fidelity,
)


def main() -> None:
    L = 3
    print(f"--- L={L}（N={L+1}）理想兩端 |Φ+⟩ 分量 (P00+P11) ---")
    print(f"Statevector 塌縮驗證: {swapping_ideal_end_fidelity(L):.6f}\n")

    print("--- 動態電路（含 if_test 前饋，供圖示與說明）---")
    qc_ff = generate_swapping_circuit(L, apply_feedforward=True)
    print(qc_ff.draw(output="text"))

    print("\n--- 無雜訊：Aer + 古典讀取後處理（略過硬體 if 的數值不穩）---")
    qc = generate_swapping_circuit(L, apply_feedforward=False)
    sim = AerSimulator()
    tqc = transpile(qc, sim, optimization_level=0)
    mem = sim.run(tqc, shots=1024, memory=True).result().get_memory()
    ok = 0
    for shot in mem:
        c0, c1 = postprocess_swapping_shot_general(shot, L)
        if c0 == c1:
            ok += 1
    print(f"P(00)+P(11) on (e0,e1) after readout decode ≈ {ok / len(mem):.4f}")


if __name__ == "__main__":
    main()

