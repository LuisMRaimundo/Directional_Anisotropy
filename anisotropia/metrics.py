"""Métricas de anisotropia notacional."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

EPSILON = 1e-9
N_MIN_BOOTSTRAP = 8
N_MIN_STABLE = 15
N_BOOTSTRAP = 1000


@dataclass
class Metrics:
    D: float
    tau: float
    A_tensor: float
    mu: float
    R: float
    n: int
    weight_sum: float
    A_tensor_ci_lo: float = np.nan
    A_tensor_ci_hi: float = np.nan
    R_ci_lo: float = np.nan
    R_ci_hi: float = np.nan
    lambda1: float = np.nan  # principal eigenvalue of J (for tensor ellipses)
    lambda2: float = np.nan  # secondary eigenvalue
    mu_axis: float = np.nan  # radians; principal axis (eigenvector sign ambiguous)
    cos_mu: float = np.nan
    sin_mu: float = np.nan
    mu_doubled_angle: float = np.nan  # 2*mu for axis statistics (mod 2π)


def _weighted_median(x: np.ndarray, w: np.ndarray) -> float:
    """Simple weighted median (sort by x, cumulative weight)."""
    if len(x) == 0:
        return float("nan")
    order = np.argsort(x)
    x_s = x[order]
    w_s = w[order]
    w_s = np.clip(w_s, 0.0, None)
    cw = np.cumsum(w_s)
    half = cw[-1] / 2.0 if cw[-1] > 0 else 0.0
    idx = int(np.searchsorted(cw, half, side="left"))
    return float(x_s[min(idx, len(x_s) - 1)])


def _standardize_dt_dp(
    v1: np.ndarray,
    v2: np.ndarray,
    w: np.ndarray,
    wsum: float,
    mode: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return scaled (v1, v2) for structure tensor. mode: local_zscore | none | robust_scale | global_zscore."""
    if mode == "none":
        return v1, v2
    if mode == "global_zscore":
        mode = "local_zscore"
    if mode == "local_zscore":
        v1_mean = np.sum(w * v1) / wsum
        v2_mean = np.sum(w * v2) / wsum
        v1_std = np.sqrt(np.sum(w * (v1 - v1_mean) ** 2) / wsum)
        v2_std = np.sqrt(np.sum(w * (v2 - v2_mean) ** 2) / wsum)
        v1_std = max(v1_std, EPSILON)
        v2_std = max(v2_std, EPSILON)
        return (v1 - v1_mean) / v1_std, (v2 - v2_mean) / v2_std
    if mode == "robust_scale":
        m1 = _weighted_median(v1, w)
        m2 = _weighted_median(v2, w)
        mad1 = _weighted_median(np.abs(v1 - m1), w)
        mad2 = _weighted_median(np.abs(v2 - m2), w)
        s1 = max(1.4826 * mad1 if mad1 > 0 else EPSILON, EPSILON)
        s2 = max(1.4826 * mad2 if mad2 > 0 else EPSILON, EPSILON)
        return (v1 - m1) / s1, (v2 - m2) / s2
    v1_mean = np.sum(w * v1) / wsum
    v2_mean = np.sum(w * v2) / wsum
    v1_std = max(np.sqrt(np.sum(w * (v1 - v1_mean) ** 2) / wsum), EPSILON)
    v2_std = max(np.sqrt(np.sum(w * (v2 - v2_mean) ** 2) / wsum), EPSILON)
    return (v1 - v1_mean) / v1_std, (v2 - v2_mean) / v2_std


