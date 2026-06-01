"""
多策略、同一雜訊模型下比較（`default_fair_comparison_noise_params` + `fair_idle_delay_profile`）：
  - 單／雙位元 depolarizing + T1/T2 + readout + 糾纏交換專用之具名 idle delay
  - 組 A：末態僅 Z 量測兩端診斷 P(00)+P(11) — 單腳靜態、雙腳之字形靜態（寬度不同，可比指標相同）
  - 組 B：糾纏交換 L=3 + 古典解碼（memory；與組 A 同一 NoiseModel）

入口：`python compare_models.py`
"""

from __future__ import annotations

from challenge_common import (
    build_noise_model,
    default_fair_comparison_noise_params,
    fair_idle_delay_profile,
    generate_ladder_bell_circuit,
    generate_zigzag_ladder_bell_circuit,
    run_phi_plus_z_diagnostic_noisy,
    run_swapping_phi_plus_diagnostic_noisy,
    swapping_ideal_end_fidelity,
    zigzag_ladder_cnot_count,
)


def main():
    shots = 8192
    fp = default_fair_comparison_noise_params()
    p_1q = fp["p_1q"]
    p_2q = fp["p_2q"]
    lat = float(fp["classical_latency_ns"])
    idle_prof = fair_idle_delay_profile(fp)
    noise = build_noise_model(
        p_1q,
        p_2q,
        p_readout_flip=fp["p_readout_flip"],
        t1=fp["t1"],
        t2=fp["t2"],
        t_1q_gate=fp["t_1q_gate"],
        t_2q_gate=fp["t_2q_gate"],
        t_measure=fp["t_measure"],
        idle_labeled_delays=idle_prof,
    )
    bsm_idle = (
        float(fp["t_2q_gate"]),
        float(fp["t_1q_gate"]),
        float(fp["t_measure"]),
    )

    print("=== 共同條件（所有策略同一 NoiseModel）===")
    print(
        f"depolarizing p(1q)={p_1q}, p(2q)={p_2q}; readout p={fp['p_readout_flip']}; "
        f"T1={fp['t1']:.0f} ns, T2={fp['t2']:.0f} ns; "
        f"t_H={fp['t_1q_gate']} ns, t_CX={fp['t_2q_gate']} ns, t_meas={fp['t_measure']} ns"
    )
    print(
        f"糾纏交換 BSM 並行 idle={bsm_idle} ns；端點等待={lat} ns；shots={shots}\n"
        "指標：P(00)+P(11) on (e0,e1)，e0=q0、e1=qL（上軌兩端）\n"
    )

    print("--- 組 A：末態全線 Z 量測，marginal 兩端（單腳 vs 雙腳之字形）---")
    for L in (1, 3, 5):
        p_sr = run_phi_plus_z_diagnostic_noisy(
            generate_ladder_bell_circuit(L, "Phi+"),
            endpoint_qubits=(0, L),
            noise_model=noise,
            shots=shots,
        )
        cx_sr = 2 * L - 1
        p_zz = run_phi_plus_z_diagnostic_noisy(
            generate_zigzag_ladder_bell_circuit(L, "Phi+"),
            endpoint_qubits=(0, L),
            noise_model=noise,
            shots=shots,
        )
        cx_zz = zigzag_ladder_cnot_count(L)
        n_zz = 2 * (L + 1)
        print(
            f"  L={L}  [單腳靜態] N={L+1} CX={cx_sr}  P≈{p_sr:.4f}  |  "
            f"[雙腳之字形] N={n_zz} CX={cx_zz}  P≈{p_zz:.4f}"
        )

    print("\n--- 組 B：糾纏交換（L=3，古典讀取解碼；與組 A 相同雜訊）---")
    p_swap = run_swapping_phi_plus_diagnostic_noisy(
        3,
        noise,
        shots,
        classical_latency_before_endpoint_meas_ns=lat,
        bsm_parallel_idle_ns=bsm_idle,
    )
    print(f"  L=3  [糾纏交換] N=4 CX=3  P≈{p_swap:.4f}")

    print("\n=== 糾纏交換理想驗證（無雜訊 Statevector）===")
    for L in (1, 3, 5):
        print(f"  L={L}: swapping_ideal P00+P11 = {swapping_ideal_end_fidelity(L):.6f}")
    print("\n完整 CSV／圖表：python competition_suite.py")
