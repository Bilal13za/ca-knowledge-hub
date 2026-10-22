"""Financial data analysis: deterministic, offline, pure functions.

Covers the Phase 6 spec: data cleaning (with a full change log — never
silent), variance analysis, group-by summaries, safe calculated columns
(AST-restricted formulas, never eval()), threshold exception reporting,
and reproducible calculation recipes.

"Excel automation" in this module means Python-generated workbooks
(openpyxl) — never VBA/macros; embedded macros are never executed.
"""
from __future__ import annotations

import ast
import operator
from typing import Any

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


def _need_pandas():
    if pd is None:
        raise RuntimeError("The 'pandas' package is required.")


def _to_number_strict(value) -> float | None:
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "nan", "None"):
            return None
        return float(s)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------- cleaning

def clean_frame(df: "pd.DataFrame", *, name: str = "dataset") -> tuple:
    """Clean a frame; return (cleaned_df, change_log).

    - strips whitespace in object cells and column names
    - drops fully-blank rows
    - normalises parseable dates to YYYY-MM-DD (unparseable kept, flagged)
    Every change is logged; nothing is silently altered.
    """
    _need_pandas()
    log: list[dict] = []
    out = df.copy()

    # column names
    renamed = {c: str(c).strip() for c in out.columns}
    if any(k != v for k, v in renamed.items()):
        changed = [k for k, v in renamed.items() if k != v]
        log.append({"action": "rename_columns", "columns": changed,
                    "detail": "stripped whitespace from column names"})
    out = out.rename(columns=renamed)

    # cell whitespace
    for col in out.columns:
        # pandas 3 infers text columns as `str` dtype; pandas 2 used `object`.
        # Accept both so whitespace stripping works on either version.
        if isinstance(out[col].dtype, pd.StringDtype) or out[col].dtype == object:
            before = out[col].astype(str)
            after = before.str.strip()
            n = int((before != after).sum())
            if n:
                log.append({"action": "strip_whitespace", "column": col,
                            "rows_affected": n})
            out[col] = after

    # fully blank rows
    blank_mask = out.apply(
        lambda r: all(str(v).strip() in ("", "nan", "None") for v in r), axis=1)
    n_blank = int(blank_mask.sum())
    if n_blank:
        log.append({"action": "drop_blank_rows", "rows_affected": n_blank,
                    "detail": f"dropped source rows "
                              f"{sorted(out.index[blank_mask].tolist())}"})
    out = out[~blank_mask].reset_index(drop=True)

    # date normalisation (parseable only)
    import warnings

    for col in out.columns:
        vals = out[col].astype(str)
        stripped = vals.str.strip()
        # Never treat a plain number as a date: "1000" parses as year 1000
        # on some pandas versions, which would mangle numeric columns.
        nonblank = stripped[stripped != ""]
        if len(nonblank) and bool(
            nonblank.str.fullmatch(r"[+-]?[\d\s,._]+").all()
        ):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(vals, errors="coerce", dayfirst=True)
        n_parseable = int(parsed.notna().sum())
        n_nonblank = int((vals.str.strip() != "").sum())
        if n_nonblank >= 3 and n_parseable / max(n_nonblank, 1) >= 0.8:
            new_vals = vals.where(parsed.isna(),
                                  parsed.dt.strftime("%Y-%m-%d"))
            n_changed = int((vals != new_vals).sum())
            if n_changed:
                log.append({"action": "normalise_dates", "column": col,
                            "rows_affected": n_changed,
                            "detail": "parseable dates -> YYYY-MM-DD; "
                                      "unparseable left untouched"})
            out[col] = new_vals

    return out, log


# ---------------------------------------------------------------- variance

def variance_analysis(df: "pd.DataFrame", *, actual_col: str,
                      compare_col: str, label_actual: str = "Actual",
                      label_compare: str = "Budget",
                      group_col: str | None = None,
                      threshold_pct: float = 0.10,
                      threshold_abs: float = 0.0) -> dict:
    """Row-level variance: actual vs compare, with threshold flagging.

    Flags rows where |variance_pct| >= threshold_pct AND
    |variance| >= threshold_abs. Thresholds are explicit parameters —
    nothing is hard-coded as "material".
    """
    _need_pandas()
    for c in (actual_col, compare_col):
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not in dataset.")
    a = df[actual_col].map(_to_number_strict)
    b = df[compare_col].map(_to_number_strict)
    variance = a - b
    with_pct = b.abs() > 0
    # Built element-wise (not by masked assignment into an object-dtype
    # Series) so the result is identical on pandas 2 and pandas 3.
    ratio = variance / b.abs()
    variance_pct = pd.Series(
        [None if (not w or pd.isna(r)) else float(r)
         for w, r in zip(with_pct.tolist(), ratio.tolist())],
        dtype=object,
    )

    rows = []
    for i in df.index:
        av, bv = a[i], b[i]
        vv = variance[i]
        pv = variance_pct[i]
        flagged = (
            vv is not None and pv is not None
            and abs(vv) >= threshold_abs
            and abs(pv) >= threshold_pct
        )
        rows.append({
            "row": int(i),
            "group": df[group_col][i] if group_col and group_col in df.columns else "",
            label_actual: av, label_compare: bv,
            "variance": None if vv is None or pd.isna(vv) else round(float(vv), 2),
            "variance_pct": None if pv is None or pd.isna(pv) else round(float(pv), 4),
            "flagged": bool(flagged),
        })
    total_a = float(a.sum(skipna=True))
    total_b = float(b.sum(skipna=True))
    total_v = total_a - total_b
    return {
        "rows": rows,
        "flagged_count": sum(1 for r in rows if r["flagged"]),
        "totals": {label_actual: round(total_a, 2),
                   label_compare: round(total_b, 2),
                   "variance": round(total_v, 2),
                   "variance_pct": round(total_v / abs(total_b), 4)
                   if total_b else None},
        "params": {"actual_col": actual_col, "compare_col": compare_col,
                   "label_actual": label_actual, "label_compare": label_compare,
                   "threshold_pct": threshold_pct,
                   "threshold_abs": threshold_abs},
    }


