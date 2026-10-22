"""xlanalysis module UI pages (Phase 6).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path


def _load_uploaded(uploaded):
    import pandas as pd

    suffix = Path(uploaded.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name
    if suffix == ".csv":
        df = pd.read_csv(tmp_path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(tmp_path, dtype=str, engine="openpyxl",
                            keep_default_na=False)
    return df


def _save_run(conn, name, operation, recipe, summary, output_path=None):
    conn.execute(
        """INSERT INTO xla_runs (name, operation, recipe_json, summary_json,
           output_path) VALUES (?,?,?,?,?)""",
        (name, operation, json.dumps(recipe, ensure_ascii=False),
         json.dumps(summary, ensure_ascii=False, default=str),
         str(output_path) if output_path else None))
    conn.commit()


def render_analyze(ctx):
    """Upload -> choose operation -> run -> download workbook."""
    import streamlit as st
    import pandas as pd
    from . import analyze, templates

    st.header("Analyze Data")
    conn = ctx["conn"]
    up = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx", "xls"])
    if not up:
        return
    df = _load_uploaded(up)
    cols = list(df.columns)
    st.write(f"{len(df)} rows · {len(cols)} columns")
    op = st.selectbox("Operation",
                      ["Clean", "Variance analysis", "Group-by summary",
                       "Calculated column", "Exception report"])
    name = st.text_input("Run name", placeholder="e.g. Jan-26 budget variance")

    if op == "Clean":
        if st.button("Run cleaning", type="primary"):
            cleaned, log = analyze.clean_frame(df)
            st.write(f"{len(log)} change groups logged")
            st.json(log)
            st.dataframe(cleaned.head(20))
            _save_run(conn, name or "clean", "clean",
                      {"file": up.name}, {"changes": len(log), "rows": len(cleaned)})

    elif op == "Variance analysis":
        actual = st.selectbox("Actual column", cols, key="v_actual")
        compare = st.selectbox("Compare column (budget/prior)", cols, key="v_compare")
        group = st.selectbox("Group column (optional)", [""] + cols)
        tp = st.number_input("Threshold %", value=0.10, min_value=0.0, step=0.01)
        ta = st.number_input("Threshold absolute", value=0.0, min_value=0.0, step=1.0)
        if st.button("Run variance", type="primary"):
            res = analyze.variance_analysis(
                df, actual_col=actual, compare_col=compare,
                group_col=group or None, threshold_pct=tp, threshold_abs=ta)
            st.json(res["totals"])
            st.write(f"{res['flagged_count']} flagged rows")
            st.dataframe(pd.DataFrame(res["rows"]).head(50))
            path = Path(tempfile.gettempdir()) / "variance_report.xlsx"
            templates.variance_report_wb(res, name or "Variance report", path)
            with open(path, "rb") as fh:
                st.download_button("Download workbook", fh.read(),
                                   file_name="variance_report.xlsx")
            _save_run(conn, name or "variance", "variance",
                      {"actual": actual, "compare": compare,
                       "threshold_pct": tp, "threshold_abs": ta},
                      res["totals"], path)

    elif op == "Group-by summary":
        by = st.multiselect("Group by", cols)
        agg_col = st.selectbox("Aggregate column", cols)
        aggs = st.multiselect("Aggregations", ["sum", "mean", "count", "min", "max"],
                              default=["sum"])
        if st.button("Run summary", type="primary") and by and aggs:
            out = analyze.summarize(df, by=by, aggregations={agg_col: aggs})
            st.dataframe(out)
            path = Path(tempfile.gettempdir()) / "summary.xlsx"
            templates.summary_wb(out, name or "Summary", path)
            with open(path, "rb") as fh:
                st.download_button("Download workbook", fh.read(),
                                   file_name="summary.xlsx")
            _save_run(conn, name or "summary", "summary",
                      {"by": by, "aggregations": {agg_col: aggs}},
                      {"groups": len(out)}, path)

    elif op == "Calculated column":
        new_col = st.text_input("New column name", placeholder="gross_margin")
        formula = st.text_input("Formula (column names + arithmetic)",
                                placeholder="(revenue - cogs) / revenue")
        st.caption("Allowed: + - * / % **, parentheses, abs/min/max/round, "
                   "column names. Nothing else — no eval().")
        if st.button("Add column", type="primary") and new_col and formula:
            try:
                out, recipe = analyze.add_calculated_column(df, new_col, formula)
            except ValueError as exc:
                st.error(str(exc))
                return
            st.dataframe(out[[new_col]].head(20))
            st.json(recipe)
            _save_run(conn, name or "calculated", "calculated", recipe,
                      {"rows": len(out)})

    elif op == "Exception report":
        col = st.selectbox("Column", cols, key="e_col")
        op_ = st.selectbox("Condition",
                           ["gt", "gte", "lt", "lte", "eq", "ne", "blank",
                            "not_blank"])
        val = st.text_input("Value (not needed for blank/not_blank)")
        label = st.text_input("Rule label", placeholder="e.g. Negative revenue")
        if st.button("Run exceptions", type="primary"):
            try:
                value = float(val) if val.strip() else None
            except ValueError:
                st.error("Value must be numeric for comparison ops.")
                return
            rules = [{"column": col, "op": op_, "value": value,
                      "label": label or f"{col} {op_} {val}",
                      "severity": "warning"}]
            findings = analyze.exception_report(df, rules)
            st.write(f"{len(findings)} exceptions")
            st.dataframe(pd.DataFrame(findings).head(50) if findings
                         else pd.DataFrame())
            path = Path(tempfile.gettempdir()) / "exceptions.xlsx"
            templates.findings_wb(findings, name or "Exceptions", path)
            with open(path, "rb") as fh:
                st.download_button("Download workbook", fh.read(),
                                   file_name="exceptions.xlsx")
            _save_run(conn, name or "exceptions", "exceptions",
                      {"rules": rules}, {"exceptions": len(findings)}, path)


def render_history(ctx):
    """Saved analysis runs with their recipes (reproducibility)."""
    import streamlit as st

    st.header("Analysis Runs")
    conn = ctx["conn"]
    runs = [dict(r) for r in conn.execute(
        "SELECT * FROM xla_runs ORDER BY id DESC")]
    if not runs:
        st.info("No runs yet.")
        return
    for r in runs:
        with st.expander(f"#{r['id']}: {r['name']} ({r['operation']})"):
            st.write("**Recipe (reproducible):**")
            st.json(json.loads(r["recipe_json"]))
            st.write("**Summary:**")
            st.json(json.loads(r["summary_json"]))
            if r["output_path"]:
                st.caption(f"Workbook: {r['output_path']}")


def register_pages():
    return [
        {"id": "xla_analyze", "title": "Analyze Data",
         "render": render_analyze, "modes": ["practice", "professional"]},
        {"id": "xla_history", "title": "Run History",
         "render": render_history, "modes": ["practice", "professional"]},
    ]
