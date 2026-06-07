"""Additional focused tests for anisotropia.metrics helpers and branches."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from anisotropia.metrics import (
    Metrics,
    _compute_tensor_and_R_internal,
    _compute_weighted_aggregate,
    _standardize_dt_dp,
    _weighted_median,
    aggregate_2A,
    aggregate_2B,
    compute_directional_conflict,
    compute_metrics_from_transitions,
)


def _minimal_trans_df(
    dp: list[float],
    dt_ql: list[float] | None = None,
    w_dur: list[float] | None = None,
) -> pd.DataFrame:
    n = len(dp)
    dt_ql = dt_ql or [1.0] * n
    w_dur = w_dur or [1.0] * n
    return pd.DataFrame(
        {
            "dp": dp,
            "dt_ql": dt_ql,
            "dt_sec": dt_ql,
            "w_dur": w_dur,
            "w_min": w_dur,
        }
    )


# --- 1. _weighted_median ------------------------------------------------------


def test_weighted_median_empty_returns_nan():
    assert np.isnan(_weighted_median(np.array([]), np.array([])))


def test_weighted_median_unsorted_x_with_weights():
    x = np.array([3.0, 1.0, 2.0])
    w = np.array([1.0, 1.0, 1.0])
    assert _weighted_median(x, w) == pytest.approx(2.0)


def test_weighted_median_clips_negative_weights_to_zero():
    x = np.array([1.0, 2.0, 3.0])
    w = np.array([-5.0, 2.0, 0.0])
    assert _weighted_median(x, w) == pytest.approx(2.0)


def test_weighted_median_all_zero_weights_returns_first_sorted_value():
    x = np.array([9.0, 5.0])
    w = np.array([0.0, 0.0])
    assert _weighted_median(x, w) == pytest.approx(5.0)


def test_weighted_median_half_weight_boundary():
    x = np.array([1.0, 2.0, 3.0])
    w = np.array([1.0, 1.0, 2.0])
    assert _weighted_median(x, w) == pytest.approx(2.0)


# --- 2. _standardize_dt_dp ----------------------------------------------------


def test_standardize_none_returns_inputs_unchanged():
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([4.0, 5.0, 6.0])
    w = np.ones(3)
    out1, out2 = _standardize_dt_dp(v1, v2, w, 3.0, "none")
    assert np.allclose(out1, v1)
    assert np.allclose(out2, v2)


def test_standardize_local_zscore_centers_and_scales():
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([2.0, 4.0, 6.0])
    w = np.ones(3)
    s1, s2 = _standardize_dt_dp(v1, v2, w, 3.0, "local_zscore")
    assert np.isclose(np.sum(s1), 0.0, atol=1e-12)
    assert np.isclose(np.sum(s2), 0.0, atol=1e-12)


def test_standardize_global_zscore_aliases_to_local_zscore():
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([2.0, 4.0, 6.0])
    w = np.ones(3)
    local = _standardize_dt_dp(v1, v2, w, 3.0, "local_zscore")
    global_ = _standardize_dt_dp(v1, v2, w, 3.0, "global_zscore")
    assert np.allclose(local[0], global_[0])
    assert np.allclose(local[1], global_[1])


def test_standardize_robust_scale_uses_median_mad_path():
    v1 = np.array([1.0, 2.0, 3.0, 100.0])
    v2 = np.array([1.0, 2.0, 3.0, 4.0])
    w = np.ones(4)
    s1, _ = _standardize_dt_dp(v1, v2, w, 4.0, "robust_scale")
    z_local, _ = _standardize_dt_dp(v1, v2, w, 4.0, "local_zscore")
    assert not np.allclose(s1, z_local)


def test_standardize_unknown_mode_falls_back_like_local_zscore():
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([2.0, 4.0, 6.0])
    w = np.ones(3)
    fallback, _ = _standardize_dt_dp(v1, v2, w, 3.0, "unexpected_mode")
    local, _ = _standardize_dt_dp(v1, v2, w, 3.0, "local_zscore")
    assert np.allclose(fallback, local)


def test_compute_tensor_unknown_standardize_string_defaults_to_local():
    dt = np.array([1.0, 1.0, 1.0])
    dp = np.array([1.0, 2.0, 3.0])
    w = np.ones(3)
    a_unknown, _, _, _, _, _, _, _ = _compute_tensor_and_R_internal(dt, dp, w, "not-a-mode")
    a_local, _, _, _, _, _, _, _ = _compute_tensor_and_R_internal(dt, dp, w, "local_zscore")
    assert a_unknown == pytest.approx(a_local)


def test_compute_tensor_zero_weight_sum_returns_nan_tuple():
    dt = np.array([1.0, 2.0])
    dp = np.array([1.0, -1.0])
    w = np.array([0.0, 0.0])
    result = _compute_tensor_and_R_internal(dt, dp, w, True)
    assert all(np.isnan(v) for v in result)


def test_compute_tensor_non_positive_eigen_sum_yields_nan_a_tensor():
    dt = np.zeros(4)
    dp = np.zeros(4)
    w = np.ones(4)
    A, mu, R, lam1, lam2, _, _, _ = _compute_tensor_and_R_internal(dt, dp, w, False)
    assert np.isnan(A)
    assert np.isnan(lam1)
    assert np.isnan(lam2)


# --- 3. compute_metrics_from_transitions (per-part / 1A-style) ----------------


def test_compute_metrics_empty_dataframe_nan_metrics():
    df = pd.DataFrame(columns=["dp", "dt_ql", "dt_sec", "w_dur", "w_min"])
    m = compute_metrics_from_transitions(df, "ql", "dur")
    assert m.n == 0
    assert m.weight_sum == 0.0
    assert np.isnan(m.D)
    assert np.isnan(m.tau)
    assert np.isnan(m.A_tensor)
    assert np.isnan(m.mu)
    assert np.isnan(m.R)


def test_compute_metrics_valid_minimal_dataframe_finite_fields():
    df = _minimal_trans_df(dp=[2.0, 2.0], dt_ql=[1.0, 1.0])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.n == 2
    assert m.weight_sum == pytest.approx(2.0)
    assert np.isfinite(m.D)
    assert np.isfinite(m.tau)
    assert np.isfinite(m.A_tensor)
    assert np.isfinite(m.mu)
    assert np.isfinite(m.R)
    assert m.D == pytest.approx(1.0)
    assert m.tau == pytest.approx(0.0)


def test_compute_metrics_filters_non_finite_and_non_positive_dt():
    df = _minimal_trans_df(
        dp=[1.0, np.nan, 2.0],
        dt_ql=[1.0, 1.0, 0.0],
    )
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.n == 1
    assert m.weight_sum == pytest.approx(1.0)


def test_compute_metrics_all_rows_filtered_returns_empty_metrics():
    df = _minimal_trans_df(dp=[np.nan, np.inf], dt_ql=[1.0, -1.0])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.n == 0
    assert m.weight_sum == 0.0
    assert np.isnan(m.A_tensor)


def test_compute_metrics_zero_or_invalid_weights_fallback_to_ones():
    df = _minimal_trans_df(dp=[1.0, -1.0], w_dur=[0.0, np.nan])
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert m.n == 2
    assert m.weight_sum == pytest.approx(2.0)
    assert m.D == pytest.approx(0.0)


# --- 4. aggregate_2A --------------------------------------------------------


def test_aggregate_2a_empty_mapping_returns_nan_metrics():
    m = aggregate_2A({})
    assert m.n == 0
    assert m.weight_sum == 0.0
    assert np.isnan(m.A_tensor)


def test_aggregate_2a_ignores_empty_or_invalid_parts():
    valid = Metrics(D=0.2, tau=0.1, A_tensor=0.7, mu=0.5, R=0.8, n=4, weight_sum=2.0)
    m = aggregate_2A(
        {
            "good": valid,
            "empty_n": Metrics(0, 0, 0, 0, 0, n=0, weight_sum=1.0),
            "bad_w": Metrics(0, 0, 0, 0, 0, n=3, weight_sum=np.nan),
        }
    )
    assert m.n == 4
    assert m.A_tensor == pytest.approx(0.7)


def test_aggregate_2a_pools_multiple_valid_parts():
    m1 = Metrics(D=0.4, tau=0.2, A_tensor=0.8, mu=0.0, R=0.9, n=3, weight_sum=2.0)
    m2 = Metrics(D=0.2, tau=0.3, A_tensor=0.6, mu=0.0, R=0.7, n=2, weight_sum=1.0)
    m = aggregate_2A({"a": m1, "b": m2})
    assert m.n == 5
    assert m.weight_sum == pytest.approx(3.0)
    assert np.isfinite(m.D)
    assert np.isfinite(m.A_tensor)


def test_compute_weighted_aggregate_empty_parts_list_returns_nan_metrics():
    m = _compute_weighted_aggregate([])
    assert m.n == 0
    assert m.weight_sum == 0.0
    assert np.isnan(m.A_tensor)


def test_compute_weighted_aggregate_non_positive_weights_use_ones_fallback():
    m = Metrics(D=1.0, tau=0.0, A_tensor=0.5, mu=0.0, R=0.5, n=2, weight_sum=-1.0)
    out = _compute_weighted_aggregate([m])
    assert out.n == 2
    assert out.weight_sum == pytest.approx(1.0)
    assert out.D == pytest.approx(1.0)


def test_compute_weighted_aggregate_non_finite_scalar_attrs_become_nan():
    m = Metrics(D=np.nan, tau=np.nan, A_tensor=np.nan, mu=np.nan, R=np.nan, n=2, weight_sum=1.0)
    out = _compute_weighted_aggregate([m])
    assert out.n == 2
    assert np.isnan(out.D)
    assert np.isnan(out.A_tensor)
    assert np.isnan(out.mu)


def test_aggregate_2b_empty_transitions_returns_nan_metrics():
    m = aggregate_2B({}, "ql", "dur")
    assert m.n == 0
    assert np.isnan(m.A_tensor)


# --- 5. compute_directional_conflict ------------------------------------------


def test_directional_conflict_empty_mapping_returns_nan():
    assert np.isnan(compute_directional_conflict({}))


def test_directional_conflict_ignores_invalid_parts():
    valid = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.0, R=0.9, n=2, weight_sum=1.0)
    out = compute_directional_conflict(
        {
            "ok": valid,
            "no_n": Metrics(0, 0, 0.5, 0.0, 0.5, n=0, weight_sum=1.0),
            "bad_w": Metrics(0, 0, 0.5, 0.0, 0.5, n=2, weight_sum=np.nan),
            "no_mu": Metrics(0, 0, 0.5, mu=np.nan, R=0.5, n=2, weight_sum=1.0),
        }
    )
    assert out == pytest.approx(0.0)


def test_directional_conflict_zero_total_weight_returns_nan():
    m = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.0, R=0.5, n=2, weight_sum=0.0)
    assert np.isnan(compute_directional_conflict({"a": m, "b": m}))


def test_directional_conflict_aligned_directions_low_conflict():
    mu = 0.25
    m = Metrics(D=0, tau=0, A_tensor=0.5, mu=mu, R=0.9, n=3, weight_sum=2.0)
    out = compute_directional_conflict({"a": m, "b": m})
    assert out == pytest.approx(0.0)


def test_directional_conflict_opposed_directions_high_conflict():
    m1 = Metrics(D=0, tau=0, A_tensor=0.5, mu=0.0, R=0.9, n=3, weight_sum=2.0)
    m2 = Metrics(D=0, tau=0, A_tensor=0.5, mu=math.pi, R=0.9, n=3, weight_sum=2.0)
    out = compute_directional_conflict({"a": m1, "b": m2})
    assert out == pytest.approx(1.0)
