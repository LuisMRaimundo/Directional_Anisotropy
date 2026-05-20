"""Tests for anisotropia.visualizations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from anisotropia.metrics import Metrics, compute_directional_conflict
from anisotropia.parsing import Event
from anisotropia.visualizations import (
    tensor_ellipse_from_metrics,
    flow_map_quiver,
    plot_tensor_ellipses,
    plot_tensor_ellipses_per_instrument,
    plot_rose_diagram,
    plot_pitch_over_time,
    plot_time_curves,
    _pitch_tick_note_name,
)


def test_compute_directional_conflict_aligned():
    """When all μ are equal, conflict ≈ 0."""
    m = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.0, R=0.8, n=10, weight_sum=1.0)
    out = compute_directional_conflict({"a": m, "b": m})
    assert np.isfinite(out) and abs(out) < 0.01


def test_compute_directional_conflict_opposite():
    """When μ differ by π, conflict ≈ 1."""
    m1 = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.0, R=0.8, n=10, weight_sum=1.0)
    m2 = Metrics(D=0, tau=0, A_tensor=0.5, mu=np.pi, R=0.8, n=10, weight_sum=1.0)
    out = compute_directional_conflict({"a": m1, "b": m2})
    assert np.isfinite(out) and out > 0.9


def test_compute_directional_conflict_empty():
    """Empty input returns nan."""
    out = compute_directional_conflict({})
    assert np.isnan(out)


def test_compute_directional_conflict_single_part():
    """Single part: R_inst=1, conflict=0."""
    m = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.5, R=0.8, n=10, weight_sum=1.0)
    out = compute_directional_conflict({"a": m})
    assert np.isfinite(out) and abs(out) < 0.01


def test_compute_directional_conflict_orthogonal():
    """μ at 0° and 90°: R_inst = √2/2 ≈ 0.71, conflict ≈ 0.29 > 0 (some disagreement)."""
    m1 = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.0, R=0.8, n=10, weight_sum=1.0)
    m2 = Metrics(D=0, tau=0, A_tensor=0.5, mu=np.pi / 2, R=0.8, n=10, weight_sum=1.0)
    out = compute_directional_conflict({"a": m1, "b": m2})
    assert np.isfinite(out) and out > 0 and out < 1


def test_tensor_ellipse_from_metrics_normalized():
    """Normalized fallback: A=1 → λ1=1, λ2≈0; ellipse degenerate along major axis."""
    w, h, ang = tensor_ellipse_from_metrics(1.0, 0.0)
    assert w > 0 and h >= 0 and np.isfinite(ang)


def test_tensor_ellipse_from_metrics_isotropic():
    """A=0: λ1=λ2=0.5, circular ellipse."""
    w, h, ang = tensor_ellipse_from_metrics(0.0, 0.5)
    assert abs(w - h) < 0.01 and np.isfinite(ang)


def test_tensor_ellipse_from_metrics_real_lambda():
    """When real λ provided, use them."""
    w1, h1, _ = tensor_ellipse_from_metrics(0.5, 0.0)
    w2, h2, _ = tensor_ellipse_from_metrics(0.5, 0.0, lam1=1.5, lam2=0.5)
    assert w2 > w1 or h2 != h1  # different scale from real eigenvalues


def test_tensor_ellipse_from_metrics_nonfinite():
    assert tensor_ellipse_from_metrics(float("nan"), 0.0) == (0, 0, 0)


def test_flow_map_quiver_subset():
    """Flow map with subset params returns figure."""
    df = pd.DataFrame([
        {"window": "w1", "part": "P1", "mu": 0.0, "A_tensor": 0.5, "D": 0.2},
        {"window": "w2", "part": "P1", "mu": 0.1, "A_tensor": 0.6, "D": -0.1},
    ])
    win_order = {"w1": 0, "w2": 1}
    fig = flow_map_quiver(df, win_order, arrow_scale=0.5, windows=["w1"], parts=["P1"])
    assert fig is not None
    plt.close(fig)


def test_flow_map_quiver_empty_grid():
    """Sem janelas em win_order → painel 'No data'."""
    df = pd.DataFrame([{"window": "w1", "part": "P1", "mu": 0.0, "A_tensor": 0.5, "D": 0.2}])
    fig = flow_map_quiver(df, {})
    plt.close(fig)
    assert fig is not None


def test_flow_map_quiver_arrow_scale_none():
    df = pd.DataFrame([{"window": "w1", "part": "P1", "mu": 0.0, "A_tensor": 0.5, "D": 0.0}])
    fig = flow_map_quiver(df, {"w1": 0}, arrow_scale=None)
    plt.close(fig)


def test_flow_map_quiver_no_colorbar_branch():
    """Sem D finito → ramo quiver sem mapa de cores."""
    df = pd.DataFrame([{"window": "w1", "part": "P1", "mu": 0.0, "A_tensor": 0.5, "D": float("nan")}])
    fig = flow_map_quiver(df, {"w1": 0})
    plt.close(fig)


def test_plot_tensor_ellipses_and_empty():
    df = pd.DataFrame({
        "window": ["w1"],
        "A_tensor": [0.5],
        "mu": [0.1],
        "lambda1": [1.0],
        "lambda2": [0.5],
    })
    fig = plot_tensor_ellipses(df, {"w1": 0})
    plt.close(fig)
    fig_empty = plot_tensor_ellipses(pd.DataFrame(), {})
    plt.close(fig_empty)


def test_plot_tensor_ellipses_multi_axes():
    df = pd.DataFrame({
        "window": ["w1", "w2", "w3"],
        "A_tensor": [0.5, 0.4, 0.6],
        "mu": [0.1, 0.2, 0.3],
    })
    fig = plot_tensor_ellipses(df, {"w1": 0, "w2": 1, "w3": 2})
    plt.close(fig)


def test_plot_tensor_ellipses_per_instrument():
    df = pd.DataFrame([
        {"window": "w1", "part": "A", "A_tensor": 0.5, "mu": 0.1, "lambda1": 1.0, "lambda2": 0.3},
        {"window": "w1", "part": "B", "A_tensor": 0.4, "mu": 0.5, "lambda1": 0.8, "lambda2": 0.4},
    ])
    fig = plot_tensor_ellipses_per_instrument(df, {"w1": 0}, max_plots=4)
    plt.close(fig)
    df_empty = pd.DataFrame(columns=["window", "part", "A_tensor", "mu"])
    fig_empty = plot_tensor_ellipses_per_instrument(df_empty, {"w1": 0})
    plt.close(fig_empty)


def test_plot_rose_diagram_branches():
    df_ok = pd.DataFrame({"dt_ql": [1.0, 1.0], "dp": [1.0, -0.5]})
    fig = plot_rose_diagram(df_ok, time_axis="ql")
    plt.close(fig)
    fig_nd = plot_rose_diagram(pd.DataFrame(), time_axis="ql")
    plt.close(fig_nd)
    df_z = pd.DataFrame({"dt_ql": [0.0], "dp": [1.0]})
    fig_z = plot_rose_diagram(df_z, time_axis="ql")
    plt.close(fig_z)
    df_sec = pd.DataFrame({"dt_sec": [1.0], "dp": [0.5]})
    fig_sec = plot_rose_diagram(df_sec, time_axis="sec")
    plt.close(fig_sec)


def test_plot_rose_diagram_per_window():
    a = pd.DataFrame({"dt_ql": [1.0, 1.0], "dp": [1.0, -1.0]})
    b = pd.DataFrame({"dt_ql": [1.0], "dp": [0.5]})
    trans_by_window = {"w1": a, "w2": b}
    win_order = {"w1": 0, "w2": 1}
    fig = plot_rose_diagram(
        a, time_axis="ql", per_window=True, trans_by_window=trans_by_window, win_order=win_order, max_windows=4
    )
    plt.close(fig)


def test_pitch_tick_note_name_maps_midi():
    assert _pitch_tick_note_name(60.0) == "C4"
    assert _pitch_tick_note_name(62.0) == "D4"


def test_plot_pitch_over_time():
    evs = {
        "Vln": [
            Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1),
            Event(t=1.0, ql=1.0, dur_ql=1.0, p=62.0, meas=1),
        ]
    }
    fig = plot_pitch_over_time(evs, has_seconds=True)
    plt.close(fig)
    fig_q = plot_pitch_over_time(evs, has_seconds=False)
    plt.close(fig_q)
    fig_empty = plot_pitch_over_time({}, has_seconds=True)
    plt.close(fig_empty)


def test_plot_pitch_over_time_many_instruments():
    evs = {f"P{i}": [Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0 + i, meas=1)] for i in range(12)}
    fig = plot_pitch_over_time(evs, has_seconds=True)
    plt.close(fig)


def test_plot_time_curves():
    df = pd.DataFrame({
        "window": ["w1", "w2"],
        "scope": ["total_2A", "total_2A"],
        "A_tensor": [0.5, 0.6],
        "mu": [0.1, 0.2],
        "D": [0.1, 0.2],
    })
    win_order = {"w1": 0, "w2": 1}
    fig = plot_time_curves(df, win_order)
    plt.close(fig)
