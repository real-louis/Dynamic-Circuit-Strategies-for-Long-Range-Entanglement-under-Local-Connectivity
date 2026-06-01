# 再現性說明（Reproducibility）

本目錄為 **推甄整合包**，整合 `2026:5:5`（Ephys 競賽）與 `2026:5:18`（PRX Quantum reproduce）。

## 環境

```bash
cd "/Users/louis/Desktop/量子運算專題/2026:6:1"
python3 -m pip install -r requirements.txt
```

> macOS 注意：若路徑含 `:`，建議直接用系統 Python 或自訂 venv 路徑（勿在 `2026:5:18` 內建 venv）。

## 一鍵建置（推薦）

```bash
python scripts/build_graduate_package.py
```

依序執行：

1. `../2026:5:5/competition_suite.py` — 產出 crossover CSV 與圖
2. `../2026:5:18/` pytest — 驗證 PRX 電路等價性
3. `scripts/error_budget_analysis.py` — error budget 表與對照圖

## 分步執行

### Step 1：Ephys 競賽數據

```bash
cd "../2026:5:5"
pip install -r requirements.txt
python competition_suite.py
```

預期：

- `results/crossover_and_resources.csv`
- `figures/crossover_p_success.png`
- `figures/resources_cx_vs_L.png`

### Step 2：PRX Quantum 電路測試

```bash
cd "../2026:5:18"
pip install -r requirements.txt
python -m pytest verify/test_equivalence.py -v
```

### Step 3：Error budget 分析

```bash
cd "../2026:6:1"
python scripts/error_budget_analysis.py
```

預期：

- `results/error_budget_table.csv`
- `figures/error_budget_fidelity_vs_L.png`
- `figures/crossover_theory_vs_simulation.png`

## Word 報告（中英雙版）

```bash
python3 scripts/generate_word_reports.py
```

預期：

- `reports/Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx`（對外繳交）
- `reports/局域連接下長程糾纏動態電路策略_專題報告_ZH.docx`（自用）

GitHub URL：編輯 `config/submission.json` 後重新執行上述指令。

## GitHub 上傳包

```bash
python3 scripts/package_github_submission.py
```

詳見 `docs/GITHUB_UPLOAD_GUIDE.md`。

## 文件產出

推甄文件位於 `docs/`，無需執行程式即可閱讀：

- `docs/推甄專題報告.md`
- `docs/研究亮點卡.md`
- `docs/推薦信素材.md`
- `docs/自傳讀書計畫素材.md`

## 疑難排解

| 問題 | 解法 |
|------|------|
| crossover 圖 panel (b) 空白 | 先執行 Step 1 |
| pytest 失敗 | 確認 `qiskit>=2.0`（2026:5:18） |
| 圖表中文亂碼 | matplotlib 使用 DejaVu Serif，報告以 Markdown 為主 |
