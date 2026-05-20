"""
Transition ontology: separate horizontal (melodic / temporal) moves from vertical (simultaneity-internal).

Default path builds the main directional field from **horizontal** transitions only
(dt strictly above epsilon in the active time units). Legacy mixed mode preserves the
previous stagger+global sort behaviour for backward compatibility.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple

import numpy as np
import pandas as pd

from anisotropia.parsing import EPSILON, Event, transitions_from_events

TransitionOntology = Literal["horizontal", "vertical", "legacy_mixed"]


@dataclass
class TransitionBuildResult:
    """Outputs of :func:`build_directional_transition_tables`."""

    horizontal: pd.DataFrame
    vertical: pd.DataFrame
    stats: Dict[str, Any]


def _voice(ev: Event) -> int:
    return int(getattr(ev, "voice", 1) or 1)


def _collapse_onsets_per_voice(evs: List[Event]) -> List[Event]:
    """
    One representative Event per (voice, ql): centroid pitch, max duration.
    Preserves temporal order for melodic chaining.
    """
    if not evs:
        return []
    by_v: Dict[int, List[Event]] = defaultdict(list)
    for e in evs:
        by_v[_voice(e)].append(e)
    out: List[Event] = []
    for vid in sorted(by_v.keys()):
        lst = sorted(by_v[vid], key=lambda x: (x.ql, x.p))
        i = 0
        while i < len(lst):
            j = i + 1
            same_ql = [lst[i]]
            while j < len(lst) and abs(lst[j].ql - lst[i].ql) < EPSILON:
                same_ql.append(lst[j])
                j += 1
            if len(same_ql) == 1:
                out.append(same_ql[0])
            else:
                p_cent = float(np.mean([x.p for x in same_ql]))
                dur_m = float(max(x.dur_ql for x in same_ql))
                out.append(
                    Event(
                        t=same_ql[0].t,
                        ql=same_ql[0].ql,
                        dur_ql=dur_m,
                        p=p_cent,
                        meas=same_ql[0].meas,
                        voice=vid,
                        is_chord_tone=len(same_ql) > 1,
                        is_unpitched=any(getattr(x, "is_unpitched", False) for x in same_ql),
                    )
                )
            i = j
    out.sort(key=lambda e: (e.ql, _voice(e), e.p))
    return out


def _pairs_from_melodic_chain(collapsed: List[Event], *, has_seconds: bool) -> List[Dict[str, Any]]:
    """Consecutive pairs along one voice timeline (collapsed already per voice)."""
    rows: List[Dict[str, Any]] = []
    by_v: Dict[int, List[Event]] = defaultdict(list)
    for e in collapsed:
        by_v[_voice(e)].append(e)
    for vid in sorted(by_v.keys()):
        chain = sorted(by_v[vid], key=lambda x: (x.ql, x.p))
        for a, b in zip(chain[:-1], chain[1:]):
            dt_ql = float(b.ql - a.ql)
            dt_sec = float(b.t - a.t) if has_seconds else dt_ql
            dp = float(b.p - a.p)
            w_dur = max(a.dur_ql, 0.0)
            dt_for_w = dt_ql if dt_ql > 0 else a.dur_ql
            w_min = max(min(a.dur_ql, dt_for_w), 0.0)
            rows.append(
                dict(
                    ql=a.ql,
                    t=a.t,
                    meas=a.meas,
                    dp=dp,
                    dt_ql=dt_ql,
                    dt_sec=dt_sec,
                    w_dur=w_dur,
                    w_min=w_min,
                    voice=vid,
                    transition_kind="horizontal",
                )
            )
    return rows


def _vertical_pairs_from_expanded(evs: List[Event], *, has_seconds: bool) -> List[Dict[str, Any]]:
    """Within same (voice, ql), all ordered pitch pairs (chord-internal). dt = 0."""
    by_key: Dict[Tuple[int, float], List[Event]] = defaultdict(list)
    for e in evs:
        by_key[(_voice(e), float(e.ql))].append(e)
    rows: List[Dict[str, Any]] = []
    for (vid, ql), group in sorted(by_key.items()):
        group = sorted(group, key=lambda x: x.p)
        if len(group) < 2:
            continue
        for i in range(len(group) - 1):
            a, b = group[i], group[i + 1]
            rows.append(
                dict(
                    ql=a.ql,
                    t=a.t,
                    meas=a.meas,
                    dp=float(b.p - a.p),
                    dt_ql=0.0,
                    dt_sec=0.0 if has_seconds else 0.0,
                    w_dur=max(a.dur_ql, 0.0),
                    w_min=0.0,
                    voice=vid,
                    transition_kind="vertical",
                )
            )
    return rows


def build_directional_transition_tables(
    evs: List[Event],
    *,
    epsilon_dt: float,
    legacy_mixed_mode: bool = False,
    has_seconds: bool = True,
    include_vertical_auxiliary: bool = True,
) -> TransitionBuildResult:
    """
    Build horizontal (main field) and optional vertical transition tables.

    Parameters
    ----------
    epsilon_dt
        Minimum |Δt| in **quarterLength** for a transition to count as horizontal for the
        main field (also compared to ``dt_sec`` when ``has_seconds`` and time axis is sec).
    legacy_mixed_mode
        If True, use global :func:`transitions_from_events` on ``evs`` as before (after
        parse-time stagger/collapse), tag rows as ``legacy_mixed``.
    include_vertical_auxiliary
        If True, compute chord-internal pairs (dt≈0) for optional plots / exports.
    """
    stats: Dict[str, Any] = {
        "n_note_events": len(evs),
        "n_candidate_transitions_legacy": 0,
        "n_horizontal_raw": 0,
        "n_horizontal_main": 0,
        "n_vertical": 0,
        "epsilon_dt_ql": float(epsilon_dt),
    }

    if legacy_mixed_mode:
        df = transitions_from_events(evs)
        if df.empty:
            return TransitionBuildResult(horizontal=df, vertical=pd.DataFrame(), stats=stats)
        df = df.copy()
        df["transition_kind"] = "legacy_mixed"
        df["voice"] = np.nan
        tc = len(df)
        stats["n_candidate_transitions_legacy"] = tc
        dt_col = "dt_sec" if has_seconds else "dt_ql"
        # When seconds map exists, epsilon is still in ql for ql mode; for sec use proportional small epsilon
        if has_seconds and dt_col == "dt_sec":
            mask_h = df["dt_sec"].abs() > max(epsilon_dt, 1e-15)
        else:
            mask_h = df["dt_ql"].abs() > max(epsilon_dt, EPSILON)
        df_h = df[mask_h].copy()
        df_v = df[~mask_h].copy()
        stats["n_horizontal_raw"] = tc
        stats["n_horizontal_main"] = len(df_h)
        stats["n_vertical"] = len(df_v)
        vert = df_v if include_vertical_auxiliary else pd.DataFrame()
        return TransitionBuildResult(horizontal=df_h, vertical=vert, stats=stats)

    collapsed = _collapse_onsets_per_voice(evs)
    row_h = _pairs_from_melodic_chain(collapsed, has_seconds=has_seconds)
    df_all = pd.DataFrame(row_h)
    if df_all.empty:
        stats["n_horizontal_raw"] = 0
        vert_df = pd.DataFrame()
        if include_vertical_auxiliary:
            vr = _vertical_pairs_from_expanded(evs, has_seconds=has_seconds)
            vert_df = pd.DataFrame(vr)
            stats["n_vertical"] = len(vert_df)
        return TransitionBuildResult(horizontal=df_all, vertical=vert_df, stats=stats)

    stats["n_horizontal_raw"] = len(df_all)
    if has_seconds:
        mask = df_all["dt_sec"].abs() > max(epsilon_dt, 1e-15)
    else:
        mask = df_all["dt_ql"].abs() > max(epsilon_dt, EPSILON)
    df_h = df_all[mask].copy()
    stats["n_horizontal_main"] = len(df_h)
    vert_df = pd.DataFrame()
    if include_vertical_auxiliary:
        vr = _vertical_pairs_from_expanded(evs, has_seconds=has_seconds)
        vert_df = pd.DataFrame(vr)
        stats["n_vertical"] = len(vert_df)
    return TransitionBuildResult(horizontal=df_h, vertical=vert_df, stats=stats)


def melodic_skeleton_for_plot(evs: List[Event]) -> List[Event]:
    """Collapsed per-voice onset series for pitch–time lines (no fake chord sweeps)."""
    return _collapse_onsets_per_voice(evs)
