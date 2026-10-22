# Connecting the CA Knowledge Hub to Terabox

**Design (from the spec, §4 Layer 5):** Terabox is the cloud vault, the Hub
is the local brain. They connect through a deliberate manual workflow — no
API, no passwords shared, nothing that can break when Terabox changes its
website. You remain in control of every file that moves.

## The folder layout (create this in your Terabox)

```
/ca-data/
  /study/          PDFs, textbooks, past papers, notes
  /datasets/       charts of accounts, rate tables, formula sheets (CSV/XLSX)
  /workflows/     checklists, templates (articleship + professional later)
  /hub-inbox/     staging area: files waiting to be pulled into the Hub
  /hub-backups/   Hub backup ZIPs (your safety net)
```

## Direction 1: Terabox → Hub (your documents become searchable)

1. On your Windows laptop, install the TeraBox desktop app (or use
   terabox.com) and sign in.
2. Put the files you want the Hub to know about into `/ca-data/hub-inbox/`
   (or any Terabox folder — then download that folder to your laptop).
3. Install the Hub: extract `ca-knowledge-hub-windows-v1.0.0.zip`,
   double-click `run_windows.bat`.
4. In the Hub: **Settings → Document folder** → point it at the local
   folder where you downloaded the files (e.g.
   `Documents\CA Knowledge Hub\inbox`).
5. Click **Refresh Library**. The Hub scans, detects new/changed files
   (SHA-256), extracts text (PDF/DOCX/TXT/MD/CSV/XLSX), keeps page
   references, and shows you a processing report: new, updated,
   unchanged, missing, failed, unsupported, needs-OCR.
6. Repeat whenever you add files: download → Refresh Library. The Hub
   never deletes knowledge when a source file disappears — it marks it
   missing and lets you decide.

Tip: in the TeraBox desktop app you can mark `/ca-data/hub-inbox/` for
offline sync, so the files are always on your laptop before you refresh.

## Direction 2: Hub → Terabox (backups live in the cloud)

1. In the Hub: **Settings → Backup** → creates a timestamped backup ZIP
   (database + documents index). The Hub verifies it by test-restoring
   automatically.
2. Upload that ZIP to `/ca-data/hub-backups/` in Terabox (drag-drop in
   the desktop app or web).
3. Do this weekly, or before exams. If your laptop ever dies, you
   reinstall the Hub anywhere and restore from that ZIP.

Optional: point the TeraBox desktop app's sync at the Hub's data folder
(`%LOCALAPPDATA%\CA Knowledge Hub`) for continuous backup — but keep the
manual weekly ZIP as the restore-tested copy.

## Rules

- **Never put client data on Terabox** — study material and your own
  notes only. During articleship, client work stays on the firm's
  systems. (This is in the spec, §11.)
- Terabox free tier: 1 TB storage, 4 GB max per file, share links expire
  after 7 days — fine for this workflow since nothing here depends on
  share links.
- You never need to give anyone your Terabox login for this setup —
  the whole connection is files you move yourself.
