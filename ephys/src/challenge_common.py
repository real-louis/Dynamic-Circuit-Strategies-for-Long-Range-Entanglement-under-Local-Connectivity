"""
Ephys 2026 梯子佈局貝爾態 — 共用函式。

【符號】L＝單腳路徑段數；N＝L+1 個量子位元（q0…qL）。整張雙腳梯子節點數常為約 2(L+1)，
與本 repo 子問題所用 N 不同——書面務必區分。

【CNOT 封閉式】靜態鏈 #CX＝2L−1；雙腳之字形靜態 #CX＝4L+2(L mod 2)−1；糾纏交換（L 奇）#CX＝L。
見 static_chain_cnot_count、zigzag_ladder_cnot_count、entanglement_swap_cnot_count、verify_resource_formulas。

【動態電路】兩比特深度敘述勿過度簡化成「與 L 無關的總時間」；見 DYNAMIC_CIRCUIT_TRADEOFF_NOTE。

e0、e1 對應 q0、qL。糾纏交換須 L 奇；貝爾測量兩 bit 皆須保留。|Φ+⟩ 前饋：控制端測得 1→X，目標端測得 1→Z。
"""

from __future__ import annotations

import math

from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister, Delay, QuantumRegister
from qiskit.quantum_info import DensityMatrix, Operator, Pauli, Statevector, partial_trace


def labeled_idle_delay(duration_ns: float, role: str) -> Delay:
    """
    具名 delay，供 Aer NoiseModel 以 instruction label 區分不同時長之熱弛豫。

    勿對含此類 delay 的電路做 transpile，否則 label 可能遺失並退化成一般 delay。
    """
    d = Delay(float(duration_ns), unit="ns")
    d.label = f"idle_{role}"
    return d


def _append_parallel_idle(qc: QuantumCircuit, qr: QuantumRegister, q_indices: list[int], duration_ns: float, role: str) -> None:
    for i in q_indices:
        qc.append(labeled_idle_delay(duration_ns, role), [qr[i]])


def generate_ladder_bell_circuit(L: int, target_state: str = "Phi+") -> QuantumCircuit:
    """
    靜態策略：沿單腳鏈 H(e0) + 正向 CNOT 鏈 + 反向 CNOT 解糾纏，使僅 e0、e1 糾纏。

    若將最前面的 H(e0) 換成 X/Z 或換初始 |1⟩，GHZ 構造會改變，最後兩端通常不再是
    目標貝爾態，需重新推導補償（競賽書面可寫「初始門決定擴散後的整體相位與宇稱」）。
    """
    qc = QuantumCircuit(L + 1)
    e0, e1 = 0, L
    qc.h(e0)
    for i in range(L):
        qc.cx(i, i + 1)
    for i in range(L - 1, 0, -1):
        qc.cx(i - 1, i)
    if target_state == "Phi-":
        qc.z(e0)
    elif target_state == "Psi+":
        qc.x(e1)
    elif target_state == "Psi-":
        qc.z(e0)
        qc.x(e1)
    return qc


def zigzag_ladder_path_edges(L: int) -> list[tuple[int, int]]:
    """
    雙腳梯子上從 v0 走到 v_L 的一條哈密頓路徑之邊（方向為 CNOT 控制→目標）。

    量子位元編號：上軌 v_i → i；下軌 w_i → L+1+i；共 2(L+1) 個量子位元。
    路徑僅使用梯子圖上的鄰邊（橫檔或同腳相鄰）。
    """
    if L < 1:
        raise ValueError("L 須為 >= 1。")
    edges: list[tuple[int, int]] = []
    k = 0
    while k < L:
        edges.append((k, L + 1 + k))
        edges.append((L + 1 + k, L + 1 + k + 1))
        edges.append((L + 1 + k + 1, k + 1))
        k += 1
        if k < L:
            edges.append((k, k + 1))
            k += 1
    return edges


def zigzag_ladder_cnot_count(L: int) -> int:
    """之字形雙腳靜態鏈：前向 |E| 個 CX + 反向 |E|−1 個 CX。"""
    m = len(zigzag_ladder_path_edges(L))
    return 2 * m - 1


