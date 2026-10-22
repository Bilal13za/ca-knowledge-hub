# Module template

Copy this directory to `modules/<your_name>/` and adapt:

1. Rename the directory to your module name (lowercase letters, digits,
   underscores only).
2. Edit `module.json`: set `name` (must match the directory), `title`,
   `version`, `description`; declare `search_categories`, `ui_entry_points`,
   `extension_schema`, `dependencies`.
3. Implement `ui.py:register_pages()` (see the example inside).
4. Add seed data and tests under `hub/tests/test_<your_name>.py`.
5. Register the module in the database (`modules` table) on first run via
   your module's `seed.py`, or let the core auto-register discovered
   manifests (Phase 1C).

See `MODULE_DEVELOPMENT_GUIDE.md` at the project root for the full contract.
