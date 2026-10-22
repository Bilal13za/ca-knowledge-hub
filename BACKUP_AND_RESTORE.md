# Backup and Restore

**Status:** Phase 1A — full procedure lands in Phase 1C with `hubcore/backup.py`.
This page records the policy now so Phase 1C implements against it.

## Policy

- Backups are full SQLite file copies + the `export_all()` package
  (JSON + CSV + dump + manifest), timestamped, with rotation (keep last 10).
- Every backup is **verified**: restore into a temporary database,
  run `PRAGMA integrity_check`, compare table counts against the manifest.
  An unverified backup is reported as failed.
- Restore never overwrites the live database without first taking a
  pre-restore backup.
- Personal study data and (later) professional data are separable:
  backups are per-database-file; the tax knowledge/working split decision
  (Phase 1A review) determines file granularity.

## Honest limitations

- Local SQLite files and ZIP backups are **not encrypted by default**;
  OS-level file protection applies. Optional SQLCipher-based encryption
  is a future module, not promised now.
- Cloud copies (e.g. TeraBox) are manual until a storage provider with
  sync is added; the Hub never uploads without explicit user action.