def generate_zigzag_ladder_bell_circuit(L: int, target_state: str = "Phi+") -> QuantumCircuit:
    """
    雙腳梯子策略：沿 `zigzag_ladder_path_edges` 做與單腳靜態相同的 GHZ 型前向／反向 CNOT，
    使僅 v0（q0）、v_L（qL）保持 |Φ+⟩（其餘線路可解糾纏離開計算子空間）。

    使用 2(L+1) 個量子位元；e0、e1 仍對應上軌兩端 q0、qL。
    """
    n = 2 * (L + 1)
    e0, e1 = 0, L
    edges = zigzag_ladder_path_edges(L)
    qc = QuantumCircuit(n)
    qc.h(e0)
    for a, b in edges:
        qc.cx(a, b)
    for a, b in reversed(edges[:-1]):
        qc.cx(a, b)
    if target_state == "Phi-":
        qc.z(e0)
    elif target_state == "Psi+":
        qc.x(e1)
    elif target_state == "Psi-":
        qc.z(e0)
        qc.x(e1)
    return qc


def build_noise_model(
    p_1q: float,
    p_2q: float,
    *,
    p_readout_flip: float | None = None,
    t1: float | None = None,
    t2: float | None = None,
    t_1q_gate: float | None = None,
    t_2q_gate: float | None = None,
    t_measure: float | None = None,
    idle_labeled_delays: dict[str, float] | None = None,
):
    """
    Aer 雜訊模型（可比較靜態鏈與糾纏交換）。

    - 預設（僅 p_1q、p_2q）：與舊版相同，單／雙位元閘 depolarizing。
    - 若給定 t1、t2 與各 gate 時間：在 depolarizing 之外再 **compose** 熱弛豫（與常見
      IBM 範例相同：depolarizing ∘ thermal），量測閘另加單比特弛豫（t_measure）。
    - p_readout_flip：對稱古典讀出錯 P(1|0)=P(0|1)=p_readout_flip。
    - idle_labeled_delays：角色名（如 bsm_cx、bsm_h、bsm_meas、endpoint_wait）→ 該段 delay
      的 ns 長度；須與 `labeled_idle_delay` / `generate_swapping_circuit` 一致。僅在啟用
      熱弛豫時允許；各角色以具 label 的 Delay 模板註冊熱雜訊（勿 transpile 剝除 label）。

    參數時間單位須一致（本專題比較腳本採 **奈秒 ns**）。
    """
    from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, thermal_relaxation_error

    noise_model = NoiseModel()

    if t1 is not None or t2 is not None:
        if t1 is None or t2 is None:
            raise ValueError("熱弛豫需同時指定 t1 與 t2。")
        if t_1q_gate is None or t_2q_gate is None or t_measure is None:
            raise ValueError("啟用熱弛豫時需指定 t_1q_gate、t_2q_gate、t_measure（ns）。")
        th_1 = thermal_relaxation_error(t1, t2, t_1q_gate)
        th_2_1q = thermal_relaxation_error(t1, t2, t_2q_gate)
        th_2 = th_2_1q.tensor(th_2_1q)
        err_1q = depolarizing_error(p_1q, 1).compose(th_1)
        err_2q = depolarizing_error(p_2q, 2).compose(th_2)
        err_meas = thermal_relaxation_error(t1, t2, t_measure)
        noise_model.add_all_qubit_quantum_error(err_1q, ["h", "x", "z"])
        noise_model.add_all_qubit_quantum_error(err_2q, ["cx"])
        noise_model.add_all_qubit_quantum_error(err_meas, ["measure"])
        if idle_labeled_delays:
            for role, t_ns in idle_labeled_delays.items():
                t_ns = float(t_ns)
                if t_ns <= 0:
                    continue
                inst = labeled_idle_delay(t_ns, role)
                noise_model.add_all_qubit_quantum_error(thermal_relaxation_error(t1, t2, t_ns), [inst])
    else:
        noise_model.add_all_qubit_quantum_error(depolarizing_error(p_1q, 1), ["h", "x", "z"])
        noise_model.add_all_qubit_quantum_error(depolarizing_error(p_2q, 2), ["cx"])
        if idle_labeled_delays:
            raise ValueError("僅指定 idle_labeled_delays 但未指定 t1/t2 時無法建立 delay 弛豫。")

    if p_readout_flip is not None:
        p = float(p_readout_flip)
        if not 0.0 <= p <= 1.0:
            raise ValueError("p_readout_flip 須在 [0,1]。")
        matrix = [[1.0 - p, p], [p, 1.0 - p]]
        noise_model.add_all_qubit_readout_error(ReadoutError(matrix))

    return noise_model