def _compute_tensor_and_R_internal(
    dt: np.ndarray, dp: np.ndarray, w: np.ndarray, standardize: bool | str
) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Returns (A_tensor, mu_axis, R, lambda1, lambda2, cos_mu, sin_mu, mu_doubled_angle).
    ``standardize`` may be bool (True -> local_zscore) or a mode string.
    """
    v1 = np.array(dt, dtype=float)
    v2 = np.array(dp, dtype=float)
    wsum = float(np.sum(w))
    if wsum <= 0:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
    mode: str = "local_zscore" if standardize is True else ("none" if standardize is False else str(standardize))
    if mode not in ("none", "local_zscore", "robust_scale", "global_zscore"):
        mode = "local_zscore"
    v1, v2 = _standardize_dt_dp(v1, v2, w, wsum, mode)
    J11 = np.sum(w * v1 * v1)
    J12 = np.sum(w * v1 * v2)
    J22 = np.sum(w * v2 * v2)
    J = np.array([[J11, J12], [J12, J22]], dtype=float)
    vals, vecs = np.linalg.eigh(J)
    lam2, lam1 = float(vals[0]), float(vals[1])
    mu_axis = float("nan")
    if (lam1 + lam2) <= 0:
        A_tensor = np.nan
        lam1, lam2 = np.nan, np.nan
    else:
        A_tensor = float((lam1 - lam2) / (lam1 + lam2))
        v = vecs[:, 1]
        mu_axis = float(math.atan2(v[1], v[0]))
    theta = np.arctan2(dp, dt)
    C = np.sum(w * np.cos(theta)) / wsum
    S = np.sum(w * np.sin(theta)) / wsum
    R = float(np.sqrt(C * C + S * S))
    mu = mu_axis if np.isfinite(mu_axis) else np.nan
    cos_mu = float(math.cos(mu_axis)) if np.isfinite(mu_axis) else np.nan
    sin_mu = float(math.sin(mu_axis)) if np.isfinite(mu_axis) else np.nan
    mu_doubled = float(2.0 * mu_axis) if np.isfinite(mu_axis) else np.nan
    return A_tensor, mu, R, lam1, lam2, cos_mu, sin_mu, mu_doubled


def compute_tensor_and_R(
    dt: np.ndarray, dp: np.ndarray, w: np.ndarray, standardize: bool | str
) -> Tuple[float, float, float]:
    """A_tensor, mu, R. Wraps internal for backward compatibility."""
    res = _compute_tensor_and_R_internal(dt, dp, w, standardize)
    return res[0], res[1], res[2]


def compute_metrics_from_transitions(
    df: pd.DataFrame,
    time_axis: str,
    weight_mode: str,
    standardize: bool | str = True,
    bootstrap_ci: bool = False,
) -> Metrics:
    """Métricas a partir de transições. ``standardize``: bool or local_zscore|none|robust_scale|global_zscore."""
    if df.empty:
        return Metrics(D=np.nan, tau=np.nan, A_tensor=np.nan, mu=np.nan, R=np.nan, n=0, weight_sum=0.0)
    dt_col = "dt_ql" if time_axis == "ql" else "dt_sec"
    w_col = "w_dur" if weight_mode == "dur" else "w_min"
    dff = df.copy()
    dff = dff[np.isfinite(dff["dp"].values)]
    dff = dff[np.isfinite(dff[dt_col].values)]
    dff = dff[dff[dt_col] > 0]
    if dff.empty:
        return Metrics(D=np.nan, tau=np.nan, A_tensor=np.nan, mu=np.nan, R=np.nan, n=0, weight_sum=0.0)
    dp = dff["dp"].to_numpy(dtype=float)
    dt = dff[dt_col].to_numpy(dtype=float)
    w = dff[w_col].to_numpy(dtype=float)
    w = np.where(np.isfinite(w), w, 0.0)
    w = np.clip(w, 0.0, None)
    if float(np.sum(w)) <= 0:
        w = np.ones_like(w)
    n = len(dff)
    denom_abs_dp = np.sum(w * np.abs(dp))
    D = float(np.sum(w * dp) / denom_abs_dp) if denom_abs_dp > 0 else 0.0
    tau = (
        float(1.0 - (abs(np.sum(w * dp)) / denom_abs_dp))
        if denom_abs_dp > 0
        else 0.0
    )
    tau = float(np.clip(tau, 0.0, 1.0))
    A_tensor, mu, R, lam1, lam2, cos_mu, sin_mu, mu_da = _compute_tensor_and_R_internal(dt, dp, w, standardize)
    A_lo, A_hi, R_lo, R_hi = np.nan, np.nan, np.nan, np.nan
    if bootstrap_ci and n >= N_MIN_BOOTSTRAP:
        rng = np.random.default_rng(42)
        A_vals, R_vals = [], []
        for _ in range(N_BOOTSTRAP):
            idx = rng.choice(n, size=n, replace=True)
            a, _, r, _, _, _, _, _ = _compute_tensor_and_R_internal(dt[idx], dp[idx], w[idx], standardize)
            if np.isfinite(a):
                A_vals.append(a)
            if np.isfinite(r):
                R_vals.append(r)
        if A_vals:
            A_lo, A_hi = float(np.percentile(A_vals, 2.5)), float(np.percentile(A_vals, 97.5))
        if R_vals:
            R_lo, R_hi = float(np.percentile(R_vals, 2.5)), float(np.percentile(R_vals, 97.5))
    return Metrics(
        D=D, tau=tau, A_tensor=A_tensor, mu=mu, R=R,
        n=int(n), weight_sum=float(np.sum(w)),
        A_tensor_ci_lo=A_lo, A_tensor_ci_hi=A_hi, R_ci_lo=R_lo, R_ci_hi=R_hi,
        lambda1=lam1, lambda2=lam2,
        mu_axis=mu, cos_mu=cos_mu, sin_mu=sin_mu, mu_doubled_angle=mu_da,
    )


def _compute_weighted_aggregate(parts: List[Metrics]) -> Metrics:
    """Média ponderada de métricas (núcleo de 2A)."""
    parts = [m for m in parts if m.n > 0 and np.isfinite(m.weight_sum)]
    if not parts:
        return Metrics(D=np.nan, tau=np.nan, A_tensor=np.nan, mu=np.nan, R=np.nan, n=0, weight_sum=0.0)
    W = np.array([m.weight_sum for m in parts], dtype=float)
    W = np.where(W > 0, W, 0.0)
    if float(np.sum(W)) <= 0:
        W = np.ones_like(W)

    def wmean(attr: str) -> float:
        x = np.array([getattr(m, attr) for m in parts], dtype=float)
        ok = np.isfinite(x)
        if not np.any(ok):
            return np.nan
        return float(np.sum(W[ok] * x[ok]) / np.sum(W[ok]))

    mu_vals = np.array([m.mu for m in parts], dtype=float)
    ok_mu = np.isfinite(mu_vals)
    if np.any(ok_mu):
        C = np.sum(W[ok_mu] * np.cos(mu_vals[ok_mu])) / np.sum(W[ok_mu])
        S = np.sum(W[ok_mu] * np.sin(mu_vals[ok_mu])) / np.sum(W[ok_mu])
        mu = float(math.atan2(S, C))
    else:
        mu = np.nan
    n_tot = int(np.sum([m.n for m in parts]))
    w_tot = float(np.sum(W))
    return Metrics(
        D=wmean("D"), tau=wmean("tau"), A_tensor=wmean("A_tensor"),
        mu=mu, R=wmean("R"), n=n_tot, weight_sum=w_tot,
    )


def aggregate_2A(
    metrics_by_part: Dict[str, Metrics],
    bootstrap_ci: bool = False,
) -> Metrics:
    """2A: média ponderada por instrumento. bootstrap_ci quando ≥2 instrumentos."""
    valid = [(k, m) for k, m in metrics_by_part.items() if m.n > 0 and np.isfinite(m.weight_sum)]
    if not valid:
        return Metrics(D=np.nan, tau=np.nan, A_tensor=np.nan, mu=np.nan, R=np.nan, n=0, weight_sum=0.0)
    parts = [m for _, m in valid]
    m = _compute_weighted_aggregate(parts)
    A_lo, A_hi, R_lo, R_hi = np.nan, np.nan, np.nan, np.nan
    if bootstrap_ci and len(valid) >= 2:
        rng = np.random.default_rng(42)
        A_vals, R_vals = [], []
        for _ in range(N_BOOTSTRAP):
            idx = rng.choice(len(parts), size=len(parts), replace=True)
            resampled = [parts[i] for i in idx]
            mb = _compute_weighted_aggregate(resampled)
            if np.isfinite(mb.A_tensor):
                A_vals.append(mb.A_tensor)
            if np.isfinite(mb.R):
                R_vals.append(mb.R)
        if A_vals:
            A_lo, A_hi = float(np.percentile(A_vals, 2.5)), float(np.percentile(A_vals, 97.5))
        if R_vals:
            R_lo, R_hi = float(np.percentile(R_vals, 2.5)), float(np.percentile(R_vals, 97.5))
        m.A_tensor_ci_lo = A_lo
        m.A_tensor_ci_hi = A_hi
        m.R_ci_lo = R_lo
        m.R_ci_hi = R_hi
    return m


def compute_directional_conflict(metrics_by_part: Dict[str, object]) -> float:
    """
    Directional conflict between instruments in window w.
    Conflito(w) = 1 - R_inst(w), where R_inst = weighted circular resultant of μ(j,w).
    High conflict: layers in different directions. Low: coherent global orientation.

    Weights W_j,w = weight_sum (sum of transition weights) per instrument.
    """
    valid = [(k, m) for k, m in metrics_by_part.items()
             if hasattr(m, 'mu') and hasattr(m, 'weight_sum')
             and m.n > 0 and np.isfinite(m.weight_sum) and np.isfinite(m.mu)]
    if not valid:
        return np.nan
    W = np.array([m.weight_sum for _, m in valid], dtype=float)
    mu = np.array([m.mu for _, m in valid], dtype=float)
    W_sum = np.sum(W)
    if W_sum <= 0:
        return np.nan
    C = np.sum(W * np.cos(mu)) / W_sum
    S = np.sum(W * np.sin(mu)) / W_sum
    R_inst = float(np.sqrt(C * C + S * S))
    return float(1.0 - R_inst)


def aggregate_2B(
    transitions_by_part: Dict[str, pd.DataFrame],
    time_axis: str,
    weight_mode: str,
    standardize: bool | str = True,
    bootstrap_ci: bool = False,
) -> Metrics:
    """2B: pool global de transições."""
    dfs = [df for df in transitions_by_part.values() if df is not None and not df.empty]
    if not dfs:
        return Metrics(D=np.nan, tau=np.nan, A_tensor=np.nan, mu=np.nan, R=np.nan, n=0, weight_sum=0.0)
    pooled = pd.concat(dfs, axis=0, ignore_index=True)
    return compute_metrics_from_transitions(
        pooled, time_axis=time_axis, weight_mode=weight_mode,
        standardize=standardize, bootstrap_ci=bootstrap_ci,
    )
