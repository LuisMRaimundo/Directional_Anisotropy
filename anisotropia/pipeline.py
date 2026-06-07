"""
Programmatic analysis pipeline (no Streamlit).

Orchestrates parse → transitions → windowing → metrics → aggregates.
Metric formulas are unchanged; behaviour matches Anisotropia.py defaults.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from anisotropia.analysis_warnings import (
    collect_all_analysis_warnings,
    warnings_as_strings,
)
from anisotropia.config import AnalysisConfig
from anisotropia.metrics import (
    Metrics,
    aggregate_2A,
    aggregate_2B,
    compute_directional_conflict,
    compute_metrics_from_transitions,
)
from anisotropia.models import AnalysisResult, WindowResult
from anisotropia.parsing import parse_musicxml
from anisotropia.reproducibility import build_reproducibility_metadata
from anisotropia.transitions import build_directional_transition_tables
from anisotropia.windowing import parse_event_window_label, window_slices_for_part

_EPSILON_SEC = 1e-9


def _metrics_to_row(
    m: Metrics,
    *,
    window: str,
    scope: str,
    part_name: str,
    conflict: float = np.nan,
) -> dict:
    r = dict(
        window=window,
        scope=scope,
        part=part_name,
        D=m.D,
        tau=m.tau,
        A_tensor=m.A_tensor,
        mu=m.mu,
        mu_axis=getattr(m, "mu_axis", m.mu),
        cos_mu=getattr(m, "cos_mu", np.nan),
        sin_mu=getattr(m, "sin_mu", np.nan),
        R=m.R,
        n=m.n,
        W=m.weight_sum,
        conflict=conflict,
        lambda1=getattr(m, "lambda1", np.nan),
        lambda2=getattr(m, "lambda2", np.nan),
        mu_doubled_angle=getattr(m, "mu_doubled_angle", np.nan),
    )
    if np.isfinite(m.A_tensor_ci_lo):
        r["A_tensor_ci_lo"] = m.A_tensor_ci_lo
        r["A_tensor_ci_hi"] = m.A_tensor_ci_hi
    if np.isfinite(m.R_ci_lo):
        r["R_ci_lo"] = m.R_ci_lo
        r["R_ci_hi"] = m.R_ci_hi
    return r


def _conflict_row(window: str, conf: float) -> dict:
    return dict(
        window=window,
        scope="conflito",
        part="DIRECTIONAL_CONFLICT",
        D=np.nan,
        tau=np.nan,
        A_tensor=np.nan,
        mu=np.nan,
        mu_axis=np.nan,
        cos_mu=np.nan,
        sin_mu=np.nan,
        R=np.nan,
        n=0,
        W=0.0,
        conflict=conf,
        lambda1=np.nan,
        lambda2=np.nan,
        mu_doubled_angle=np.nan,
    )


def _slice_transitions_for_window(
    win_label: str,
    ref_wdf: pd.DataFrame,
    trans_by_part: Dict[str, pd.DataFrame],
    config: AnalysisConfig,
    window_mode: str,
) -> Dict[str, pd.DataFrame]:
    """Mirror Anisotropia.py window slicing."""
    out: Dict[str, pd.DataFrame] = {}
    if window_mode == "total":
        for part, df in trans_by_part.items():
            out[part] = df
        return out
    if window_mode == "measures":
        if ref_wdf.empty:
            return out
        m0 = int(ref_wdf["meas"].min())
        m1 = int(ref_wdf["meas"].max()) + 1
        for part, df in trans_by_part.items():
            out[part] = df[(df["meas"] >= m0) & (df["meas"] < m1)]
        return out
    if window_mode == "seconds":
        if ref_wdf.empty:
            return out
        t0 = float(ref_wdf["t"].min())
        t1 = t0 + float(config.window_size)
        for part, df in trans_by_part.items():
            out[part] = df[(df["t"] >= t0) & (df["t"] < t1)]
        return out
    if ref_wdf.empty:
        return out
    i0, i1_last = parse_event_window_label(win_label)
    if i0 is None or i1_last is None:
        return out
    i1_exclusive = i1_last + 1
    for part, df in trans_by_part.items():
        out[part] = df.iloc[i0:i1_exclusive] if len(df) > i0 else df.iloc[0:0]
    return out


def run_analysis(
    xml_bytes: bytes,
    filename: str,
    config: AnalysisConfig | None = None,
    *,
    corpus_id: str | None = None,
) -> AnalysisResult:
    """
    Run full notational directional-field analysis without Streamlit.

    Raises ValueError on parse failure or insufficient transitions (caller may catch).
    """
    cfg = config or AnalysisConfig()
    warn_list: List[str] = []

    if cfg.standardization_mode == "global_zscore":
        warn_list.append(
            "standardization_mode global_zscore: alias of local_zscore per metric window (not corpus-global)."
        )

    events_by_part, has_seconds, parse_warnings = parse_musicxml(
        xml_bytes,
        filename,
        chord_rep=cfg.chord_rep,
        grace_policy=cfg.grace_policy,
        split_voices=cfg.split_voices,
        expand_chord_pitches=cfg.expand_chord_pitches,
        chord_simultaneity=cfg.chord_simultaneity,
        merge_tied_notes=cfg.merge_tied_notes,
        expand_repeats=cfg.expand_repeats,
        merge_grand_staff=cfg.merge_grand_staff,
        pitch_space=cfg.pitch_space,
        unpitched_policy=cfg.unpitched_policy,
    )

    n_events = sum(len(v) for v in events_by_part.values())
    time_axis = cfg.effective_time_axis(has_seconds)
    if cfg.window_mode == "seconds" and not has_seconds:
        warn_list.append("seconds window unavailable; using quarterLength time axis.")
        time_axis = "ql"

    trans_by_part: Dict[str, pd.DataFrame] = {}
    trans_vertical_by_part: Dict[str, pd.DataFrame] = {}
    ontology_meta: Dict[str, Any] = {
        "parts": {},
        "epsilon_dt": float(cfg.epsilon_dt),
        "legacy_mixed_mode": cfg.legacy_mixed_mode,
    }

    for part, evs in events_by_part.items():
        tb = build_directional_transition_tables(
            evs,
            epsilon_dt=float(cfg.epsilon_dt),
            legacy_mixed_mode=cfg.legacy_mixed_mode,
            has_seconds=has_seconds,
            include_vertical_auxiliary=cfg.include_vertical_auxiliary,
        )
        trans_by_part[part] = tb.horizontal
        trans_vertical_by_part[part] = tb.vertical
        ontology_meta["parts"][part] = tb.stats

    ref_part = (
        max(trans_by_part.keys(), key=lambda k: len(trans_by_part[k]))
        if trans_by_part
        else None
    )
    if not ref_part or trans_by_part[ref_part].empty:
        raise ValueError("Insufficient horizontal transitions for metrics.")

    windows_slices = window_slices_for_part(
        trans_by_part[ref_part],
        window_mode=cfg.window_mode,
        window_size=float(cfg.window_size),
        step=float(cfg.step),
    )
    if not windows_slices:
        raise ValueError("No windows could be created with current parameters.")

    rows: List[dict] = []
    window_results: List[WindowResult] = []
    trans_by_window: Dict[str, pd.DataFrame] = {}

    for win_label, ref_wdf in windows_slices:
        trans_part_windowed = _slice_transitions_for_window(
            win_label, ref_wdf, trans_by_part, cfg, cfg.window_mode
        )
        metrics_part: Dict[str, Metrics] = {}
        for part, wdf in trans_part_windowed.items():
            metrics_part[part] = compute_metrics_from_transitions(
                wdf,
                time_axis=time_axis,
                weight_mode=cfg.weight_mode,
                standardize=cfg.standardization_mode,
                bootstrap_ci=cfg.bootstrap_ci,
            )

        mA = aggregate_2A(metrics_part, bootstrap_ci=cfg.bootstrap_ci) if cfg.compute_2a else None
        mB = (
            aggregate_2B(
                trans_part_windowed,
                time_axis=time_axis,
                weight_mode=cfg.weight_mode,
                standardize=cfg.standardization_mode,
                bootstrap_ci=cfg.bootstrap_ci,
            )
            if cfg.compute_2b
            else None
        )
        conflict_val = (
            compute_directional_conflict(metrics_part) if len(metrics_part) >= 2 else np.nan
        )

        for part, m in metrics_part.items():
            rows.append(_metrics_to_row(m, window=win_label, scope="instrumento", part_name=part))
        if mA is not None:
            rows.append(_metrics_to_row(mA, window=win_label, scope="total_2A", part_name="TOTAL_2A"))
        if mB is not None:
            rows.append(_metrics_to_row(mB, window=win_label, scope="total_2B", part_name="TOTAL_2B"))
        if np.isfinite(conflict_val):
            rows.append(_conflict_row(win_label, float(conflict_val)))

        window_results.append(
            WindowResult(
                window_label=win_label,
                metrics_by_part=metrics_part,
                metrics_2a=mA,
                metrics_2b=mB,
                directional_conflict=float(conflict_val) if np.isfinite(conflict_val) else np.nan,
                trans_by_part_windowed=trans_part_windowed,
            )
        )
        if ref_part and trans_part_windowed.get(ref_part) is not None:
            trans_by_window[win_label] = trans_part_windowed[ref_part].copy()

    df_out = pd.DataFrame(rows)
    summary_counts: Dict[str, Any] = {
        "n_note_events_total": int(n_events),
        "n_horizontal_transitions_total": int(sum(len(trans_by_part[p]) for p in trans_by_part)),
        "n_vertical_auxiliary_total": int(
            sum(len(trans_vertical_by_part[p]) for p in trans_vertical_by_part)
        ),
        "n_reference_part_horizontal": int(len(trans_by_part[ref_part])) if ref_part else 0,
        "reference_part_name": ref_part,
        "voice_aware_transition_construction": True,
        "per_voice_chain_construction": not cfg.legacy_mixed_mode,
        "cross_voice_chaining_in_main_field": bool(cfg.legacy_mixed_mode),
        "split_by_voice_output_aggregation": cfg.split_voices,
        "vertical_auxiliary_built": cfg.include_vertical_auxiliary,
        "main_field_horizontal_only": not cfg.legacy_mixed_mode,
    }

    structured_warnings = collect_all_analysis_warnings(
        df_results=df_out,
        events_by_part=events_by_part,
        ontology_meta=ontology_meta,
        summary_counts=summary_counts,
        unpitched_policy=cfg.unpitched_policy,
        bootstrap_ci=cfg.bootstrap_ci,
        parse_warnings=parse_warnings,
        extra_messages=warn_list,
    )
    warn_list = warnings_as_strings(structured_warnings)

    repro = build_reproducibility_metadata(
        filename=filename,
        xml_bytes=xml_bytes,
        config=cfg,
        corpus_id=corpus_id,
        ontology_summary=ontology_meta,
        time_axis_effective=time_axis,
        analysis_warnings=structured_warnings,
    )

    report_params = {
        **cfg.to_dict(),
        "weight_mode": cfg.weight_mode,
        "window_mode": cfg.window_mode,
        "scientific_mode": cfg.bootstrap_ci,
        "epsilon_dt": cfg.epsilon_dt,
        "ontology_summary": ontology_meta,
        "voice_aware_transition_construction": True,
        "per_voice_chain_construction": not cfg.legacy_mixed_mode,
        "cross_voice_chaining_in_main_field": bool(cfg.legacy_mixed_mode),
        "split_by_voice_output_aggregation": cfg.split_voices,
        "vertical_auxiliary_built": cfg.include_vertical_auxiliary,
        "main_field_horizontal_only": not cfg.legacy_mixed_mode,
        "summary_counts": summary_counts,
        "warnings": warn_list,
        "warnings_structured": [w.to_dict() for w in structured_warnings],
        **repro,
    }

    return AnalysisResult(
        df_results=df_out,
        events_by_part=events_by_part,
        trans_by_part=trans_by_part,
        trans_vertical_by_part=trans_vertical_by_part,
        trans_by_window=trans_by_window,
        windows=window_results,
        has_seconds=has_seconds,
        time_axis=time_axis,
        ref_part=ref_part,
        config=cfg,
        warnings=warn_list,
        structured_warnings=structured_warnings,
        ontology_meta=ontology_meta,
        summary_counts=summary_counts,
        reproducibility=repro,
        report_params=report_params,
    )