def default_fair_comparison_noise_params() -> dict:
    """
    書面／比較用一組一致參數：閘 depolarizing + T1/T2 門時間弛豫 + 讀出 + 端點古典等待延遲。

    數值為示範級超導量級（非特定實機校準）；重點是兩策略共用同一模型。
    """
    return {
        "p_1q": 0.001,
        "p_2q": 0.01,
        "p_readout_flip": 0.02,
        "t1": 60_000.0,
        "t2": 80_000.0,
        "t_1q_gate": 25.0,
        "t_2q_gate": 350.0,
        "t_measure": 1_200.0,
        "classical_latency_ns": 2_500.0,
    }


def fair_idle_delay_profile(fp: dict) -> dict[str, float]:
    """由 default_fair_comparison_noise_params 建 `build_noise_model(..., idle_labeled_delays=...)` 用字典。"""
    lat = float(fp["classical_latency_ns"])
    profile = {
        "bsm_cx": float(fp["t_2q_gate"]),
        "bsm_h": float(fp["t_1q_gate"]),
        "bsm_meas": float(fp["t_measure"]),
    }
    if lat > 0:
        profile["endpoint_wait"] = lat
    return profile


def generate_swapping_circuit(
    L: int,
    apply_feedforward: bool = False,
    *,
    classical_latency_before_endpoint_meas_ns: float = 0.0,
    bsm_parallel_idle_ns: tuple[float, float, float] | None = None,
) -> QuantumCircuit:
    """
    糾纏交換策略：相鄰 |Φ+⟩ 對 + 標準貝爾測量 (CX 於 (k,k+1) 再 H(k) 後 Z 量測兩線)。

    apply_feedforward=True 時插入 if_test（方便畫電路／口頭說明）。部分 Aer 版本對動態
    電路仍有數值問題；含雜訊比較時建議用 generate_swapping_circuit(..., False) 並對
    L=3 做古典讀取後處理（見 postprocess_swapping_shot_l3）。

    classical_latency_before_endpoint_meas_ns：在最後量測 e0、e1 前，對兩端點插入具名
    idle delay（role=endpoint_wait），模擬古典處理等待；須與 noise model 中同角色之
    熱弛豫時間一致。

    bsm_parallel_idle_ns：若給定 (t_cx, t_h, t_meas)，則每一層 BSM 分三時間片：未參與
    CX／H／量測的量子位元分別與該閘並行 idle（具名 bsm_cx、bsm_h、bsm_meas），對齊
    `fair_idle_delay_profile`。
    """
    if L % 2 == 0:
        raise ValueError("糾纏交換此構造需要 L 為奇數（使 N=L+1 為偶數，可鋪滿貝爾對）。")
    n = L + 1
    n_layers = (L - 1) // 2
    bsm_regs = [ClassicalRegister(2, f"bsm{s}") for s in range(n_layers)]
    cr_out = ClassicalRegister(2, "out")
    qr = QuantumRegister(n, "q")
    qc = QuantumCircuit(qr, *bsm_regs, cr_out)

    for s in range(0, n, 2):
        qc.h(qr[s])
        qc.cx(qr[s], qr[s + 1])

    layer = 0
    for k in range(1, L, 2):
        if bsm_parallel_idle_ns is not None:
            t_cx, t_h, t_m = (float(bsm_parallel_idle_ns[0]), float(bsm_parallel_idle_ns[1]), float(bsm_parallel_idle_ns[2]))
            idle_cx = [i for i in range(n) if i not in (k, k + 1)]
            _append_parallel_idle(qc, qr, idle_cx, t_cx, "bsm_cx")
            qc.cx(qr[k], qr[k + 1])
            idle_h = [i for i in range(n) if i != k]
            _append_parallel_idle(qc, qr, idle_h, t_h, "bsm_h")
            qc.h(qr[k])
            idle_m = [i for i in range(n) if i not in (k, k + 1)]
            _append_parallel_idle(qc, qr, idle_m, t_m, "bsm_meas")
        else:
            qc.cx(qr[k], qr[k + 1])
            qc.h(qr[k])
        qc.measure(qr[k], bsm_regs[layer][0])
        qc.measure(qr[k + 1], bsm_regs[layer][1])
        if apply_feedforward:
            right = k + 2
            if right < n:
                with qc.if_test((bsm_regs[layer][0], 1)):
                    qc.x(qr[right])
                with qc.if_test((bsm_regs[layer][1], 1)):
                    qc.z(qr[right])
        layer += 1

    if classical_latency_before_endpoint_meas_ns > 0:
        lat = float(classical_latency_before_endpoint_meas_ns)
        for qi in (0, L):
            qc.append(labeled_idle_delay(lat, "endpoint_wait"), [qr[qi]])

    qc.measure(qr[0], cr_out[0])
    qc.measure(qr[L], cr_out[1])
    return qc


