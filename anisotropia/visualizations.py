"""
Strong visualizations: flow map (quiver), tensor ellipses, polar histogram (Rose diagram).

Scientific basis: tensor ellipses use real eigenvalues (λ₁, λ₂) when available.
Fallback: normalized shape (λ₁+λ₂=1) preserves anisotropy ratio. See MANUAL_METRICAS.md.

Temporal ordering: all multi-window plots use win_order for chronological display.
Subset control: optional windows/parts parameters restrict which data are shown.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse
    from matplotlib import rcParams
    from matplotlib.ticker import FuncFormatter, MaxNLocator
except ImportError:
    mpl = None
    plt = None
    rcParams = None
    FuncFormatter = None  # type: ignore[misc, assignment]
    MaxNLocator = None  # type: ignore[misc, assignment]

from music21 import pitch as m21_pitch

# ---------------------------------------------------------------------------
# Publication-style theme (matplotlib rc_context)
# ---------------------------------------------------------------------------
RC_PROFESSIONAL: Dict[str, object] = {
    "figure.facecolor": "#FAFBFC",
    # Slightly below matplotlib default so Streamlit on-screen PNGs are not oversized.
    "figure.dpi": 96,
    "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.9,
    "axes.grid": True,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "-",
    "grid.linewidth": 0.7,
    "grid.alpha": 1.0,
    "xtick.color": "#475569",
    "ytick.color": "#475569",
    "text.color": "#0F172A",
    "axes.labelcolor": "#334155",
    "axes.titleweight": "semibold",
    "axes.titlesize": 11.5,
    "axes.labelsize": 10,
    "font.size": 10,
    "legend.fontsize": 9,
    "legend.frameon": True,
    "legend.framealpha": 0.96,
    "legend.edgecolor": "#E2E8F0",
    "legend.fancybox": False,
    "figure.titlesize": 13,
    "figure.titleweight": "semibold",
}

# Color-blind–friendly accent palette (Okabe–Ito–inspired + slate)
PROFESSIONAL_COLORS = {
    "ink": "#0F172A",
    "slate": "#475569",
    "muted": "#64748B",
    "border": "#CBD5E1",
    "track": "#E2E8F0",
    "fill_strong": "#2563EB",
    "fill_soft": "#93C5FD",
    "fill_ci": "#BFDBFE",
    "rose": "#0369A1",
    "rose_edge": "#0C4A6E",
    "ellipse_fill": "#38BDF8",
    "ellipse_edge": "#0369A1",
    "conflict": "#DC2626",
    "accent_1": "#0072B2",
    "accent_2": "#D55E00",
    "accent_3": "#009E73",
    "accent_4": "#CC79A7",
    "diverging_bad": "#94A3B8",
}

# Figure sizes (inches) tuned for Streamlit: avoid huge bitmaps and full-width stretch.
FIG_EMPTY_W, FIG_EMPTY_H = 5.6, 3.2
# Flow map: cap size; gentler growth per window / part than original (0.85 / 0.45).
FIG_FLOW_MAX_W, FIG_FLOW_MAX_H = 11.0, 6.5


@contextmanager
def professional_rc() -> Iterator[None]:
    """Use matplotlib settings tuned for clean, publication-style figures."""
    if plt is None:
        yield
        return
    with plt.rc_context(RC_PROFESSIONAL):
        yield


def _spines_minimal(ax) -> None:
    """Hide top/right; soften remaining spines."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(PROFESSIONAL_COLORS["border"])
        ax.spines[s].set_linewidth(0.9)


def _style_axes(ax) -> None:
    """Cartesian axes: light background, minimal spines."""
    if ax is None:
        return
    ax.set_facecolor("#FFFFFF")
    _spines_minimal(ax)
    ax.tick_params(colors=PROFESSIONAL_COLORS["slate"], labelsize=9, width=0.8, length=4)
    if ax.get_ylabel():
        ax.yaxis.get_label().set_color(PROFESSIONAL_COLORS["ink"])


def _style_axes_grid(ax) -> None:
    """Axes that keep full grid (e.g. flow map)."""
    if ax is None:
        return
    ax.set_facecolor("#F8FAFC")
    for spine in ax.spines.values():
        spine.set_color(PROFESSIONAL_COLORS["border"])
        spine.set_linewidth(0.8)
    ax.tick_params(colors=PROFESSIONAL_COLORS["slate"], labelsize=9)
    ax.grid(True, color="#E2E8F0", linestyle="-", linewidth=0.6, alpha=1.0)


