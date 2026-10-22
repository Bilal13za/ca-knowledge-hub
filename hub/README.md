# CA Knowledge Hub — application source

Local-first, offline, deterministic knowledge and professional-practice
system. SQLite + FTS5. No generative AI in the core.

```
hub/
  app.py                 # UI entry point (lands in Phase 1C)
  hubcore/               # Layer 2 services
    db.py                # connections, integrity checks
    migrations.py        # versioned migration framework
    migrations/001_initial.sql
    registry.py          # module discovery + manifest validation
    storage.py           # StorageProvider interface + LocalFolderProvider
    export.py            # JSON+CSV+dump+manifest export format
  modules/               # Layer 4 — one directory per module
    _template/           # copy to start a new module (not discovered)
  tests/                 # pytest suite (offline, deterministic)
  requirements.txt       # runtime deps (stdlib-only until Phase 1C)
  requirements-dev.txt   # pytest
  run_windows.bat        # Windows launcher (lands in Phase 1C)
```

Run tests: `python -m pytest tests/ -q` from this directory.