def swapping_ideal_end_fidelity(L: int) -> float:
    """無雜訊下以 Statevector.measure 逐步塌縮 + 量子層級 Pauli 修正，檢查 e0-e1 是否 |Φ+⟩。"""
    if L % 2 == 0:
        raise ValueError("L 必須為奇數。")
    n = L + 1

    def x_op(q: int) -> Operator:
        c = QuantumCircuit(n)
        c.x(q)
        return Operator(c)

    def z_op(q: int) -> Operator:
        c = QuantumCircuit(n)
        c.z(q)
        return Operator(c)

    prep = QuantumCircuit(n)
    for s in range(0, n, 2):
        prep.h(s)
        prep.cx(s, s + 1)
    psi = Statevector.from_instruction(prep)

    for k in range(1, L, 2):
        bsm = QuantumCircuit(n)
        bsm.cx(k, k + 1)
        bsm.h(k)
        psi = psi.evolve(Operator(bsm))
        outcome, psi = psi.measure([k, k + 1])
        m0, m1 = int(outcome[0]), int(outcome[1])
        right = k + 2
        if m0:
            psi = psi.evolve(x_op(right))
        if m1:
            psi = psi.evolve(z_op(right))

    dm = DensityMatrix(psi)
    trace_idx = list(range(1, L))
    rdm = partial_trace(dm, trace_idx)
    return float((rdm.data[0, 0] + rdm.data[3, 3]).real)


def postprocess_swapping_shot_l3(bsm0: int, bsm1: int, o_e0: int, o_e1: int) -> tuple[int, int]:
    """
    僅適用 L=3（單次貝爾測量）：古典上對 e1 讀取做 X 補償（與量子前饋在 Z 基讀取等價）。
    bsm0, bsm1 為 q1、q2 的測量結果（與 generate_swapping_circuit 中 bsm0[0],bsm0[1] 對應）。
    """
    return o_e0, o_e1 ^ bsm0


def parse_aer_memory_l3(shot: str) -> tuple[int, int, int, int]:
    """
    將 Aer 的 memory 字串還原為 (m0, m1, o_e0, o_e1)。

    實測 Qiskit Aer 2.x 對本電路回傳兩段各 2 bit、空格分隔，且 **先 e0/e1（out）、後 bsm**
    （與暫存器宣告順序可能相反）；若升版後結果異常，請先用 noiseless 確認格式。
    """
    left, right = shot.split()
    if len(left) != 2 or len(right) != 2:
        raise ValueError(f"預期兩段各 2 bit，得到 {shot!r}")
    o_e0, o_e1 = int(left[0]), int(left[1])
    m0, m1 = int(right[0]), int(right[1])
    return m0, m1, o_e0, o_e1


def postprocess_swapping_shot_general(shot: str, L: int) -> tuple[int, int]:
    """
    與 `generate_swapping_circuit(..., apply_feedforward=False)` 搭配：Aer memory 為
    「out（兩端 Z 讀出）」在前，之後各層 bsm0、bsm1、…（各 2 bit）。古典上對 e1 做
    等同量子前饋之補償：對每一層 BSM 的第一個 bit 與 o_e1 做 XOR（L=3 時即
    `postprocess_swapping_shot_l3` 之行為）。
    """
    if L % 2 == 0:
        raise ValueError("糾纏交換此構造需要 L 為奇數。")
    parts = shot.split()
    expected = (L - 1) // 2 + 1
    if len(parts) != expected:
        raise ValueError(f"L={L}: 預期 memory 共 {expected} 段，得到 {len(parts)}：{shot!r}")
    o0, o1 = int(parts[0][0]), int(parts[0][1])
    if L == 1:
        return o0, o1
    flip = 0
    for seg in parts[1:]:
        if len(seg) != 2:
            raise ValueError(f"BSM 段須為 2 bit：{seg!r}")
        flip ^= int(seg[0])
    return o0, o1 ^ flip


