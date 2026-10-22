# CA Knowledge Hub v1.0.0 — Windows

Your lifelong, local-first CA knowledge and professional-practice system.
Everything runs on this computer only. No account, no cloud, no telemetry.

## First launch

1. Extract this ZIP anywhere (e.g. `Documents\CA Knowledge Hub`).
2. Double-click **`run_windows.bat`**.
   - If Python is missing, it installs it automatically via winget.
   - It creates an isolated environment, installs dependencies
     (needs internet **once**), builds the module libraries
     (about a minute), then opens the app in your browser.
3. Keep the black window open while using the app. Close it to stop.

Your data lives in the `data\` folder next to the app
(`data\hub.db` — the database, `data\backups\` — automatic backups).
Copy the whole folder to back up or move computers.

## What's inside

12 modules, all offline and deterministic:

| Module | What it does |
|---|---|
| Audit | Risk → assertion → control → procedure → evidence chains (29 factors, 99 procedures, 30 rules) |
| Tax | 14-step tax decision chain, 63 rules, WHT calc tables |
| Financial Reporting | 13 IAS/IFRS standards, treatment suggester, worked examples |
| Reconciliation | Bank/supplier/GL matching workbench |
| Data Analysis | Spreadsheet cleaning, variance, group-by, templates |
| BIA / Case Analysis | 49 frameworks, 44 calculations, 210 flashcards, 27 mind maps |
| FS Analysis | 16 ratios, trends, common-size, red-flag prompts |
| Working Papers | 9 templates, review workflow, exception + evidence tracking |
| Corporate Finance | NPV/IRR/WACC/valuation with visible assumptions |
| Company Law | Provision research tracker, compliance calendar, filings |
| Research | Issue register, source comparison, versioned conclusions |
| Study Mode | SM-2 flashcards, 131-question bank, revision planner (your private study data) |

Plus: document library with full-text search, workspaces
(on-demand module bundles with cross-links), backup/restore with
verification, JSON/CSV/SQLite export.

## Verify it yourself

The `tests\` folder has 188 automated tests. After installing:
`.\.venv\Scripts\python -m pytest tests\ -q` — all should pass.

## Notes

- Study content is pitched at CA Inter level. Tax/company-law
  content is marked with verification status — check primary
  sources (FBR/SECP) before relying on it professionally.
- This is v1.0.0 covering build phases 1A–13. The build log is
  `docs\PROJECT_STATUS.md` (included).
