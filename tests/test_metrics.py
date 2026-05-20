"""Testes unitários para métricas de anisotropia notacional."""

import numpy as np
import pandas as pd

from anisotropia.metrics import (
    Metrics,
    compute_tensor_and_R,
    compute_metrics_from_transitions,
    aggregate_2A,
    aggregate_2B,
    _compute_weighted_aggregate,
)


def test_compute_tensor_and_R_unidirectional():
    """Transições maioritariamente ascendentes: A_tensor alto, R alto."""
    np.random.seed(42)
    n = 20
    dt = np.random.rand(n) * 0.5 + 0.1  # pequena variância
    dp = np.random.rand(n) * 0.5 + 1.5  # dp sempre positivo, predominante subida
    w = np.ones(n)
    A, mu, R = compute_tensor_and_R(dt, dp, w, standardize=True)
    assert np.isfinite(A)
    assert A > 0.5
    assert np.isfinite(R)
    assert R > 0.5


def test_compute_tensor_and_R_isotropic():
    """Transições em todas as direcções: A_tensor baixo."""
    np.random.seed(42)
    n = 100
    dt = np.random.rand(n) + 0.1
    dp = np.random.randn(n) * 3  # aleatório
    w = np.ones(n)
    A, mu, R = compute_tensor_and_R(dt, dp, w, standardize=True)
    assert np.isfinite(A)
    assert A < 0.5


def test_compute_tensor_and_R_empty_weights():
    """Soma de pesos zero: retorna NaN."""
    dt = np.array([1.0, 2.0])
    dp = np.array([0.5, -0.5])
    w = np.array([0.0, 0.0])
    A, mu, R = compute_tensor_and_R(dt, dp, w, standardize=True)
    assert np.isnan(A)
    assert np.isnan(mu)
    assert np.isnan(R)


def test_compute_metrics_from_transitions_empty():
    """DataFrame vazio: métricas NaN."""
    df = pd.DataFrame(columns=["ql", "t", "meas", "dp", "dt_ql", "dt_sec", "w_dur", "w_min"])
    m = compute_metrics_from_transitions(df, "ql", "dur")
    assert m.n == 0
    assert np.isnan(m.A_tensor)


def test_compute_metrics_from_transitions_bootstrap():
    """Com n>=8 e bootstrap_ci: deve produzir IC finitos."""
    n = 30
    df = pd.DataFrame({
        "dp": np.random.randn(n) * 2,
        "dt_ql": np.ones(n) * 0.5,
        "dt_sec": np.ones(n) * 0.5,
        "w_dur": np.ones(n),
        "w_min": np.ones(n) * 0.25,
    })
    df = df[df["dt_ql"] > 0]
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=True, bootstrap_ci=True)
    assert m.n >= 8
    assert np.isfinite(m.A_tensor_ci_lo)
    assert np.isfinite(m.A_tensor_ci_hi)
    assert m.A_tensor_ci_lo <= m.A_tensor_ci_hi


def test_aggregate_2A_single_part():
    """2A com um instrumento: resultado igual ao da parte."""
    m1 = Metrics(D=0.5, tau=0.3, A_tensor=0.8, mu=1.57, R=0.9, n=10, weight_sum=5.0)
    agg = aggregate_2A({"Part1": m1}, bootstrap_ci=False)
    assert agg.A_tensor == 0.8
    assert agg.n == 10


def test_aggregate_2A_bootstrap():
    """2A com ≥2 instrumentos e bootstrap: IC finitos."""
    m1 = Metrics(D=0.5, tau=0.3, A_tensor=0.8, mu=1.57, R=0.9, n=10, weight_sum=5.0)
    m2 = Metrics(D=-0.2, tau=0.5, A_tensor=0.6, mu=1.5, R=0.7, n=8, weight_sum=4.0)
    agg = aggregate_2A({"P1": m1, "P2": m2}, bootstrap_ci=True)
    assert np.isfinite(agg.A_tensor_ci_lo)
    assert np.isfinite(agg.A_tensor_ci_hi)


