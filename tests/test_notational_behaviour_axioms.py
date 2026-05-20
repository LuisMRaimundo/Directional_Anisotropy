"""Formal notational behaviour axioms for metric functions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from anisotropia.config import AnalysisConfig
from anisotropia.metrics import (
    Metrics,
    aggregate_2A,
    compute_directional_conflict,
    compute_metrics_from_transitions,
    compute_tensor_and_R,
)
from anisotropia.pipeline import run_analysis
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _df_from_dp_dt(dp, dt, w=None):
    n = len(dp)
    w = w if w is not None else np.ones(n)
    return pd.DataFrame(
        {
            "dp": np.asarray(dp, float),
            "dt_ql": np.asarray(dt, float),
            "dt_sec": np.asarray(dt, float),
            "w_dur": w,
            "w_min": np.minimum(w, np.asarray(dt, float)),
        }
    )


# --- Drift D ---


def test_D_ascending_positive():
    df = _df_from_dp_dt([2, 2, 1], [1, 1, 1])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.D > 0


def test_D_descending_negative():
    df = _df_from_dp_dt([-2, -3, -1], [1, 1, 1])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.D < 0


def test_D_balanced_near_zero():
    df = _df_from_dp_dt([2, -2, 2, -2], [1, 1, 1, 1])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert abs(m.D) < 0.15


def test_D_zero_denominator_safe():
    df = _df_from_dp_dt([0, 0], [1, 1])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.D == 0.0


# --- Tortuosity tau ---


def test_tau_monotone_low():
    df = _df_from_dp_dt([1, 1, 1, 1], [1, 1, 1, 1])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.tau < 0.2


def test_tau_oscillating_higher():
    df = _df_from_dp_dt([3, -3, 3, -3], [1, 1, 1, 1])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.tau > 0.5


def test_tau_bounded_unit_interval():
    df = _df_from_dp_dt(np.random.randn(40), np.ones(40), np.ones(40))
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert 0.0 <= m.tau <= 1.0


# --- Tensor anisotropy ---


def test_A_rank_one_high():
    dt = np.ones(30) * 0.5
    dp = np.ones(30) * 2.0 + np.random.randn(30) * 0.01
    w = np.ones(30)
    A, _, R = compute_tensor_and_R(dt, dp, w, standardize=True)
    assert A > 0.85
    assert R > 0.85


def test_A_isotropic_lower():
    dt = np.random.rand(80) + 0.1
    dp = np.random.randn(80) * 4
    w = np.ones(80)
    A, _, _ = compute_tensor_and_R(dt, dp, w, standardize=True)
    assert A < 0.55


def test_standardize_none_vs_local_zscore_both_finite():
    """local_zscore rescales axes; rank-one geometry can match none on proportional data."""
    dt = np.array([1.0, 100.0, 2.0, 200.0])
    dp = np.array([1.0, 2.0, 1.0, 2.0])
    w = np.ones(4)
    A_none, _, _ = compute_tensor_and_R(dt, dp, w, standardize="none")
    A_loc, _, _ = compute_tensor_and_R(dt, dp, w, standardize="local_zscore")
    assert np.isfinite(A_none) and np.isfinite(A_loc)
    assert A_loc > 0.5


# --- Angular coherence R ---


def test_R_aligned_high():
    dt = np.ones(25)
    dp = np.ones(25) * 1.5
    w = np.ones(25)
    _, _, R = compute_tensor_and_R(dt, dp, w, standardize=False)
    assert R > 0.95


def test_R_dispersed_lower():
    angles = np.linspace(0, 2 * np.pi, 36, endpoint=False)
    dt = np.cos(angles) + 0.5
    dp = np.sin(angles) + 0.5
    w = np.ones(36)
    _, _, R = compute_tensor_and_R(dt, dp, w, standardize=False)
    assert R < 0.45


def test_R_in_unit_interval():
    df = _df_from_dp_dt(np.random.randn(20), np.abs(np.random.randn(20)) + 0.1)
    m = compute_metrics_from_transitions(df, "ql", "dur")
    assert 0.0 <= m.R <= 1.0


# --- 2A / 2B / conflict ---


def test_2A_weighted_respects_weights():
    m_hi = Metrics(D=1.0, tau=0.0, A_tensor=0.9, mu=0.0, R=0.9, n=10, weight_sum=100.0)
    m_lo = Metrics(D=-1.0, tau=1.0, A_tensor=0.1, mu=3.14, R=0.1, n=2, weight_sum=1.0)
    agg = aggregate_2A({"a": m_hi, "b": m_lo})
    assert agg.D > 0.5


def test_2B_can_differ_from_2A():
    xml = (FIXTURES / "minimal_two_parts.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    r = run_analysis(xml, "two.xml", cfg)
    mA = r.windows[0].metrics_2a
    mB = r.windows[0].metrics_2b
    assert mA is not None and mB is not None


def test_conflict_high_for_opposing_mu():
    m1 = Metrics(D=0, tau=0, A_tensor=0.8, mu=0.0, R=0.8, n=5, weight_sum=5.0)
    m2 = Metrics(D=0, tau=0, A_tensor=0.8, mu=np.pi, R=0.8, n=5, weight_sum=5.0)
    c = compute_directional_conflict({"a": m1, "b": m2})
    assert c > 0.5


# --- Windowing determinism ---


def test_windowed_pipeline_deterministic():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="events", window_size=2, step=1, bootstrap_ci=False)
    r1 = run_analysis(xml, "m.xml", cfg)
    r2 = run_analysis(xml, "m.xml", cfg)
    assert r1.df_results.equals(r2.df_results)
