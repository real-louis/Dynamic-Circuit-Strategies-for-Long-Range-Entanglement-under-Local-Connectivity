# GitHub 上傳指南（對外繳交用）

## 1. 設定倉庫 URL

編輯 `config/submission.json`，將 `github_repository_url` 改為你的 GitHub 連結：

```json
"github_repository_url": "https://github.com/你的帳號/long-range-entanglement-dynamic-circuits"
```

重新產生 Word 報告以更新連結：

```bash
python3 scripts/generate_word_reports.py
```

## 2. 打包 monorepo

```bash
python3 scripts/package_github_submission.py
```

產出目錄：`github_release/`（含 ephys/、prx/、scripts/、results/、figures/、reports/）

## 3. 上傳至 GitHub

```bash
cd github_release
git init
git add .
git commit -m "Initial release: Ephys 2026 + PRX Quantum 5.030339 reproduction"
# 在 GitHub 網頁建立新 repo 後：
git remote add origin https://github.com/你的帳號/long-range-entanglement-dynamic-circuits.git
git branch -M main
git push -u origin main
```

## 4. 對外繳交清單

| 項目 | 檔案 |
|------|------|
| 英文 Word 報告 | `reports/Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx` |
| 程式倉庫 | GitHub URL（寫在報告第 7 節） |
| 重現說明 | 倉庫內 `REPRODUCE.md` |

## 5. 中文版（自用）

`reports/局域連接下長程糾纏動態電路策略_專題報告_ZH.docx` 不需上傳 GitHub，僅本地閱讀。

## 6. 審查者重現步驟（可貼在 PR / README）

```bash
git clone https://github.com/你的帳號/long-range-entanglement-dynamic-circuits.git
cd long-range-entanglement-dynamic-circuits
pip install -r requirements.txt
python3 scripts/build_graduate_package.py
python3 -m pytest prx/verify/test_equivalence.py -q
```

預期：4 張主要 figure、CSV 數據、pytest 35 passed。
