"""corpfn module UI pages (Phase 10).

Each render(ctx) receives {"conn", "workspace", "mode", "data_dir",
"modules_dir"}. Streamlit is imported inside render functions so the
module stays importable without the UI stack.
"""
from __future__ import annotations

import json as _json


def _num_list(st, label, key, default="100,120,140"):
    raw = st.text_area(label, value=default, key=key,
                       help="Comma-separated numbers.")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _save_run(conn, name, kind, inputs, result):
    conn.execute(
        "INSERT INTO cf_runs (name, kind, inputs_json, result_json)"
        " VALUES (?,?,?,?)",
        (name, kind, _json.dumps(inputs, ensure_ascii=False),
         _json.dumps(result, ensure_ascii=False, default=str)))
    conn.commit()


def render_appraisal(ctx):
    """Investment appraisal: NPV, IRR, payback."""
    import streamlit as st
    from . import finance

    st.header("Investment Appraisal")
    conn = ctx["conn"]
    cfs = _num_list(st, "Cash flows (period 1..n)", "cf_cfs")
    outlay = st.text_input("Initial outlay", "300", key="cf_outlay")
    rate = st.text_input("Discount rate (decimal, e.g. 0.10)",
                         "0.10", key="cf_rate")
    name = st.text_input("Run name", "Project A", key="cf_name")
    col1, col2, col3 = st.columns(3)
    try:
        if col1.button("NPV"):
            res = finance.npv(cfs, rate, outlay)
            st.metric("NPV", res["npv"])
            st.write("Accept" if res["accept"] else "Reject")
            st.write(res["workings"])
            _save_run(conn, name, "npv",
                      {"cash_flows": cfs, "discount_rate": rate,
                       "initial_outlay": outlay}, res)
        if col2.button("IRR"):
            res = finance.irr(cfs, outlay)
            st.metric("IRR %", res["irr_pct"])
            st.write(f"Check NPV at IRR: {res['check_npv_at_irr']}")
            _save_run(conn, name, "irr",
                      {"cash_flows": cfs, "initial_outlay": outlay}, res)
        if col3.button("Payback"):
            res = finance.payback(cfs, outlay, rate)
            st.metric("Discounted payback (periods)",
                      res["payback_periods"] or "never")
            _save_run(conn, name, "payback",
                      {"cash_flows": cfs, "initial_outlay": outlay,
                       "discount_rate": rate}, res)
    except ValueError as exc:
        st.error(str(exc))
    st.caption("Assumptions: cash flows at period ends; rate reflects "
               "project risk. Payback ignores time value unless discounted.")


def render_costofcap(ctx):
    """CAPM and WACC."""
    import streamlit as st
    from . import finance

    st.header("Cost of Capital")
    conn = ctx["conn"]
    st.subheader("CAPM — cost of equity")
    rf = st.text_input("Risk-free rate (decimal)", "0.06", key="w_rf")
    beta = st.text_input("Beta", "1.2", key="w_beta")
    rm = st.text_input("Market return (decimal)", "0.14", key="w_rm")
    if st.button("CAPM"):
        try:
            res = finance.capm(rf, beta, rm)
            st.metric("Ke %", res["cost_of_equity"])
            _save_run(conn, "CAPM", "capm",
                      {"risk_free": rf, "beta": beta,
                       "market_return": rm}, res)
        except ValueError as exc:
            st.error(str(exc))
    st.subheader("WACC")
    e = st.text_input("Market value of equity", "600", key="w_e")
    d = st.text_input("Market value of debt", "400", key="w_d")
    ke = st.text_input("Cost of equity (decimal)", "0.156", key="w_ke")
    kd = st.text_input("Cost of debt (decimal)", "0.10", key="w_kd")
    t = st.text_input("Tax rate (decimal)", "0.29", key="w_t")
    if st.button("WACC"):
        try:
            res = finance.wacc(e, d, ke, kd, t)
            st.metric("WACC %", res["wacc"])
            st.write(res["workings"])
            _save_run(conn, "WACC", "wacc",
                      {"equity_value": e, "debt_value": d,
                       "cost_of_equity": ke, "cost_of_debt": kd,
                       "tax_rate": t}, res)
        except ValueError as exc:
            st.error(str(exc))


def render_valuation(ctx):
    """Gordon growth valuation and sensitivity."""
    import streamlit as st
    from . import finance

    st.header("Valuation & Sensitivity")
    conn = ctx["conn"]
    st.subheader("Gordon growth model")
    d1 = st.text_input("Next dividend D1", "5", key="v_d1")
    ke = st.text_input("Cost of equity (decimal)", "0.15", key="v_ke")
    g = st.text_input("Growth (decimal)", "0.05", key="v_g")
    if st.button("Value"):
        try:
            res = finance.gordon_valuation(d1, ke, g)
            st.metric("Value per share", res["value_per_share"])
            _save_run(conn, "Gordon", "gordon",
                      {"next_dividend": d1, "cost_of_equity": ke,
                       "growth": g}, res)
        except ValueError as exc:
            st.error(str(exc))
    st.subheader("Sensitivity — NPV")
    cfs = _num_list(st, "Cash flows", "s_cfs", "100,120,140")
    outlay = st.text_input("Initial outlay", "300", key="s_outlay")
    rate = st.text_input("Discount rate", "0.10", key="s_rate")
    vary = st.selectbox("Vary", ["discount_rate", "initial_outlay",
                                 "cash_flows"])
    if st.button("Run sensitivity"):
        try:
            res = finance.sensitivity(
                {"cash_flows": cfs, "discount_rate": rate,
                 "initial_outlay": outlay},
                vary, ["-0.20", "-0.10", "0", "0.10", "0.20"])
            st.write(f"Base NPV: {res['base_npv']}")
            st.table(res["rows"])
            _save_run(conn, "Sensitivity", "sensitivity",
                      {"varied_input": vary}, res)
        except ValueError as exc:
            st.error(str(exc))


def render_history(ctx):
    """Saved runs."""
    import streamlit as st

    st.header("Saved Runs")
    rows = ctx["conn"].execute(
        "SELECT * FROM cf_runs ORDER BY id DESC").fetchall()
    for r in rows:
        import json as _j
        with st.expander(f"#{r['id']} {r['name']} [{r['kind']}]"):
            st.write("**Inputs:**", _j.loads(r["inputs_json"]))
            st.write("**Result:**", _j.loads(r["result_json"]))
            st.caption(r["created_at"])


def register_pages():
    return [
        {"id": "cf_appraisal", "title": "Investment Appraisal",
         "render": render_appraisal, "modes": ["practice", "professional"]},
        {"id": "cf_costofcap", "title": "Cost of Capital",
         "render": render_costofcap, "modes": ["practice", "professional"]},
        {"id": "cf_valuation", "title": "Valuation & Sensitivity",
         "render": render_valuation, "modes": ["practice", "professional"]},
        {"id": "cf_history", "title": "Saved Runs",
         "render": render_history, "modes": ["practice", "professional"]},
    ]
