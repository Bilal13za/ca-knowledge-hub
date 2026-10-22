"""CA Knowledge Hub — Streamlit UI shell (Phase 1C).

Offline-first, local-only (localhost). The shell discovers module pages
from manifests (hubcore.registry) and renders them with no core edits.
All data lives in hub/data/hub.db (SQLite + FTS5).
"""
from __future__ import annotations

import io
import json
import zipfile
from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from hubcore import (
    backup as backupmod,
    bootstrap,
    db as dbmod,
    documents as docmod,
    export as exportmod,
    knowledge,
    registry,
    search as searchmod,
    storage,
    workspaces,
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "hub.db"
INBOX_DIR = DATA_DIR / "inbox"
BACKUP_DIR = DATA_DIR / "backups"
MODULES_DIR = APP_DIR / "modules"
APP_VERSION = "0.3.0"
MODES = ["study", "practice", "professional"]

STATUS_COLORS = {
    "verified": "green",
    "extracted_unverified": "orange",
    "user_note": "blue",
    "interpretation": "violet",
    "superseded": "gray",
}


# ---------------------------------------------------------------- boot

@contextmanager
def open_conn():
    """Fresh SQLite connection per use (safe with Streamlit reruns)."""
    conn = dbmod.get_connection(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_first_run() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with open_conn() as conn:
        dbmod.initialise(conn)
        bootstrap.sync_modules(conn, MODULES_DIR)
        if not workspaces.list_workspaces(conn):
            workspaces.create_workspace(conn, "General", ["core"])
        # First-run content seed (idempotent; skipped on later runs).
        import seed_all
        seed_all.ensure_seeded(conn, MODULES_DIR)


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "gray")
    return f":{color}[{status}]"


# ---------------------------------------------------------------- nav (pure, tested)

def module_page_nav_items(modules_info: list[dict], mode: str) -> list[dict]:
    """Convert discovered module pages into nav entries for one mode.

    Pure function (no Streamlit) so it is unit-testable.
    Returns [{"label", "module", "page_id", "page"}].
    """
    items: list[dict] = []
    for mod in modules_info:
        for page in mod.get("pages", []):
            if mode in page.get("modes", MODES):
                items.append({
                    "label": f"{mod['title']}: {page['title']}",
                    "module": mod["name"],
                    "page_id": page["id"],
                    "page": page,
                })
    return items


def discover_module_pages() -> list[dict]:
    """Discover enabled modules and load their UI pages (failures isolated)."""
    found, _ = registry.discover_with_warnings(MODULES_DIR)
    result: list[dict] = []
    with open_conn() as conn:
        enabled = {r["name"] for r in bootstrap.enabled_modules(conn)}
    for name, mod in found.items():
        if name not in enabled:
            continue
        try:
            pages = registry.load_ui_pages(mod)
        except (ImportError, AttributeError, ValueError):
            pages = []
        result.append({"name": name, "title": mod.title, "pages": pages})
    return result


# ---------------------------------------------------------------- core pages

def render_dashboard(ctx):
    st.header("Dashboard")
    with open_conn() as conn:
        counts = dbmod.table_counts(conn)
        due = knowledge.due_for_review(conn)
        last_refresh = conn.execute(
            "SELECT value_json FROM settings WHERE key='last_refresh'"
        ).fetchone()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Documents indexed", counts.get("documents", 0))
    c2.metric("Knowledge records", counts.get("knowledge_records", 0))
    c3.metric("Modules enabled", counts.get("modules", 0))
    c4.metric("Review due (30d)", len(due), delta_color="inverse")
    ws = ctx["workspace"]
    st.subheader("Active workspace")
    if ws:
        st.write(f"**{ws['name']}** — modules: {', '.join(ws['modules']) or 'none'}")
    else:
        st.info("No workspace selected. Create one in Workspaces.")
    if last_refresh:
        rep = json.loads(last_refresh[0])
        st.caption(f"Last library refresh: {rep.get('finished_at', '?')} — "
                   f"{len(rep.get('new', []))} new, {len(rep.get('updated', []))} updated, "
                   f"{len(rep.get('failed', []))} failed.")
    if due:
        with st.expander(f"⚠️ {len(due)} records due for review"):
            for r in due[:20]:
                st.write(f"{status_badge(r['verification_status'])} **{r['title']}** "
                         f"(`{r['module']}`) — due {r['review_due_date']}")


def render_search(ctx):
    st.header("Global search")
    query = st.text_input("Search knowledge records and documents", key="q")
    with open_conn() as conn:
        cats = searchmod.search_categories(conn)
    ws = ctx["workspace"]
    default_mods = ws["modules"] if ws else []
    modules = st.multiselect("Module filter (empty = active workspace, or all)",
                             options=cats,
                             default=[m for m in default_mods if m in cats])
    scope = modules or (default_mods if default_mods else None)
    if query:
        with open_conn() as conn:
            res = searchmod.global_search(conn, query, modules=scope, limit=30)
        st.subheader(f"Knowledge records ({len(res['records'])})")
        for r in res["records"]:
            with st.expander(f"{status_badge(r['verification_status'])} {r['title']} "
                             f"(`{r['module']}`)"):
                st.markdown(r["snippet"], unsafe_allow_html=True)
                st.caption(f"Topic: {r['topic']} {r['subtopic']} | "
                           f"Source page: {r['source_page'] or '—'}")
        st.subheader(f"Document passages ({len(res['chunks'])})")
        for h in res["chunks"]:
            loc = f"p.{h['page_no']}" if h["page_no"] else (h["sheet_name"] or "")
            st.markdown(f"**{h['filename']}** {loc}")
            st.markdown(h["snippet"], unsafe_allow_html=True)


def render_library(ctx):
    st.header("Document library")
    tab_scan, tab_docs = st.tabs(["Refresh Library", "Documents"])

    with tab_scan:
        with open_conn() as conn:
            row = conn.execute(
                "SELECT value_json FROM settings WHERE key='storage_folder'"
            ).fetchone()
        folder = st.text_input("Source folder (e.g. your TeraBox downloads folder)",
                               value=json.loads(row[0]) if row else "")
        col1, col2 = st.columns(2)
        if col1.button("Save folder"):
            if folder and Path(folder).is_dir():
                with open_conn() as conn:
                    conn.execute(
                        "INSERT INTO settings (key, value_json) VALUES ('storage_folder', ?)"
                        " ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                        (json.dumps(folder),),
                    )
                st.success("Saved.")
            else:
                st.error("That folder does not exist.")
        if col2.button("Scan source folder"):
            if not folder or not Path(folder).is_dir():
                st.error("Save a valid source folder first.")
            else:
                with st.spinner("Scanning..."):
                    provider = storage.get_provider("local_folder", {"folder": folder})
                    staged = provider.scan()
                st.session_state["staged"] = [
                    {"relative": s.relative, "size": s.size} for s in staged
                ]
                st.success(f"Found {len(staged)} files.")
        staged = st.session_state.get("staged", [])
        if staged:
            st.write(f"{len(staged)} files staged.")
            if st.button(f"Fetch {len(staged)} files to inbox"):
                provider = storage.get_provider("local_folder", {"folder": folder})
                with st.spinner("Copying..."):
                    for s in provider.scan():
                        provider.fetch(s, INBOX_DIR)
                st.success("Fetched. Now run Refresh Library.")
        if st.button("🔄 Refresh Library", type="primary"):
            with open_conn() as conn, st.spinner("Extracting and indexing..."):
                report = docmod.refresh_library(conn, INBOX_DIR)
            st.success(f"Done: {len(report['new'])} new, {len(report['updated'])} updated, "
                       f"{len(report['unchanged'])} unchanged.")
            with st.expander("Processing report", expanded=True):
                for key in ("new", "updated", "unchanged", "missing",
                            "failed", "unsupported", "ocr_needed"):
                    items = report.get(key, [])
                    st.write(f"**{key}** ({len(items)}): "
                             f"{', '.join(items[:20])}" + ("…" if len(items) > 20 else ""))

    with tab_docs:
        filt = st.selectbox("Status filter",
                            ["all", "indexed", "failed", "unsupported",
                             "ocr_needed", "missing"])
        with open_conn() as conn:
            docs = docmod.list_documents(
                conn, status=None if filt == "all" else filt)
        st.write(f"{len(docs)} documents")
        for d in docs[:200]:
            st.write(f"{status_badge(d['status'])} **{d['filename']}** "
                     f"({d['file_type']}, {d['file_size'] // 1024} KB)")


def _record_form_defaults():
    return {"module": "core", "topic": "", "subtopic": "", "title": "",
            "description": "", "keywords": "", "content": "",
            "verification_status": "user_note", "source_page": "",
            "review_due_date": ""}


def render_knowledge(ctx):
    st.header("Knowledge records")
    ws = ctx["workspace"]
    scope = ws["modules"] if ws else None
    with open_conn() as conn:
        cats = searchmod.search_categories(conn)
    col1, col2 = st.columns(2)
    mod_filter = col1.selectbox("Module", ["(workspace)"] + cats)
    status_filter = col2.selectbox("Verification", ["any"] + list(knowledge.VERIFICATION_STATUSES))
    with open_conn() as conn:
        records = knowledge.list_records(
            conn,
            module=None if mod_filter == "(workspace)" else mod_filter,
            verification_status=None if status_filter == "any" else status_filter,
            limit=200,
        )
        if mod_filter == "(workspace)" and scope:
            records = [r for r in records if r["module"] in scope]
    st.write(f"{len(records)} records")
    labels = [f"{r['id']}: {r['title']} (`{r['module']}`)" for r in records]
    choice = st.selectbox("Open record", ["—"] + labels)
    if choice != "—":
        rid = int(choice.split(":")[0])
        _render_record_detail(rid, ctx)

    with st.expander("＋ New record"):
        with st.form("new_record"):
            d = _record_form_defaults()
            d["title"] = st.text_input("Title")
            d["module"] = st.text_input("Module", value="core")
            d["topic"] = st.text_input("Topic")
            d["verification_status"] = st.selectbox(
                "Verification status", list(knowledge.VERIFICATION_STATUSES))
            d["content"] = st.text_area("Content", height=150)
            d["keywords"] = st.text_input("Keywords (comma-separated)")
            d["source_page"] = st.text_input("Source page / section")
            d["review_due_date"] = st.text_input("Review due date (YYYY-MM-DD)")
            if st.form_submit_button("Create"):
                if not d["title"]:
                    st.error("Title is required.")
                else:
                    with open_conn() as conn:
                        rid = knowledge.create_record(conn, d)
                    st.success(f"Created record {rid}.")
                    st.rerun()


def _render_record_detail(rid: int, ctx):
    with open_conn() as conn:
        rec = knowledge.get_record(conn, rid)
        if rec is None:
            st.error("Record not found.")
            return
        rels = knowledge.get_relations(conn, rid)
    st.subheader(rec["title"])
    st.write(f"{status_badge(rec['verification_status'])} `{rec['module']}` / {rec['topic']}")
    st.markdown(rec["content"] or "*No content.*")
    if rec["source_page"]:
        st.caption(f"Source page: {rec['source_page']}")
    # cross-module implication prompts (spec 4B.5)
    ws = ctx["workspace"]
    active = ws["modules"] if ws else []
    with open_conn() as conn:
        others = knowledge.related_in_other_modules(conn, rid, active)
    for o in others:
        st.info(f"🔗 Has **{o['rel_type']}** in module `{o['other_module']}`: "
                f"{o['other_title']} — add `{o['other_module']}` to your workspace "
                f"to explore it.")
    if rels:
        with st.expander(f"Relations ({len(rels)})"):
            for r in rels:
                st.write(f"{r['direction']} · `{r['rel_type']}` → "
                         f"{r['other_title']} (`{r['other_module']}`) — {r['note']}")
    with st.expander("Edit / revise"):
        with st.form(f"edit_{rid}"):
            title = st.text_input("Title", value=rec["title"])
            content = st.text_area("Content", value=rec["content"], height=150)
            status = st.selectbox("Verification status",
                                  list(knowledge.VERIFICATION_STATUSES),
                                  index=list(knowledge.VERIFICATION_STATUSES).index(
                                      rec["verification_status"]))
            reason = st.text_input("Reason for change (required for revision log)")
            c1, c2 = st.columns(2)
            save = c1.form_submit_button("Save (minor edit)")
            revise = c2.form_submit_button("Save as revision")
            if save or revise:
                data = {"title": title, "content": content,
                        "verification_status": status}
                with open_conn() as conn:
                    if revise:
                        if not reason:
                            st.error("A reason is required for a revision.")
                        else:
                            knowledge.revise_record(conn, rid, data, reason=reason)
                            st.success("Revision recorded.")
                            st.rerun()
                    else:
                        knowledge.update_record(conn, rid, data)
                        st.success("Saved.")
                        st.rerun()
    if st.button("Delete record", key=f"del_{rid}"):
        with open_conn() as conn:
            knowledge.delete_record(conn, rid)
        st.success("Deleted (revision history kept).")
        st.rerun()


def render_workspaces(ctx):
    st.header("Workspaces")
    st.caption("A workspace is a named set of modules for the task at hand. "
               "Search and browsing scope to the active workspace.")
    with open_conn() as conn:
        all_ws = workspaces.list_workspaces(conn)
        cats = searchmod.search_categories(conn)
    for ws in all_ws:
        mods = json.loads(ws["module_list_json"])
        col1, col2, col3 = st.columns([3, 2, 1])
        active = st.session_state.get("workspace_id") == ws["id"]
        col1.write(f"{'🟢 ' if active else ''}**{ws['name']}** — {', '.join(mods) or 'no modules'}")
        if col2.button("Switch", key=f"sw_{ws['id']}", disabled=active):
            with open_conn() as conn:
                workspaces.touch_workspace(conn, ws["id"])
            st.session_state["workspace_id"] = ws["id"]
            st.rerun()
        if col3.button("Delete", key=f"delw_{ws['id']}"):
            with open_conn() as conn:
                workspaces.delete_workspace(conn, ws["id"])
            st.rerun()
    with st.expander("＋ New workspace"):
        with st.form("new_ws"):
            name = st.text_input("Name (e.g. Audit + Tax)")
            mods = st.multiselect("Modules", options=cats, default=cats[:1])
            if st.form_submit_button("Create"):
                if not name:
                    st.error("Name is required.")
                else:
                    with open_conn() as conn:
                        wid = workspaces.create_workspace(conn, name, mods)
                    st.session_state["workspace_id"] = wid
                    st.success(f"Workspace '{name}' created and activated.")
                    st.rerun()


def render_sources(ctx):
    st.header("Source register")
    with st.form("new_source"):
        code = st.text_input("Code (unique, e.g. ITA-2025)")
        title = st.text_input("Title")
        kind = st.selectbox("Kind", ["legislation", "standard", "textbook",
                                    "official_guidance", "user", "other"])
        jurisdiction = st.text_input("Jurisdiction", value="Pakistan")
        url = st.text_input("URL / reference")
        if st.form_submit_button("Add source"):
            if not code or not title:
                st.error("Code and title are required.")
            else:
                with open_conn() as conn:
                    try:
                        conn.execute(
                            "INSERT INTO sources (code, title, kind, jurisdiction, url)"
                            " VALUES (?,?,?,?,?)",
                            (code, title, kind, jurisdiction, url),
                        )
                        st.success("Source added.")
                    except Exception as exc:
                        st.error(f"Could not add source: {exc}")
                st.rerun()
    with open_conn() as conn:
        sources = [dict(r) for r in conn.execute("SELECT * FROM sources ORDER BY code")]
    for s in sources:
        st.write(f"**{s['code']}** — {s['title']} ({s['kind']}, {s['jurisdiction']})")


def render_backup(ctx):
    st.header("Backup & export")
    if st.button("💾 Backup now", type="primary"):
        with st.spinner("Backing up and verifying..."):
            with open_conn() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            dest = backupmod.backup_database(DB_PATH, BACKUP_DIR)
            result = backupmod.verify_backup(dest)
        if result["ok"]:
            st.success(f"Backup verified: {dest.name}")
        else:
            st.error(f"Backup FAILED verification: {result['errors']}")
    backups = sorted([p for p in BACKUP_DIR.glob("hub-backup-*") if p.is_dir()],
                     key=lambda p: p.name, reverse=True)
    st.subheader(f"Backups ({len(backups)})")
    for b in backups[:10]:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"**{b.name}**")
        if col2.button("Verify", key=f"v_{b.name}"):
            with st.spinner("Verifying..."):
                res = backupmod.verify_backup(b)
            st.success("OK") if res["ok"] else st.error(str(res["errors"]))
        if col3.button("Restore", key=f"r_{b.name}"):
            st.session_state["restore_candidate"] = str(b)
    cand = st.session_state.get("restore_candidate")
    if cand:
        st.warning(f"Restore from `{Path(cand).name}`? A safety backup of the "
                   f"current database is taken first.")
        if st.button("Confirm restore"):
            try:
                with open_conn() as conn:
                    pass
                pre = backupmod.restore_database(cand, DB_PATH, backup_dir=BACKUP_DIR)
                st.success(f"Restored. Pre-restore safety backup: {pre.name if pre else 'n/a'}")
            except Exception as exc:
                st.error(f"Restore failed: {exc}")
            st.session_state["restore_candidate"] = None

    st.subheader("Export")
    if st.button("Generate export package"):
        with open_conn() as conn, st.spinner("Exporting..."):
            outdir = DATA_DIR / "export"
            manifest = exportmod.export_all(conn, outdir)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in outdir.rglob("*"):
                    if p.is_file():
                        zf.write(p, p.relative_to(outdir))
        st.session_state["export_zip"] = buf.getvalue()
        st.success(f"Export ready: {manifest}")
    if st.session_state.get("export_zip"):
        st.download_button("⬇ Download export ZIP",
                           data=st.session_state["export_zip"],
                           file_name="hub-export.zip", mime="application/zip")