def run_swapping_phi_plus_diagnostic_noisy(
    L: int,
    noise_model,
    shots: int,
    *,
    classical_latency_before_endpoint_meas_ns: float = 0.0,
    bsm_parallel_idle_ns: tuple[float, float, float] | None = None,
) -> float:
    """
    糾纏交換末態：對 e0、e1 之 Z 讀出做古典解碼後，回傳 P(00)+P(11)（|Φ+⟩ 診斷）。
    """
    from qiskit_aer import AerSimulator

    if L % 2 == 0:
        raise ValueError("L 須為奇數。")
    qc = generate_swapping_circuit(
        L,
        apply_feedforward=False,
        classical_latency_before_endpoint_meas_ns=float(classical_latency_before_endpoint_meas_ns),
        bsm_parallel_idle_ns=bsm_parallel_idle_ns,
    )
    sim = AerSimulator(noise_model=noise_model)
    mem = sim.run(qc, shots=shots, memory=True).result().get_memory()
    ok = 0
    for shot in mem:
        c0, c1 = postprocess_swapping_shot_general(shot, L)
        if c0 == c1:
            ok += 1
    return ok / shots


def estimate_chsh_mermin_noisy_shots(
    prep: QuantumCircuit,
    noise_model,
    shots: int,
    *,
    endpoint_qubits: tuple[int, int],
) -> float:
    """
    以矇特卡羅估計 `chsh_mermin_correlator`：對端點做 ZZ（直接 Z 量測邊際）與 XX
    （端點各加 H 後 Z 量測邊際），無需完整密度矩陣（適用寬電路如之字形）。
    """
    from qiskit.result import marginal_counts
    from qiskit_aer import AerSimulator

    e0, e1 = endpoint_qubits
    n = prep.num_qubits
    sim = AerSimulator(noise_model=noise_model)

    def e_zz_from_marginal(cts: dict) -> float:
        tot = sum(cts.values())
        if tot <= 0:
            return 0.0
        p00 = cts.get("00", 0) / tot
        p11 = cts.get("11", 0) / tot
        p01 = cts.get("01", 0) / tot
        p10 = cts.get("10", 0) / tot
        return p00 + p11 - p01 - p10

    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc_zz = QuantumCircuit(qr, cr)
    qc_zz.compose(prep, qubits=range(n), inplace=True)
    for i in range(n):
        qc_zz.measure(qr[i], cr[i])
    r1 = sim.run(qc_zz, shots=shots).result()
    c_z = marginal_counts(r1, indices=[e0, e1]).get_counts()
    ezz = e_zz_from_marginal(c_z)

    qr2 = QuantumRegister(n, "q2")
    cr2 = ClassicalRegister(n, "c2")
    qc_xx = QuantumCircuit(qr2, cr2)
    qc_xx.compose(prep, qubits=range(n), inplace=True)
    qc_xx.h(e0)
    qc_xx.h(e1)
    for i in range(n):
        qc_xx.measure(qr2[i], cr2[i])
    r2 = sim.run(qc_xx, shots=shots).result()
    c_x = marginal_counts(r2, indices=[e0, e1]).get_counts()
    exx = e_zz_from_marginal(c_x)

    return math.sqrt(2.0) * (ezz + exx)


def chsh_noisy_static_chain_shots(L: int, noise_model, shots: int) -> float:
    """單腳靜態製備後，含噪矇特卡羅估計端點 CHSH 型關聯量。"""
    qc = generate_ladder_bell_circuit(L, "Phi+")
    return estimate_chsh_mermin_noisy_shots(qc, noise_model, shots, endpoint_qubits=(0, L))