def _style_polar(ax) -> None:
    ax.set_facecolor("#FAFBFC")
    ax.grid(color="#CBD5E1", linestyle="-", linewidth=0.65, alpha=0.85)
    ax.tick_params(colors=PROFESSIONAL_COLORS["slate"], labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(PROFESSIONAL_COLORS["border"])


def _scope_colors() -> List[str]:
    return [
        PROFESSIONAL_COLORS["accent_1"],
        PROFESSIONAL_COLORS["accent_2"],
        PROFESSIONAL_COLORS["accent_3"],
        PROFESSIONAL_COLORS["accent_4"],
    ]


def flow_map_quiver(
    df_instruments: pd.DataFrame,
    win_order: Dict[str, int],
    *,
    arrow_scale: Optional[float] = 0.6,
    windows: Optional[List[str]] = None,
    parts: Optional[List[str]] = None,
) -> "plt.Figure":
    """
    Flow map (quiver): time × instrument.
    x = window index, y = instrument. Arrow: angle μ, length = A, color = D.

    arrow_scale: max arrow length in cell units (0.5 = half cell). None = auto from data.
    windows, parts: optional subsets; None = all.
    """
    if plt is None:
        raise ImportError("matplotlib required")
    with professional_rc():
        all_parts = df_instruments["part"].unique().tolist()
        all_windows = sorted(win_order.keys(), key=lambda w: win_order[w])
        parts = parts if parts is not None else all_parts
        windows = windows if windows is not None else all_windows
        windows = sorted([w for w in all_windows if w in windows], key=lambda w: win_order.get(w, -1))
        parts = [p for p in all_parts if p in parts]
        n_win = len(windows)
        n_part = len(parts)
        if n_win == 0 or n_part == 0:
            fig, ax = plt.subplots(figsize=(FIG_EMPTY_W, FIG_EMPTY_H))
            fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
            ax.text(
                0.5, 0.5, "No data",
                ha="center", va="center", fontsize=11, color=PROFESSIONAL_COLORS["muted"],
            )
            ax.axis("off")
            return fig
        win_to_idx = {w: i for i, w in enumerate(windows)}
        part_to_idx = {p: i for i, p in enumerate(parts)}
        X, Y = np.meshgrid(np.arange(n_win), np.arange(n_part))
        U = np.zeros_like(X, dtype=float)
        V = np.zeros_like(X, dtype=float)
        C_arr = np.full_like(X, np.nan, dtype=float)
        for _, row in df_instruments.iterrows():
            if row["window"] not in win_to_idx or row["part"] not in part_to_idx:
                continue
            wi = win_to_idx[row["window"]]
            pi = part_to_idx[row["part"]]
            mu = row.get("mu")
            A = row.get("A_tensor", 0)
            D = row.get("D", 0)
            if np.isfinite(mu) and np.isfinite(A):
                U[pi, wi] = A * np.cos(mu)
                V[pi, wi] = A * np.sin(mu)
            if np.isfinite(D):
                C_arr[pi, wi] = (float(D) + 1) / 2
        valid_C = np.isfinite(C_arr)
        C_plot = np.ma.masked_where(~valid_C, np.where(valid_C, C_arr, 0.0))
        fw = min(FIG_FLOW_MAX_W, max(5.8, n_win * 0.52))
        fh = min(FIG_FLOW_MAX_H, max(3.0, n_part * 0.28))
        fig, ax = plt.subplots(figsize=(fw, fh))
        fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
        _style_axes_grid(ax)
        mag = np.sqrt(U * U + V * V)
        max_mag = float(np.nanmax(mag)) if np.any(np.isfinite(mag)) else 1.0
        if max_mag <= 0:
            max_mag = 1.0
        scale_val = arrow_scale if arrow_scale is not None else 0.6
        quiver_scale = max_mag / max(scale_val, 0.01)
        if np.any(valid_C):
            cmap = plt.cm.RdBu_r.copy()
            cmap.set_bad(color=PROFESSIONAL_COLORS["diverging_bad"], alpha=0.45)
            Q = ax.quiver(
                X, Y, U, V, C_plot, cmap=cmap,
                scale=quiver_scale, scale_units="xy", angles="xy", pivot="mid",
                minlength=0.05, width=0.006, headwidth=3.2, headlength=4,
            )
            cbar = plt.colorbar(Q, ax=ax, shrink=0.82, pad=0.02, aspect=22)
            cbar.set_label("Drift D (down ← 0 → up)", fontsize=9, color=PROFESSIONAL_COLORS["ink"])
            cbar.ax.tick_params(labelsize=8, colors=PROFESSIONAL_COLORS["slate"])
            cbar.outline.set_edgecolor(PROFESSIONAL_COLORS["border"])
        else:
            ax.quiver(
                X, Y, U, V, color=PROFESSIONAL_COLORS["slate"],
                scale=quiver_scale, scale_units="xy", angles="xy", pivot="mid", minlength=0.05,
                width=0.006,
            )
        ax.set_xticks(np.arange(n_win))
        ax.set_xticklabels(windows, rotation=40, ha="right", fontsize=8)
        ax.set_yticks(np.arange(n_part))
        ax.set_yticklabels(parts, fontsize=8)
        ax.set_xlabel("Window", fontsize=10, color=PROFESSIONAL_COLORS["ink"])
        ax.set_ylabel("Instrument", fontsize=10, color=PROFESSIONAL_COLORS["ink"])
        ax.set_title(
            "Directional flow map  ·  angle = μ, length ∝ A_tensor, colour = D",
            fontsize=11.5, pad=10, color=PROFESSIONAL_COLORS["ink"],
        )
        fig.tight_layout()
        return fig


def tensor_ellipse_from_metrics(
    A: float,
    mu: float,
    scale: float = 0.4,
    lam1: Optional[float] = None,
    lam2: Optional[float] = None,
) -> Tuple[float, float, float]:
    """
    Return (width, height, angle_deg) for ellipse.
    Major axis ∝ √λ₁, minor ∝ √λ₂, rotation = μ.

    When lam1, lam2 are provided and finite: use real eigenvalues from J.
    Otherwise: normalized shape λ₁=(1+A)/2, λ₂=(1-A)/2 (unit trace), preserving
    anisotropy ratio. Scale is arbitrary for display.
    """
    if not np.isfinite(A) or not np.isfinite(mu):
        return 0, 0, 0
    if lam1 is not None and lam2 is not None and np.isfinite(lam1) and np.isfinite(lam2) and (lam1 + lam2) > 0:
        l1, l2 = max(lam1, 1e-10), max(lam2, 1e-10)
    else:
        l1 = max((1 + A) / 2, 1e-6)
        l2 = max((1 - A) / 2, 1e-6)
    w = 2 * np.sqrt(l1) * scale
    h = 2 * np.sqrt(l2) * scale
    return w, h, float(np.degrees(mu))


def plot_tensor_ellipses(
    df_totals: pd.DataFrame,
    win_order: Dict[str, int],
    *,
    windows: Optional[List[str]] = None,
) -> "plt.Figure":
    """
    Tensor ellipses: for each window, J as ellipse.
    Major axis ∝ √λ₁, minor ∝ √λ₂, rotation = μ.
    Uses real λ when available (aggregates use normalized shape).
    windows: optional subset; None = all (ordered by win_order).
    """
    if plt is None:
        raise ImportError("matplotlib required")
    with professional_rc():
        all_windows = sorted(win_order.keys(), key=lambda w: win_order[w])
        windows = windows if windows is not None else all_windows
        windows = sorted([w for w in all_windows if w in windows], key=lambda w: win_order.get(w, -1))
        n = len(windows)
        if n == 0:
            fig, ax = plt.subplots(figsize=(FIG_EMPTY_W, FIG_EMPTY_H))
            fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
            ax.set_facecolor("#F1F5F9")
            return fig
        cols = min(4, max(1, n))
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(2.65 * cols + 0.35, 2.65 * rows + 0.55))
        fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
        if rows == 1 and cols == 1:
            axes_flat = [axes]
        else:
            axes_flat = axes.flatten()
        for idx, win in enumerate(windows):
            ax = axes_flat[idx]
            match = df_totals[df_totals["window"] == win]
            row = match.iloc[0] if len(match) > 0 else None
            if row is not None:
                A, mu = row.get("A_tensor"), row.get("mu")
                lam1 = row.get("lambda1")
                lam2 = row.get("lambda2")
                lam1 = float(lam1) if (isinstance(lam1, (int, float)) and np.isfinite(lam1)) else None
                lam2 = float(lam2) if (isinstance(lam2, (int, float)) and np.isfinite(lam2)) else None
                w, h, ang = tensor_ellipse_from_metrics(
                    float(A) if np.isfinite(A) else 0,
                    float(mu) if np.isfinite(mu) else 0,
                    lam1=lam1,
                    lam2=lam2,
                )
                if w > 0 or h > 0:
                    ell = Ellipse(
                        (0.5, 0.5), w, h, angle=ang,
                        facecolor=PROFESSIONAL_COLORS["ellipse_fill"],
                        edgecolor=PROFESSIONAL_COLORS["ellipse_edge"],
                        linewidth=1.6, alpha=0.88, zorder=3,
                    )
                    ax.add_patch(ell)
            ax.set_facecolor("#F1F5F9")
            pad = 0.08
            ax.set_xlim(-pad, 1 + pad)
            ax.set_ylim(-pad, 1 + pad)
            ax.set_aspect("equal")
            ax.set_title(str(win), fontsize=9.5, fontweight="semibold", color=PROFESSIONAL_COLORS["ink"])
            ax.axis("off")
        for idx in range(n, len(axes_flat)):
            axes_flat[idx].axis("off")
        fig.suptitle(
            "Structure tensor as ellipses  ·  major ∝ √λ₁, minor ∝ √λ₂, rotation = μ",
            fontsize=12.5, y=1.02, color=PROFESSIONAL_COLORS["ink"],
        )
        fig.tight_layout()
        return fig


