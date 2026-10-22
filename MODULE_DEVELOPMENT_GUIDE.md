# Module Development Guide

**Status:** Phase 1A (v1). Extended as new module kinds are added.

## 1. What a module is

A directory `hub/modules/<name>/` containing at minimum a `module.json`
manifest. Directories starting with `_` (e.g. `_template`) are never
discovered. The manifest `name` must equal the directory name
(lowercase letters, digits, underscores).

## 2. Manifest reference (`module.json`)

```jsonc
{
  "name": "audit",                 // required, ^[a-z0-9_]+$, == directory
  "title": "Audit Risk Library",   // required
  "version": "1.0.0",              // required, MAJOR.MINOR.PATCH
  "description": "...",            // required
  "enabled": true,                 // optional, default true
  "data_requirements": ["..."],    // optional: tables/seeds the module needs
  "search_categories": ["audit"],  // optional: chips in global search
  "ui_entry_points": {             // optional
    "pages": "modules.audit.ui:register_pages"
  },
  "extension_schema": {            // optional: JSON Schema for extension_json
    "type": "object",
    "properties": { "assertions": {"type": "array", "items": {"type": "string"}} }
  },
  "extension_tables": [],          // optional: ["audit_ext"] if using joined tables
  "dependencies": [],              // optional: other module names
  "tests": "hub/tests/test_audit.py",
  "sources_required": ["ISA ..."]  // optional: documentation hint only
}
```

Invalid manifests are **skipped with a warning** — they never break
discovery or other modules (`registry.discover_with_warnings`).

## 3. UI entry-point contract

`ui_entry_points.pages` is `"dotted.path:callable"`. The callable takes no
arguments and returns a list of page dicts:

```python
{
  "id": "audit_home",        # unique page id
  "title": "Audit Library",   # shown in navigation
  "render": render_fn,        # callable(ctx) -> None
  "modes": ["study", "practice", "professional"],  # subset
}
```

`ctx` is a dict with at least `{"conn": sqlite3.Connection,
"workspace": dict | None, "mode": str}`. Import Streamlit (or the chosen
stack) **inside** render functions so `hubcore` stays UI-agnostic.
Pages must degrade gracefully when their module's data is absent.

## 4. Data: the one extension pattern

1. Put shared fields in `knowledge_records` (see DATABASE_SCHEMA.md).
2. Module-specific fields → `extension_json`, validated against your
   `extension_schema` at write time.
3. Frequently-queried fields → `<name>_ext` table (`record_id` FK),
   listed in `extension_tables`.
4. Cross-module links → `record_relations` rows with a `rel_type`
   (e.g. `has-tax-implication`, `tested-by`). Creating a relationship is
   a no-code row insert — never requires a code change.

## 5. Knowledge updates without code

Routine updates are data operations, not software changes:

- New/changed rule → insert a new `rules`/`knowledge_records` row with an
  incremented `version`; mark the old row `superseded` (link
  `superseded_by`); append a `revision_history` row with reason + source.
- New document → drop it in the inbox folder → Refresh Library.
- New checklist → `knowledge_records` rows with `topic='checklist'`.

## 6. No-code module example

A module can be **only** `module.json` + seed JSON + `ui.py` with two
pages (browser + search). See `hub/modules/_template/`. No Python beyond
`register_pages()` is required.

## 7. Checklist before a module ships

- [ ] Manifest validates (`registry.validate_manifest`).
- [ ] `register_pages()` returns well-formed pages; renders with empty DB.
- [ ] Seed data has `source_id` + `verification_status` on every
      technical record; nothing invented (see SOURCE_VERIFICATION_POLICY.md).
- [ ] Tests cover: seed load, one happy-path workflow, one failure path.
- [ ] `CHANGELOG.md` updated; `DATABASE_SCHEMA.md` updated if tables added.