def chsh_noisy_zigzag_shots(L: int, noise_model, shots: int) -> float:
    """雙腳之字形靜態製備後，含噪矇特卡羅估計上軌兩端點 CHSH 型關聯量。"""
    qc = generate_zigzag_ladder_bell_circuit(L, "Phi+")
    return estimate_chsh_mermin_noisy_shots(qc, noise_model, shots, endpoint_qubits=(0, L))


def circuit_metrics(qc: QuantumCircuit) -> dict:
    """回傳 CX 數、電路深度、寬度（供策略資源比較表）。"""
    ops = qc.count_ops()
    return {
        "num_qubits": qc.num_qubits,
        "cx": int(ops.get("cx", 0)),
        "depth": qc.depth(),
    }


def run_phi_plus_z_diagnostic_noisy(
    prep: QuantumCircuit,
    *,
    endpoint_qubits: tuple[int, int],
    noise_model,
    shots: int,
) -> float:
    """
    一致比較用：prep 之後對**全部**量子位元做 Z 量測，回傳兩端點上 P(00)+P(11)（|Φ+⟩ 診斷）。

    與 `marginal_counts(..., indices=[e0,e1])` 對齊；不經 transpile，以免剝除具名 delay。
    """
    from qiskit.result import marginal_counts
    from qiskit_aer import AerSimulator

    e0, e1 = endpoint_qubits
    n = prep.num_qubits
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    meas = QuantumCircuit(qr, cr)
    meas.compose(prep, qubits=range(n), inplace=True)
    for i in range(n):
        meas.measure(qr[i], cr[i])
    sim = AerSimulator(noise_model=noise_model)
    result = sim.run(meas, shots=shots).result()
    m = marginal_counts(result, indices=[e0, e1])
    cts = m.get_counts()
    return (cts.get("00", 0) + cts.get("11", 0)) / shots


def static_chain_cnot_count(L: int) -> int:
    """
    靜態 GHZ 鏈 + 解糾纏之 CNOT 個數：2L − 1（L ≥ 1）。
    L 為單腳段數，與 generate_ladder_bell_circuit 參數一致。
    """
    if L < 1:
        raise ValueError("L 須為 >= 1 的整數。")
    return 2 * L - 1


def entanglement_swap_cnot_count(L: int) -> int:
    """
    本專題實作之糾纏交換（相鄰貝爾對 + BSM）CNOT 個數：L。
    僅定義於 **L 為奇數**（與 generate_swapping_circuit 一致）。
    """
    if L < 1 or L % 2 == 0:
        raise ValueError("糾纏交換此構造需要 L 為正奇數。")
    return L


def verify_resource_formulas(max_L: int = 15) -> list[str]:
    """
    核對封閉式與 Qiskit 計數一致。若有差異回傳錯誤訊息列表（空列表代表通過）。
    """
    errors: list[str] = []
    for L in range(1, max_L + 1):
        got = circuit_metrics(generate_ladder_bell_circuit(L))["cx"]
        exp = static_chain_cnot_count(L)
        if got != exp:
            errors.append(f"static L={L}: circuit cx={got}, formula={exp}")
    for L in range(1, max_L + 1, 2):
        got = circuit_metrics(generate_swapping_circuit(L, False))["cx"]
        exp = entanglement_swap_cnot_count(L)
        if got != exp:
            errors.append(f"swapping L={L}: circuit cx={got}, formula={exp}")
    for L in range(1, max_L + 1):
        got = circuit_metrics(generate_zigzag_ladder_bell_circuit(L))["cx"]
        exp = zigzag_ladder_cnot_count(L)
        if got != exp:
            errors.append(f"zigzag L={L}: circuit cx={got}, formula={exp}")
    return errors


def reduced_two_qubit_dm_static(L: int, target_state: str = "Phi+") -> DensityMatrix:
    """靜態策略末態對 (e0,e1) 的約化密度矩陣（理想、無雜訊）。"""
    qc = generate_ladder_bell_circuit(L, target_state=target_state)
    psi = Statevector.from_instruction(qc)
    dm = DensityMatrix(psi)
    trace_idx = [i for i in range(L + 1) if i not in (0, L)]
    return partial_trace(dm, trace_idx)