def plot_tensor_ellipses_per_instrument(
    df_instruments: pd.DataFrame,
    win_order: Dict[str, int],
    *,
    max_plots: int = 12,
    windows: Optional[List[str]] = None,
    parts: Optional[List[str]] = None,
) -> "plt.Figure":
    """
    Tensor ellipses per instrument per window (when ≥2 instruments).
    Uses real λ from J when available.
    windows, parts: optional subsets; None = all. max_plots limits total cells shown.
    """
    if plt is None:
        raise ImportError("matplotlib required")
    with professional_rc():
        all_parts = df_instruments["part"].unique().tolist()
        all_windows = sorted(win_order.keys(), key=lambda w: win_order[w])
        parts = parts if parts is not None else all_parts
        windows = windows if windows is not None else all_windows
        parts = [p for p in all_parts if p in parts]
        windows = sorted([w for w in all_windows if w in windows], key=lambda w: win_order.get(w, -1))
        n_cells = len(parts) * len(windows)
        if n_cells == 0:
            fig, ax = plt.subplots(figsize=(FIG_EMPTY_W, FIG_EMPTY_H))
            fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
            ax.set_facecolor("#F1F5F9")
            return fig
        n_show = min(n_cells, max_plots)
        cols = min(4, max(1, len(windows)), max_plots)
        rows = min((n_show + cols - 1) // cols, 8)
        fig, axes = plt.subplots(rows, cols, figsize=(2.55 * cols + 0.32, 2.35 * rows + 0.45))
        fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
        if rows == 1 and cols == 1:
            axes_flat = [axes]
        else:
            axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
        plot_idx = 0
        for win in windows:
            if plot_idx >= n_show:
                break
            for part in parts:
                if plot_idx >= len(axes_flat):
                    break
                ax = axes_flat[plot_idx]
                match = df_instruments[(df_instruments["window"] == win) & (df_instruments["part"] == part)]
                row = match.iloc[0] if len(match) > 0 else None
                if row is not None:
                    A, mu = row.get("A_tensor"), row.get("mu")
                    lam1 = row.get("lambda1")
                    lam2 = row.get("lambda2")
                    lam1 = float(lam1) if (isinstance(lam1, (int, float)) and np.isfinite(lam1)) else None
                    lam2 = float(lam2) if (isinstance(lam2, (int, float)) and np.isfinite(lam2)) else None
                    w, h, ang = tensor_ellipse_from_metrics(
                        float(A) if np.isfinite(A) else 0,
                        float(mu) if np.isfinite(mu) else 0,
                        lam1=lam1,
                        lam2=lam2,
                    )
                    if w > 0 or h > 0:
                        ell = Ellipse(
                            (0.5, 0.5), w, h, angle=ang,
                            facecolor=PROFESSIONAL_COLORS["ellipse_fill"],
                            edgecolor=PROFESSIONAL_COLORS["ellipse_edge"],
                            linewidth=1.4, alpha=0.88, zorder=3,
                        )
                        ax.add_patch(ell)
                ax.set_facecolor("#F1F5F9")
                pad = 0.08
                ax.set_xlim(-pad, 1 + pad)
                ax.set_ylim(-pad, 1 + pad)
                ax.set_aspect("equal")
                ax.set_title(f"{part}\n{win}", fontsize=8.5, color=PROFESSIONAL_COLORS["ink"])
                ax.axis("off")
                plot_idx += 1
        for idx in range(plot_idx, len(axes_flat)):
            axes_flat[idx].axis("off")
        fig.suptitle(
            "Per-instrument tensor ellipses",
            fontsize=12.5, y=1.01, color=PROFESSIONAL_COLORS["ink"],
        )
        fig.tight_layout()
        return fig


def plot_rose_diagram(
    df_trans: pd.DataFrame,
    time_axis: str = "ql",
    n_bins: int = 24,
    per_window: bool = False,
    trans_by_window: Optional[Dict[str, pd.DataFrame]] = None,
    win_order: Optional[Dict[str, int]] = None,
    *,
    max_windows: int = 9,
    windows: Optional[List[str]] = None,
) -> "plt.Figure":
    """
    Polar histogram (Rose diagram) of θᵢ = arctan2(Δpᵢ, Δtᵢ).
    Narrow peaks → strong anisotropy. Circular → isotropy.

    When per_window=True and trans_by_window provided: one Rose per window (ODF per segment).
    win_order: for temporal ordering of windows. windows: optional subset. max_windows: limit.
    """
    if plt is None:
        raise ImportError("matplotlib required")
    with professional_rc():
        dt_col = "dt_ql" if time_axis == "ql" else "dt_sec"
        if per_window and trans_by_window and len(trans_by_window) > 1:
            all_wins = list(trans_by_window.keys())
            sort_key = (lambda w: win_order.get(w, -1)) if win_order else (lambda w: w)
            all_wins = sorted(all_wins, key=sort_key)
            subset = windows if windows is not None else all_wins
            wins = sorted([w for w in all_wins if w in subset], key=sort_key)[:max_windows]
            n = len(wins)
            if n > 0:
                cols = 3
                rows = (n + cols - 1) // cols
                fig, axes = plt.subplots(
                    rows, cols, subplot_kw=dict(projection="polar"),
                    figsize=(2.75 * cols + 0.2, 2.75 * rows + 0.35),
                )
                fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
                axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
                for idx, win in enumerate(wins):
                    ax = axes_flat[idx]
                    _style_polar(ax)
                    dfw = trans_by_window[win]
                    if dt_col in dfw.columns and "dp" in dfw.columns:
                        dff = dfw[dfw[dt_col] > 0]
                        if not dff.empty:
                            theta = np.arctan2(dff["dp"].values, dff[dt_col].values)
                            bins = np.linspace(-np.pi, np.pi, n_bins + 1)
                            hist, _ = np.histogram(theta, bins=bins)
                            width = 2 * np.pi / n_bins
                            ax.bar(
                                bins[:-1] + width / 2, hist, width=width * 0.92, bottom=0,
                                color=PROFESSIONAL_COLORS["rose"], alpha=0.88,
                                edgecolor=PROFESSIONAL_COLORS["rose_edge"], linewidth=0.45,
                            )
                    ax.set_title(str(win), fontsize=9, pad=10, color=PROFESSIONAL_COLORS["ink"])
                for idx in range(n, len(axes_flat)):
                    axes_flat[idx].axis("off")
                fig.suptitle(
                    "Rose diagrams (θ = arctan2(Δp, Δt))  ·  narrow peaks → anisotropy",
                    fontsize=12, y=1.02, color=PROFESSIONAL_COLORS["ink"],
                )
                fig.tight_layout()
                return fig
        if dt_col not in df_trans.columns or "dp" not in df_trans.columns:
            fig, ax = plt.subplots(subplot_kw=dict(projection="polar"), figsize=(4.0, 4.0))
            fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
            _style_polar(ax)
            ax.set_title("Rose diagram — no data", fontsize=11, pad=16, color=PROFESSIONAL_COLORS["muted"])
            return fig
        dff = df_trans[df_trans[dt_col] > 0].copy()
        if dff.empty:
            fig, ax = plt.subplots(subplot_kw=dict(projection="polar"), figsize=(4.0, 4.0))
            fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
            _style_polar(ax)
            ax.set_title("Rose diagram — no valid transitions", fontsize=11, pad=16, color=PROFESSIONAL_COLORS["muted"])
            return fig
        theta = np.arctan2(dff["dp"].values, dff[dt_col].values)
        bins = np.linspace(-np.pi, np.pi, n_bins + 1)
        hist, _ = np.histogram(theta, bins=bins)
        width = 2 * np.pi / n_bins
        fig, ax = plt.subplots(subplot_kw=dict(projection="polar"), figsize=(4.1, 4.1))
        fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
        _style_polar(ax)
        ax.bar(
            bins[:-1] + width / 2, hist, width=width * 0.92, bottom=0,
            color=PROFESSIONAL_COLORS["rose"], alpha=0.88,
            edgecolor=PROFESSIONAL_COLORS["rose_edge"], linewidth=0.45,
        )
        n_obs = len(dff)
        ax.set_title(
            f"Rose diagram  ·  θ = arctan2(Δp, Δt)  ·  n={n_obs}",
            fontsize=11.5,
            pad=20,
            color=PROFESSIONAL_COLORS["ink"],
        )
        return fig


def _pitch_tick_note_name(value: float, _pos: Optional[int] = None) -> str:
    """Format a Y-axis tick (MIDI, typically integer) as note name + octave."""
    if not np.isfinite(value):
        return ""
    try:
        p = m21_pitch.Pitch()
        p.midi = round(float(value))
        return p.nameWithOctave
    except Exception:
        return str(int(round(value)))


def plot_pitch_over_time(
    events_by_part: "Dict[str, List]",
    has_seconds: bool = True,
    *,
    parts: Optional[List[str]] = None,
    alpha: float = 0.92,
    melodic_skeleton: bool = True,
) -> "plt.Figure":
    """
    Pitch-over-time: one line per instrument.
    X-axis: time (seconds if has_seconds else quarterLength).
    Y-axis: pitch as note names with octave (positions still in MIDI for spacing).

    If ``melodic_skeleton`` is True (default), expects caller to pass **one onset per
    (voice, time)** (e.g. collapsed chord slices) so lines do not fake arpeggio paths
    through simultaneous chord tones. Pass raw expanded events only for diagnostics.
    """
    if melodic_skeleton:
        try:
            from anisotropia.transitions import melodic_skeleton_for_plot

            events_by_part = {k: melodic_skeleton_for_plot(v) for k, v in events_by_part.items()}
        except Exception:
            pass
    if plt is None:
        raise ImportError("matplotlib required")
    with professional_rc():
        all_parts = list(events_by_part.keys())
        parts = parts if parts is not None else all_parts
        parts = [p for p in parts if p in events_by_part and events_by_part[p]]
        if not parts:
            fig, ax = plt.subplots(figsize=(7.2, 3.5))
            fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
            ax.set_facecolor("#FFFFFF")
            ax.text(
                0.5, 0.5, "No event data",
                ha="center", va="center", fontsize=11, color=PROFESSIONAL_COLORS["muted"],
                transform=ax.transAxes,
            )
            ax.axis("off")
            return fig
        n = len(parts)
        _name = "tab10" if n <= 10 else "tab20"
        if mpl is not None and hasattr(mpl, "colormaps"):
            _cmap = mpl.colormaps[_name]
        else:
            _cmap = plt.cm.get_cmap(_name)
        colors = [_cmap(i / max(n - 1, 1)) for i in range(n)]
        fig, ax = plt.subplots(figsize=(7.8, 3.9))
        fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
        _style_axes(ax)
        x_label = "Time (s)" if has_seconds else "Time (quarter lengths)"
        ax.set_xlabel(x_label)
        ax.set_ylabel("Pitch (note names)")
        ax.set_title(
            "Pitch–time (melodic skeleton · one point per onset & voice)",
            fontsize=12,
            pad=10,
        )
        for i, part in enumerate(parts):
            evs = events_by_part[part]
            x = [e.t if has_seconds else e.ql for e in evs]
            y = [e.p for e in evs]
            if not x:
                continue
            c = colors[i]
            ax.plot(
                x, y, "-", color=c, label=part, alpha=alpha, linewidth=1.65,
                marker="o", markersize=2.8, markerfacecolor=c, markeredgecolor="white", markeredgewidth=0.35,
            )
        if FuncFormatter is not None and MaxNLocator is not None:
            ax.yaxis.set_major_locator(MaxNLocator(nbins=12, integer=True, min_n_ticks=4))
            ax.yaxis.set_major_formatter(FuncFormatter(_pitch_tick_note_name))
        leg = ax.legend(
            loc="upper left", bbox_to_anchor=(1.02, 1), framealpha=0.97, fontsize=8.5,
            borderpad=0.6, labelspacing=0.35,
        )
        leg.get_frame().set_edgecolor(PROFESSIONAL_COLORS["border"])
        fig.tight_layout(rect=[0, 0, 0.82, 1])
        return fig


def plot_time_curves(
    df_totals: pd.DataFrame,
    win_order: Dict[str, int],
    *,
    windows: Optional[List[str]] = None,
) -> "plt.Figure":
    """
    Time curves for report: A(w), sin μ(w), cos μ(w), D(w).
    sin/cos μ avoid jumps from periodicity.
    windows: optional subset; None = all (ordered by win_order).
    """
    if plt is None:
        raise ImportError("matplotlib required")
    with professional_rc():
        df = df_totals.copy()
        all_win_labels = sorted(df["window"].drop_duplicates().tolist(), key=lambda w: win_order.get(w, -1))
        win_labels = windows if windows is not None else all_win_labels
        win_labels = sorted([w for w in all_win_labels if w in win_labels], key=lambda w: win_order.get(w, -1))
        df = df[df["window"].isin(win_labels)]
        df["win_idx"] = df["window"].map(win_order)
        df = df.sort_values("win_idx")
        fig, axes = plt.subplots(4, 1, figsize=(7.2, 7.4), sharex=True)
        fig.patch.set_facecolor(RC_PROFESSIONAL["figure.facecolor"])
        palette = _scope_colors()
        scopes = list(df["scope"].unique())
        scope_color = {s: palette[i % len(palette)] for i, s in enumerate(scopes)}
        for ax in axes:
            _style_axes(ax)
        for scope in scopes:
            tdf = df[df["scope"] == scope].sort_values("win_idx")
            if tdf.empty:
                continue
            col = scope_color[scope]
            x = tdf["win_idx"].to_numpy()
            axes[0].plot(x, tdf["A_tensor"], "o-", label=scope, color=col, linewidth=2, markersize=5)
            axes[1].plot(x, np.sin(tdf["mu"].astype(float)), "o-", label=scope, color=col, linewidth=2, markersize=5)
            axes[2].plot(x, np.cos(tdf["mu"].astype(float)), "o-", label=scope, color=col, linewidth=2, markersize=5)
            axes[3].plot(x, tdf["D"], "o-", label=scope, color=col, linewidth=2, markersize=5)
        titles = [
            ("A_tensor (w)", "Tensor anisotropy"),
            ("sin μ (w)", "sin μ — avoids 2π discontinuities"),
            ("cos μ (w)", "cos μ"),
            ("D (w)", "Drift"),
        ]
        for i, (ylab, sub) in enumerate(titles):
            axes[i].set_ylabel(ylab, fontsize=10)
            axes[i].set_title(sub, fontsize=10.5, loc="left", color=PROFESSIONAL_COLORS["muted"])
            leg = axes[i].legend(loc="upper right", fontsize=8.5, framealpha=0.96)
            leg.get_frame().set_edgecolor(PROFESSIONAL_COLORS["border"])
            axes[i].grid(True, color="#EEF2F7", linestyle="-", linewidth=0.7)
        axes[3].set_xlabel("Window index", fontsize=10)
        xticks = np.arange(len(win_labels))
        if len(xticks) <= 20:
            axes[3].set_xticks(xticks)
            axes[3].set_xticklabels(win_labels, rotation=42, ha="right", fontsize=8)
        fig.suptitle("Metrics along windows", fontsize=13, y=1.01, color=PROFESSIONAL_COLORS["ink"])
        fig.tight_layout()
        return fig
