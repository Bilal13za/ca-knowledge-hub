"""Recon module UI pages (Phase 5).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

KINDS = ["bank", "supplier", "customer", "gl", "inventory", "payroll",
         "tax", "other"]


def _load_uploaded(uploaded):
    """Write an uploaded file to temp and load it with the workbench."""
    from . import workbench as wb

    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in (".csv", ".xlsx", ".xls"):
        raise ValueError(f"Unsupported file type '{suffix}'. Use CSV or XLSX.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name
    df = wb.load_table(tmp_path)
    sheets = None
    if suffix in (".xlsx", ".xls"):
        sheets = wb.sheet_names(tmp_path)
    return df, sheets, tmp_path


def _column_map_form(st, df, prefix, default_id=None, default_amount=None):
    cols = [c for c in df.columns if c != "_src_row"]
    def pick(label, default):
        idx = cols.index(default) if default in cols else 0
        return st.selectbox(f"{label} ({prefix})", cols, index=idx,
                            key=f"{prefix}_{label}")
    from .workbench import ColumnMap
    return ColumnMap(
        id=pick("ID column", default_id),
        amount=pick("Amount column", default_amount),
        date=pick("Date column (optional)", None),
        description=pick("Description column (optional)", None),
    )


def render_reconcile(ctx):
    """New reconciliation run."""
    import streamlit as st
    from . import workbench as wb
    from . import store

    st.header("New Reconciliation")
    conn = ctx["conn"]
    name = st.text_input("Run name", placeholder="e.g. Jan-26 bank rec")
    kind = st.selectbox("Reconciliation type", KINDS)
    c1, c2 = st.columns(2)
    up_a = c1.file_uploader("Dataset A (e.g. bank statement)", type=["csv", "xlsx", "xls"])
    up_b = c2.file_uploader("Dataset B (e.g. cash book)", type=["csv", "xlsx", "xls"])
    label_a = c1.text_input("Label A", value="A")
    label_b = c2.text_input("Label B", value="B")

    if up_a and up_b:
        df_a, _, _ = _load_uploaded(up_a)
        df_b, _, _ = _load_uploaded(up_b)
        st.write(f"A: {len(df_a)} rows · B: {len(df_b)} rows")
        m1, m2 = st.columns(2)
        with m1:
            st.subheader(f"Map {label_a}")
            map_a = _column_map_form(st, df_a, "A")
        with m2:
            st.subheader(f"Map {label_b}")
            map_b = _column_map_form(st, df_b, "B")
        tol = st.number_input("Amount tolerance", value=0.01, min_value=0.0,
                              step=0.01)

        if st.button("Run reconciliation", type="primary"):
            result = wb.reconcile(df_a, df_b, map_a, map_b,
                                  amount_tolerance=tol,
                                  label_a=label_a, label_b=label_b)
            s = result["summary"]
            st.subheader("Summary")
            st.json(s)
            if not name:
                st.error("Give the run a name to save it.")
                return
            run_id = store.create_run(
                conn, name=name, kind=kind, label_a=label_a, label_b=label_b,
                mapping={"a": map_a.__dict__, "b": map_b.__dict__,
                         "amount_tolerance": tol})
            store.save_dataset(conn, run_id, "a", df_a, up_a.name)
            store.save_dataset(conn, run_id, "b", df_b, up_b.name)
            n = store.save_reconcile_result(conn, run_id, result)
            st.success(f"Run #{run_id} saved with {n} findings.")
            with st.expander("Findings"):
                for f in store.get_run(conn, run_id)["findings"]:
                    st.write(f"**[{f['severity']}]** {f['message']}")


def render_validate(ctx):
    """Single-file validation + duplicate check."""
    import streamlit as st
    from . import workbench as wb
    from .workbench import ValidationRules
    from . import store

    st.header("Validate a File")
    conn = ctx["conn"]
    up = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx", "xls"])
    if not up:
        return
    df, _, _ = _load_uploaded(up)
    cols = [c for c in df.columns if c != "_src_row"]
    st.write(f"{len(df)} rows · columns: {', '.join(cols)}")
    required = st.multiselect("Required columns", cols)
    dates = st.multiselect("Date columns", cols)
    amounts = st.multiselect("Amount columns", cols)
    dup_cols = st.multiselect("Duplicate-check key columns", cols)
    name = st.text_input("Run name", placeholder="e.g. AP ledger validation")

    if st.button("Run checks", type="primary"):
        rules = ValidationRules(required_columns=required,
                                date_columns=dates, amount_columns=amounts)
        findings = wb.validate_table(df, rules, name=up.name)
        if dup_cols:
            findings += wb.find_duplicates(df, dup_cols)
        st.write(f"{len(findings)} findings")
        for f in findings[:50]:
            st.write(f"**[{f.severity}]** {f.message}")
        if name and st.button("Save as run"):
            run_id = store.create_run(conn, name=name, kind="other",
                                      label_a=up.name)
            store.save_dataset(conn, run_id, "a", df, up.name)
            store.save_findings(conn, run_id, findings)
            st.success(f"Run #{run_id} saved.")


def render_history(ctx):
    """Run history, resolutions, exports."""
    import streamlit as st
    from . import store

    st.header("Reconciliation Runs")
    conn = ctx["conn"]
    runs = store.list_runs(conn)
    if not runs:
        st.info("No runs yet.")
        return
    for r in runs:
        with st.expander(f"#{r['id']}: {r['name']} ({r['kind']}) — "
                         f"{r['open_count']} open / {r['finding_count']} findings"):
            detail = store.get_run(conn, r["id"])
            st.json(detail["summary"])
            for f in detail["findings"]:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**[{f['severity']}]** {f['message']} "
                         f"({'open' if f['status'] == 'open' else f['status']})")
                if f["status"] == "open":
                    with c2.popover("Resolve"):
                        note = st.text_area("Resolution note",
                                            key=f"note_{f['id']}")
                        if st.button("Mark resolved", key=f"res_{f['id']}"):
                            if not note.strip():
                                st.error("A resolution note is required.")
                            else:
                                store.resolve_finding(conn, f["id"], note)
                                st.rerun()
                elif f["resolution_note"]:
                    st.caption(f"Resolution: {f['resolution_note']}")
            if st.button("Export findings (XLSX)", key=f"exp_{r['id']}"):
                import tempfile
                path = Path(tempfile.gettempdir()) / f"recon_run_{r['id']}.xlsx"
                store.export_findings(conn, r["id"], path)
                with open(path, "rb") as fh:
                    st.download_button("Download", fh.read(),
                                       file_name=path.name,
                                       key=f"dl_{r['id']}")


def register_pages():
    return [
        {"id": "recon_new", "title": "New Reconciliation",
         "render": render_reconcile, "modes": ["practice", "professional"]},
        {"id": "recon_validate", "title": "Validate a File",
         "render": render_validate, "modes": ["practice", "professional"]},
        {"id": "recon_history", "title": "Run History",
         "render": render_history, "modes": ["practice", "professional"]},
    ]
