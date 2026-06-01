"""
Ephys 2026 競賽一鍵產出：多策略資源、CHSH、同雜訊下 P(00)+P(11) 與圖表。

策略分組（同一 NoiseModel、同一端點診斷指標）：
  - 組 A：單腳靜態、雙腳之字形靜態 — 末態全線 Z 量測，marginal (e0,e1)。
  - 組 B：糾纏交換 L=3 — memory + 古典解碼（指標與組 A 對齊為兩端 Z 同位元機率）。

入口：`python competition_suite.py`
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from challenge_common import (
    DYNAMIC_CIRCUIT_TRADEOFF_NOTE,
    LADDER_TOPOLOGY_NOTE,
    build_noise_model,
    chsh_mermin_correlator,
    circuit_metrics,
    default_fair_comparison_noise_params,
    entanglement_swap_cnot_count,
    fair_idle_delay_profile,
    generate_ladder_bell_circuit,
    generate_swapping_circuit,
    generate_zigzag_ladder_bell_circuit,
    reduced_two_qubit_dm_static,
    reduced_two_qubit_dm_swapping_ideal,
    reduced_two_qubit_dm_zigzag_ideal,
    run_phi_plus_z_diagnostic_noisy,
    run_swapping_phi_plus_diagnostic_noisy,
    static_chain_cnot_count,
    swapping_ideal_end_fidelity,
    verify_resource_formulas,
    zigzag_ladder_cnot_count,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"


def main():
    shots = 8192
    fp = default_fair_comparison_noise_params()
    lat = float(fp["classical_latency_ns"])
    bsm_idle = (float(fp["t_2q_gate"]), float(fp["t_1q_gate"]), float(fp["t_measure"]))
    noise = build_noise_model(
        fp["p_1q"],
        fp["p_2q"],
        p_readout_flip=fp["p_readout_flip"],
        t1=fp["t1"],
        t2=fp["t2"],
        t_1q_gate=fp["t_1q_gate"],
        t_2q_gate=fp["t_2q_gate"],
        t_measure=fp["t_measure"],
        idle_labeled_delays=fair_idle_delay_profile(fp),
    )
    # 理想 CHSH 可掃較大 L；含噪蒙地卡羅對雙腳之字形在 L=9 時寬 20Q 明顯變慢，故含噪預設不掃 L=9。
    L_list_ideal = [1, 3, 5, 7, 9]
    L_list_noisy = [1, 3, 5, 7]

    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)

    formula_check = verify_resource_formulas(25)
    if formula_check:
        raise RuntimeError("CNOT 封閉式與電路計數不一致: " + "; ".join(formula_check))

    csv_path = RESULTS / "crossover_and_resources.csv"
    rows = []

    print(
        "=== 多策略；雜訊與 compare_models 一致 "
        f"(depol + T1/T2 + readout + swap idle + 端點 {lat} ns) ===\n"
    )
    print(LADDER_TOPOLOGY_NOTE.strip() + "\n")

    print("--- 理想：兩端 CHSH（|Φ+⟩ 時 ≈ 2√2）---")
    for L in L_list_ideal:
        ch_s = chsh_mermin_correlator(reduced_two_qubit_dm_static(L))
        ch_w = chsh_mermin_correlator(reduced_two_qubit_dm_swapping_ideal(L))
        ch_z = chsh_mermin_correlator(reduced_two_qubit_dm_zigzag_ideal(L))
        fid = swapping_ideal_end_fidelity(L)
        print(
            f"  L={L}: 單腳靜態 CHSH={ch_s:.4f} | 雙腳之字 CHSH={ch_z:.4f} | "
            f"交換 CHSH={ch_w:.4f} | 交換塌縮 P00+P11={fid:.4f}"
        )
        rows.append(
            {
                "L": L,
                "group": "ideal",
                "strategy": "static_ideal",
                "num_qubits": L + 1,
                "cx": circuit_metrics(generate_ladder_bell_circuit(L))["cx"],
                "depth": circuit_metrics(generate_ladder_bell_circuit(L))["depth"],
                "chsh_ideal": round(ch_s, 6),
                "p_noisy_e0e1": "",
            }
        )
        rows.append(
            {
                "L": L,
                "group": "ideal",
                "strategy": "zigzag_ideal",
                "num_qubits": 2 * (L + 1),
                "cx": circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["cx"],
                "depth": circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["depth"],
                "chsh_ideal": round(ch_z, 6),
                "p_noisy_e0e1": "",
            }
        )
        rows.append(
            {
                "L": L,
                "group": "ideal",
                "strategy": "swapping_ideal",
                "num_qubits": L + 1,
                "cx": circuit_metrics(generate_swapping_circuit(L, False))["cx"],
                "depth": circuit_metrics(generate_swapping_circuit(L, False))["depth"],
                "chsh_ideal": round(ch_w, 6),
                "p_noisy_e0e1": "",
            }
        )

    print(
        f"\n--- 組 A：同雜訊 P(00)+P(11)（末態全線量測 marginal 兩端）；L∈{L_list_noisy} ---"
    )
    L_noisy = []
    P_static = []
    P_zigzag = []
    for L in L_list_noisy:
        p_st = run_phi_plus_z_diagnostic_noisy(
            generate_ladder_bell_circuit(L, "Phi+"),
            endpoint_qubits=(0, L),
            noise_model=noise,
            shots=shots,
        )
        p_zz = run_phi_plus_z_diagnostic_noisy(
            generate_zigzag_ladder_bell_circuit(L, "Phi+"),
            endpoint_qubits=(0, L),
            noise_model=noise,
            shots=shots,
        )
        L_noisy.append(L)
        P_static.append(p_st)
        P_zigzag.append(p_zz)
        print(f"  L={L}  單腳靜態 P≈{p_st:.4f}  |  雙腳之字 P≈{p_zz:.4f}")
        rows.append(
            {
                "L": L,
                "group": "end_meas_A",
                "strategy": "static_noisy",
                "num_qubits": L + 1,
                "cx": circuit_metrics(generate_ladder_bell_circuit(L))["cx"],
                "depth": circuit_metrics(generate_ladder_bell_circuit(L))["depth"],
                "chsh_ideal": "",
                "p_noisy_e0e1": round(p_st, 6),
            }
        )
        rows.append(
            {
                "L": L,
                "group": "end_meas_A",
                "strategy": "zigzag_noisy",
                "num_qubits": 2 * (L + 1),
                "cx": circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["cx"],
                "depth": circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["depth"],
                "chsh_ideal": "",
                "p_noisy_e0e1": round(p_zz, 6),
            }
        )

    L_list_swap_noisy = [1, 3, 5, 7]
    print(f"\n--- 組 B：糾纏交換 L∈{L_list_swap_noisy}（古典解碼）---")
    p_sw_list: list[float] = []
    for L_sw in L_list_swap_noisy:
        p_sw = run_swapping_phi_plus_diagnostic_noisy(
            L_sw,
            noise,
            shots,
            classical_latency_before_endpoint_meas_ns=lat,
            bsm_parallel_idle_ns=bsm_idle,
        )
        p_sw_list.append(p_sw)
        print(f"  L={L_sw}  糾纏交換 P≈{p_sw:.4f}")
        qc_sw = generate_swapping_circuit(
            L_sw,
            False,
            classical_latency_before_endpoint_meas_ns=lat,
            bsm_parallel_idle_ns=bsm_idle,
        )
        rows.append(
            {
                "L": L_sw,
                "group": "swap_decode_B",
                "strategy": "swapping_noisy",
                "num_qubits": qc_sw.num_qubits,
                "cx": circuit_metrics(qc_sw)["cx"],
                "depth": circuit_metrics(qc_sw)["depth"],
                "chsh_ideal": "",
                "p_noisy_e0e1": round(p_sw, 6),
            }
        )

    fieldnames = ["L", "group", "strategy", "num_qubits", "cx", "depth", "chsh_ideal", "p_noisy_e0e1"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"\n已寫入 {csv_path}")

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(L_noisy, P_static, "o-", label="A: single-rail static (noisy)")
    ax.plot(L_noisy, P_zigzag, "s-", color="darkgreen", label="A: two-rail zigzag static (noisy)")
    ax.plot(
        L_list_swap_noisy,
        p_sw_list,
        "^-",
        color="crimson",
        lw=2,
        ms=8,
        label="B: entanglement swapping (decode)",
    )
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, label="ideal")
    ax.set_xlabel("L (segments along rail e0–e1)")
    ax.set_ylabel("P(00)+P(11) on endpoints")
    ax.set_title("Same noise: group A (end meas) vs group B (swap L=3)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_ylim(0.45, 1.05)
    fig.tight_layout()
    fig_path = FIGURES / "crossover_p_success.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"已儲存 {fig_path}")

    fig2, ax2 = plt.subplots(figsize=(8, 4.2))
    cx_s = [circuit_metrics(generate_ladder_bell_circuit(L))["cx"] for L in L_list_ideal]
    cx_z = [circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["cx"] for L in L_list_ideal]
    cx_w = [circuit_metrics(generate_swapping_circuit(L, False))["cx"] for L in L_list_ideal]
    ax2.plot(L_list_ideal, cx_s, "o-", label="single-rail static")
    ax2.plot(L_list_ideal, cx_z, "s-", color="darkgreen", label="two-rail zigzag static")
    ax2.plot(L_list_ideal, cx_w, "^-", color="purple", label="swapping (prep+BSM)")
    ax2.set_xlabel("L")
    ax2.set_ylabel("CNOT count")
    ax2.set_title("Resources: CNOTs vs L (ideal circuits)")
    ax2.legend()
    fig2.tight_layout()
    cx_path = FIGURES / "resources_cx_vs_L.png"
    fig2.savefig(cx_path, dpi=150)
    plt.close(fig2)
    print(f"已儲存 {cx_path}")

    txt_path = RESULTS / "circuit_static_L5.txt"
    txt_path.write_text(str(generate_ladder_bell_circuit(5).draw(output="text")), encoding="utf-8")
    txt_path_z = RESULTS / "circuit_zigzag_L5.txt"
    txt_path_z.write_text(str(generate_zigzag_ladder_bell_circuit(5).draw(output="text")), encoding="utf-8")
    txt_path2 = RESULTS / "circuit_swapping_L3_feedforward.txt"
    txt_path2.write_text(str(generate_swapping_circuit(3, True).draw(output="text")), encoding="utf-8")
    print(f"已寫入電路 ASCII: {txt_path.name}, {txt_path_z.name}, {txt_path2.name}")

    formula_csv = RESULTS / "resource_formula_table.csv"
    form_rows = []
    for L in range(1, 11):
        N = L + 1
        s_form = static_chain_cnot_count(L)
        s_circ = circuit_metrics(generate_ladder_bell_circuit(L))["cx"]
        s_dep = circuit_metrics(generate_ladder_bell_circuit(L))["depth"]
        z_form = zigzag_ladder_cnot_count(L)
        z_circ = circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["cx"]
        z_dep = circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["depth"]
        if L % 2 == 1:
            w_form = entanglement_swap_cnot_count(L)
            w_circ = circuit_metrics(generate_swapping_circuit(L, False))["cx"]
            w_dep = circuit_metrics(generate_swapping_circuit(L, False))["depth"]
        else:
            w_form = w_circ = w_dep = ""
        form_rows.append(
            {
                "L": L,
                "N_single_rail": N,
                "N_two_rail_zigzag": 2 * (L + 1),
                "static_cx_closed": s_form,
                "static_cx": s_circ,
                "static_depth": s_dep,
                "zigzag_cx_closed": z_form,
                "zigzag_cx": z_circ,
                "zigzag_depth": z_dep,
                "swap_cx_closed": w_form,
                "swap_cx": w_circ,
                "swap_depth": w_dep,
            }
        )
    with formula_csv.open("w", newline="", encoding="utf-8") as f:
        fw = csv.DictWriter(f, fieldnames=list(form_rows[0].keys()))
        fw.writeheader()
        fw.writerows(form_rows)
    print(f"已寫入 {formula_csv}")

    print("\n" + DYNAMIC_CIRCUIT_TRADEOFF_NOTE.strip())
    print(
        "\n完成。組 B：糾纏交換於 L∈{1,3,5,7} 以古典解碼（postprocess_swapping_shot_general）；"
        "實機仍須對應量子前饋與延遲建模。"
    )
