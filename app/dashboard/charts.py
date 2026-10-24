"""Chart and table helpers that work on old and new Streamlit versions."""
import pandas as pd
import streamlit as st

from dashboard.settings import PALETTE


def _st_version() -> tuple:
    try:
        return tuple(int(p) for p in st.__version__.split(".")[:2])
    except Exception:  # noqa: BLE001
        return (1, 0)


NEW_WIDTH_API = _st_version() >= (1, 50)


def call_stretch(fn, *args, **kwargs):
    """Call a Streamlit element so it fills its container on both old and new versions."""
    attempts = ({"width": "stretch"}, {"use_container_width": True})
    if not NEW_WIDTH_API:
        attempts = attempts[::-1]
    for opts in attempts:
        try:
            return fn(*args, **kwargs, **opts)
        except (TypeError, st.errors.StreamlitAPIException):
            continue
    return fn(*args, **kwargs)


def style_fig(fig, height: int = 360, legend: bool = True):
    """Apply the dark, transparent dashboard style to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins, Segoe UI, sans-serif", color="#dbe4ff"), height=height,
        margin=dict(l=20, r=20, t=55, b=20), colorway=PALETTE, showlegend=legend,
        title=dict(font=dict(size=16, color="#ffffff")),
        legend=dict(bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False)
    return fig


def show_plot(fig, height: int = 360, legend: bool = True) -> None:
    call_stretch(st.plotly_chart, style_fig(fig, height, legend))


def show_df(df: pd.DataFrame, height: int | None = None) -> None:
    kwargs = {"hide_index": True}
    if height:
        kwargs["height"] = height
    call_stretch(st.dataframe, df, **kwargs)


def panel():
    """A bordered container (falls back to a plain one on very old Streamlit)."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()
