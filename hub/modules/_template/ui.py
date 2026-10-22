"""Example UI entry point for a Hub module.

The core shell calls register_pages() at startup and renders each returned
page inside the application navigation. Pages declare which of the three
modes (study / practice / professional) they belong to.

The render callable receives a context dict with at least:
    {"conn": sqlite3.Connection, "workspace": dict | None, "mode": str}

For Streamlit, render functions simply call st.* as usual; the shell sets
the page title beforehand.
"""


def render_home(ctx):
    """Example page — replace with real module pages."""
    # NOTE: Streamlit import is deferred so hubcore stays UI-agnostic.
    import streamlit as st

    st.header("Template module")
    st.write("Replace this with the module's real pages.")


def register_pages():
    return [
        {
            "id": "template_home",
            "title": "Template",
            "render": render_home,
            "modes": ["study", "practice", "professional"],
        }
    ]