def render_settings(ctx):
    st.header("Settings")
    st.write(f"**App version:** {APP_VERSION}")
    with open_conn() as conn:
        ver = dbmod.migrations.current_version(conn)
        counts = dbmod.table_counts(conn)
    st.write(f"**Database schema version:** {ver}")
    st.write(f"**Database file:** {DB_PATH} "
             f"({DB_PATH.stat().st_size // 1024 if DB_PATH.exists() else 0} KB)")
    st.write(f"**Inbox folder:** {INBOX_DIR}")
    st.write(f"**Storage provider:** Local folder (manual download → inbox). "
             f"No cloud API is used.")
    with st.expander("Table row counts"):
        st.json(counts)


# ---------------------------------------------------------------- main

CORE_PAGES = [
    ("Dashboard", "dashboard", render_dashboard),
    ("Search", "search", render_search),
    ("Library", "library", render_library),
    ("Knowledge", "knowledge", render_knowledge),
    ("Workspaces", "workspaces", render_workspaces),
    ("Sources", "sources", render_sources),
    ("Backup & Export", "backup", render_backup),
    ("Settings", "settings", render_settings),
]


def main():
    st.set_page_config(page_title="CA Knowledge Hub", layout="wide")
    ensure_first_run()

    if "mode" not in st.session_state:
        st.session_state["mode"] = "study"
    if "workspace_id" not in st.session_state:
        with open_conn() as conn:
            ws_list = workspaces.list_workspaces(conn)
            st.session_state["workspace_id"] = ws_list[0]["id"] if ws_list else None

    with open_conn() as conn:
        ws = (workspaces.get_workspace(conn, st.session_state["workspace_id"])
              if st.session_state["workspace_id"] else None)

    st.sidebar.title("CA Knowledge Hub")
    st.sidebar.caption(f"v{APP_VERSION} · offline · local")
    mode = st.sidebar.radio("Mode", MODES,
                              index=MODES.index(st.session_state["mode"]),
                              horizontal=True)
    st.session_state["mode"] = mode

    ws_names, ws_ids = [], []
    with open_conn() as conn:
        for w in workspaces.list_workspaces(conn):
            ws_names.append(w["name"])
            ws_ids.append(w["id"])
    if ws_ids:
        idx = ws_ids.index(st.session_state["workspace_id"]) \
            if st.session_state["workspace_id"] in ws_ids else 0
        chosen = st.sidebar.selectbox("Workspace", ws_names, index=idx)
        st.session_state["workspace_id"] = ws_ids[ws_names.index(chosen)]
        with open_conn() as conn:
            ws = workspaces.get_workspace(conn, st.session_state["workspace_id"])

    ctx = {"workspace": ws, "mode": mode, "data_dir": DATA_DIR,
           "modules_dir": MODULES_DIR}

    # navigation: core pages + discovered module pages for this mode
    nav_labels: list[str] = []
    nav_targets: list[tuple[str, object]] = []
    for label, pid, fn in CORE_PAGES:
        nav_labels.append(label)
        nav_targets.append(("core", fn))
    for item in module_page_nav_items(discover_module_pages(), mode):
        nav_labels.append(item["label"])
        nav_targets.append(("module", item["page"]))

    choice = st.sidebar.radio("Navigate", nav_labels)
    kind, target = nav_targets[nav_labels.index(choice)]
    if kind == "core":
        target(ctx)
    else:
        st.header(target["title"])
        with open_conn() as conn:
            page_ctx = dict(ctx)
            page_ctx["conn"] = conn
            target["render"](page_ctx)


if __name__ == "__main__":
    main()
