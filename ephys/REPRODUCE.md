# 再現性說明（Reproducibility）

本資料夾為「整理版」副本：將核心程式置於 `src/`，入口腳本留在根目錄作為 wrapper，
避免影響原本 `python competition_suite.py` 等使用方式。

## 環境

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-lock.txt   # 或 requirements.txt
```

## 一鍵重產圖表與 CSV

在 `organized/` 目錄內：

```bash
python competition_suite.py
```

預期產出：

- `results/crossover_and_resources.csv`
- `results/resource_formula_table.csv`
- `figures/crossover_p_success.png`
- `figures/resources_cx_vs_L.png`
- `results/circuit_static_L5.txt`、`results/circuit_swapping_L3_feedforward.txt`

## 產出 PDF 書面報告（繁中、附圖表）

在專案根目錄（含 `src/` 與 `results/`）：

```bash
PYTHONPATH=src python scripts/generate_report_pdf.py
```

預期產出：`reports/Ephys2026_梯子佈局貝爾態_專題報告.pdf`（依 `results/*.csv` 自動繪圖；請先執行 `competition_suite.py`）。

## 初賽繳交資料夾（含更新後圖表）

```bash
python package_submission.py
```

輸出目錄：`organized/submission/Ephys2026_初賽繳交/`。