# ---------------------------------------------------------------- summary

_AGGREGATIONS = {"sum", "mean", "count", "min", "max", "nunique"}


def summarize(df: "pd.DataFrame", *, by: list[str],
              aggregations: dict[str, list[str]]) -> "pd.DataFrame":
    """Group-by summary. aggregations: {column: [agg, ...]}."""
    _need_pandas()
    for c in by:
        if c not in df.columns:
            raise ValueError(f"Group column '{c}' not in dataset.")
    agg_spec: dict[str, list] = {}
    for col, aggs in aggregations.items():
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not in dataset.")
        for agg in aggs:
            if agg not in _AGGREGATIONS:
                raise ValueError(f"Unknown aggregation '{agg}'.")
            if agg in ("sum", "mean", "min", "max"):
                agg_spec.setdefault(col, []).append(
                    lambda s, _a=agg: getattr(
                        pd.to_numeric(s.map(_to_number_strict),
                                      errors="coerce"), _a)(skipna=True))
            elif agg == "count":
                agg_spec.setdefault(col, []).append("count")
            else:  # nunique
                agg_spec.setdefault(col, []).append("nunique")
    grouped = df.groupby(list(by), dropna=False)
    parts = []
    for col, funcs in agg_spec.items():
        for fn, agg_name in zip(funcs, aggregations[col]):
            res = grouped[col].agg(fn)
            res.name = f"{col}__{agg_name}"
            parts.append(res)
    out = pd.concat(parts, axis=1).reset_index()
    return out


# ------------------------------------------------------- calculated columns

_ALLOWED_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub,
                   ast.Mult: operator.mul, ast.Div: operator.truediv,
                   ast.Mod: operator.mod, ast.Pow: operator.pow}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_ALLOWED_FUNCS = {"abs": abs, "min": min, "max": max, "round": round}


def _eval_node(node: ast.AST, env: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ValueError(f"Unknown column '{node.id}' in formula.")
        v = env[node.id]
        if v is None:
            raise ValueError(f"Blank value in column '{node.id}'.")
        return float(v)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](
            _eval_node(node.left, env), _eval_node(node.right, env))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_node(node.operand, env))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in _ALLOWED_FUNCS and not node.keywords:
        return _ALLOWED_FUNCS[node.func.id](
            *[_eval_node(a, env) for a in node.args])
    raise ValueError(f"Formula element not allowed: {ast.dump(node)[:80]}")


def add_calculated_column(df: "pd.DataFrame", name: str,
                          formula: str) -> tuple:
    """Add a column computed from a safe formula over existing columns.

    Returns (new_df, recipe_entry). Rejects anything outside arithmetic,
    whitelisted functions and column names — never eval().
    """
    _need_pandas()
    if not name or name in df.columns:
        raise ValueError(f"Invalid or duplicate column name '{name}'.")
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula: {exc}") from exc
    cols_used = sorted({n.id for n in ast.walk(tree)
                        if isinstance(n, ast.Name)
                        and n.id not in _ALLOWED_FUNCS})
    for c in cols_used:
        if c not in df.columns:
            raise ValueError(f"Unknown column '{c}' in formula.")
    numeric = {c: df[c].map(_to_number_strict) for c in cols_used}
    values = []
    for i in df.index:
        env = {c: numeric[c][i] for c in cols_used}
        try:
            values.append(_eval_node(tree, env))
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"Row {int(i)}: {exc}") from exc
    out = df.copy()
    out[name] = [round(v, 4) for v in values]
    recipe = {"column": name, "formula": formula, "inputs": cols_used}
    return out, recipe


# ---------------------------------------------------------------- exceptions

def exception_report(df: "pd.DataFrame",
                     rules: list[dict]) -> list[dict]:
    """Threshold exception reporting.

    Each rule: {column, op, value, label, severity}. ops: gt, gte, lt,
    lte, eq, ne, between, outside, blank, not_blank.
    Returns [{rule_label, severity, row, column, value, message}].
    """
    _need_pandas()
    out = []
    for rule in rules:
        col = rule["column"]
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not in dataset.")
        op, value = rule["op"], rule.get("value")
        label = rule.get("label", f"{col} {op} {value}")
        severity = rule.get("severity", "warning")
        nums = df[col].map(_to_number_strict)
        raw = df[col].astype(str)
        for i in df.index:
            hit, disp = False, raw[i]
            if op == "blank":
                hit = raw[i].strip() == ""
            elif op == "not_blank":
                hit = raw[i].strip() != ""
            else:
                v = nums[i]
                if v is None:
                    continue
                if op == "gt":
                    hit = v > value
                elif op == "gte":
                    hit = v >= value
                elif op == "lt":
                    hit = v < value
                elif op == "lte":
                    hit = v <= value
                elif op == "eq":
                    hit = v == value
                elif op == "ne":
                    hit = v != value
                elif op == "between":
                    hit = value[0] <= v <= value[1]
                elif op == "outside":
                    hit = v < value[0] or v > value[1]
                else:
                    raise ValueError(f"Unknown op '{op}'.")
                disp = v
            if hit:
                out.append({"rule": label, "severity": severity,
                            "row": int(i), "column": col, "value": disp,
                            "message": f"{label}: row {int(i)} {col}={disp}"})
    return out