def reduced_two_qubit_dm_swapping_ideal(L: int) -> DensityMatrix:
    """
    糾纏交換協議末態（逐步塌縮 + Pauli 修正後）在 (e0,e1) 上的約化密度矩陣。
    各測量分支修正後兩端皆為 |Φ+⟩，故與測量結果無關。
    """
    if L % 2 == 0:
        raise ValueError("L 必須為奇數。")
    n = L + 1

    def x_op(q: int) -> Operator:
        c = QuantumCircuit(n)
        c.x(q)
        return Operator(c)

    def z_op(q: int) -> Operator:
        c = QuantumCircuit(n)
        c.z(q)
        return Operator(c)

    prep = QuantumCircuit(n)
    for s in range(0, n, 2):
        prep.h(s)
        prep.cx(s, s + 1)
    psi = Statevector.from_instruction(prep)

    for k in range(1, L, 2):
        bsm = QuantumCircuit(n)
        bsm.cx(k, k + 1)
        bsm.h(k)
        psi = psi.evolve(Operator(bsm))
        outcome, psi = psi.measure([k, k + 1])
        m0, m1 = int(outcome[0]), int(outcome[1])
        right = k + 2
        if m0:
            psi = psi.evolve(x_op(right))
        if m1:
            psi = psi.evolve(z_op(right))

    dm = DensityMatrix(psi)
    trace_idx = list(range(1, L))
    return partial_trace(dm, trace_idx)


def reduced_two_qubit_dm_zigzag_ideal(L: int, target_state: str = "Phi+") -> DensityMatrix:
    """之字形雙腳靜態末態在 (v0,v_L) 上的約化密度矩陣（理想、無雜訊）。"""
    qc = generate_zigzag_ladder_bell_circuit(L, target_state=target_state)
    psi = Statevector.from_instruction(qc)
    n = 2 * (L + 1)
    trace_idx = [i for i in range(n) if i not in (0, L)]
    # 對 Statevector 直接 partial_trace，避免先建完整 n 量子位元 DensityMatrix（n≳16 會爆記憶體）
    return partial_trace(psi, trace_idx)


def chsh_mermin_correlator(rho: DensityMatrix) -> float:
    """
    CHSH 量：對選定的局域可觀測量組合，|Φ+⟩ 理想值為 2*sqrt(2) ≈ 2.828。
    使用 CHSH = sqrt(2) * (⟨ZZ⟩ + ⟨XX⟩)（對本題標準最大違反角設定）。
    """
    zz = float(rho.expectation_value(Pauli("ZZ")).real)
    xx = float(rho.expectation_value(Pauli("XX")).real)
    return math.sqrt(2.0) * (zz + xx)


# --- 拓樸對照（書面／口試用）---
LADDER_TOPOLOGY_NOTE = """
【梯子佈局對照】題目 Fig.1–2：雙腳梯上僅相鄰節點可有雙位元閘。
本程式以「單腳鏈」抽象：e0、e1 為同一腳兩端，沿鏈索引 0→L 皆為圖上相鄰邊。
**整張梯子**節點數可寫成約 2(L+1)（兩腳）；**本程式**僅配置 N=L+1 個量子位元完成
單腳子問題——書面請明講，避免與「全圖節點數」混淆。
實際送量子虛擬機／硬體時，請將 0..L 映射到題目編號（如 e0,1,7,…），
並以 coupling_map + transpile 插入 SWAP。資源封閉式見 static_chain_cnot_count、
zigzag_ladder_cnot_count、entanglement_swap_cnot_count；圖表見 competition_suite。
另見 `generate_zigzag_ladder_bell_circuit`：明確使用雙腳梯子邊之策略。
"""


DYNAMIC_CIRCUIT_TRADEOFF_NOTE = """
【動態電路 vs 單一變換】測量輔助協議常可減少「沿鏈線性累積」的兩比特閘層次，但
量測錯誤、讀取、古典前饋延遲與電路時間仍隨實機而變。短距離可能仍以靜態鏈較佳；
長距離可能出現 crossover——請以同雜訊模擬／實機數據佐證，不宜宣稱「與 L 完全無關的常數時間」。
【BSM 並行 idle】糾纏交換在貝爾測量期間，未參與該步閘的量子位元在實機上仍經歷
退相干；本專題以具名 delay 與 `fair_idle_delay_profile` 對齊各段時長（勿 transpile）。
"""