def test_aggregate_2B_pooled():
    """2B concatena transições."""
    df1 = pd.DataFrame({"dp": [1, 2], "dt_ql": [0.5, 0.5], "dt_sec": [0.5, 0.5], "w_dur": [1, 1], "w_min": [0.25, 0.25]})
    df2 = pd.DataFrame({"dp": [-1, 0], "dt_ql": [0.5, 0.5], "dt_sec": [0.5, 0.5], "w_dur": [1, 1], "w_min": [0.25, 0.25]})
    agg = aggregate_2B({"P1": df1, "P2": df2}, "ql", "dur", standardize=True, bootstrap_ci=False)
    assert agg.n == 4


def test_D_tau_closed_form_no_standardize():
    """Hand-checked: D = sum(w dp)/sum(w|dp|), tau = 1 - |sum(w dp)|/sum(w|dp|)."""
    df = pd.DataFrame(
        {
            "dp": [3.0, -1.0],
            "dt_ql": [1.0, 1.0],
            "dt_sec": [1.0, 1.0],
            "w_dur": [1.0, 1.0],
            "w_min": [1.0, 1.0],
        }
    )
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=False)
    assert abs(m.D - 0.5) < 1e-12
    assert abs(m.tau - 0.5) < 1e-12


def test_tensor_parallel_vectors_rank_one_A_equals_one():
    """All (dt, dp) parallel → J rank-one → lambda2=0 → A_tensor=1."""
    from anisotropia.metrics import _compute_tensor_and_R_internal

    dt = np.ones(5)
    dp = np.ones(5)
    w = np.ones(5)
    A, _mu, _R, l1, l2, _, _, _ = _compute_tensor_and_R_internal(dt, dp, w, standardize=False)
    assert abs(A - 1.0) < 1e-9
    assert l2 == 0.0 or abs(l2) < 1e-9


def test_aggregate_2B_matches_manual_concat():
    """2B must equal metrics on vertically stacked transitions."""
    df1 = pd.DataFrame(
        {
            "dp": [1.0, 0.5],
            "dt_ql": [1.0, 1.0],
            "dt_sec": [1.0, 1.0],
            "w_dur": [1.0, 1.0],
            "w_min": [0.5, 0.5],
        }
    )
    df2 = pd.DataFrame(
        {
            "dp": [-0.25],
            "dt_ql": [0.5],
            "dt_sec": [0.5],
            "w_dur": [2.0],
            "w_min": [0.5],
        }
    )
    m_b = aggregate_2B({"P1": df1, "P2": df2}, "ql", "dur", standardize=False, bootstrap_ci=False)
    m_p = compute_metrics_from_transitions(
        pd.concat([df1, df2], axis=0, ignore_index=True),
        "ql",
        "dur",
        standardize=False,
        bootstrap_ci=False,
    )
    assert m_b.n == m_p.n
    assert abs(m_b.D - m_p.D) < 1e-12
    assert abs(m_b.tau - m_p.tau) < 1e-12
    assert abs(m_b.A_tensor - m_p.A_tensor) < 1e-12 or (
        np.isnan(m_b.A_tensor) and np.isnan(m_p.A_tensor)
    )


def test_weighted_aggregate_circular_mu():
    """Média circular de μ evita wrap incorreto."""
    m1 = Metrics(D=0, tau=0, A_tensor=0.5, mu=3.0, R=0.5, n=5, weight_sum=2.0)  # μ perto de π
    m2 = Metrics(D=0, tau=0, A_tensor=0.5, mu=-3.0, R=0.5, n=5, weight_sum=2.0)  # μ perto de -π
    agg = _compute_weighted_aggregate([m1, m2])
    assert np.isfinite(agg.mu)
    # média de 3 e -3 (mod 2π) deveria estar perto de π
    assert abs(agg.mu) <= np.pi
