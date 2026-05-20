"""Build multi-sheet Excel workbooks for Anisotropia exports."""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from music21 import pitch as m21_pitch

from anisotropia.parsing import Event


def midi_to_note_name(m: float) -> str:
    """Map MIDI pitch (float OK for centroids) to music21 name + octave."""
    if not np.isfinite(m):
        return ""
    try:
        p = m21_pitch.Pitch()
        p.midi = float(m)
        return p.nameWithOctave
    except Exception:
        return ""


def _sheet_name(name: str) -> str:
    """Excel sheet names: max 31 chars; no []:*?/\\."""
    bad = '[]:*?/\\'
    s = "".join(c for c in name if c not in bad)[:31]
    return s or "Sheet1"


def events_to_trajectories_df(
    events_by_part: Dict[str, List[Event]],
    *,
    has_seconds: bool,
) -> pd.DataFrame:
    """Long-format pitch–time table (one row per note event per instrument)."""
    rows = []
    for part, evs in events_by_part.items():
        for e in evs:
            pm = float(e.p)
            rows.append(
                {
                    "part": part,
                    "time_s": float(e.t) if has_seconds else np.nan,
                    "time_ql": float(e.ql),
                    "measure": int(e.meas),
                    "pitch_midi": pm,
                    "pitch_note": midi_to_note_name(pm),
                    "dur_ql": float(e.dur_ql),
                }
            )
    return pd.DataFrame(rows)


def concat_transitions_by_part(trans_by_part: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Stack all parts' transition tables with a leading `part` column."""
    dfs = []
    for part, df in trans_by_part.items():
        if df is not None and not df.empty:
            d = df.copy()
            d.insert(0, "part", part)
            dfs.append(d)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def enrich_transitions_with_note_names(
    trans_all: pd.DataFrame,
    events_by_part: Dict[str, List[Event]],
) -> pd.DataFrame:
    """
    Add pitch_from_midi, pitch_to_midi, note_from, note_to per row, aligned with
    consecutive events for each part (same order as transitions_from_events).
    """
    if trans_all.empty or "part" not in trans_all.columns:
        return trans_all
    out_frames: List[pd.DataFrame] = []
    for part in trans_all["part"].unique():
        tdf = trans_all[trans_all["part"] == part].reset_index(drop=True)
        evs = events_by_part.get(part, [])
        n_tr = len(tdf)
        n_pair = max(0, len(evs) - 1)
        from_midi: List[float] = [np.nan] * n_tr
        to_midi: List[float] = [np.nan] * n_tr
        for j in range(min(n_tr, n_pair)):
            from_midi[j] = float(evs[j].p)
            to_midi[j] = float(evs[j + 1].p)
        tdf = tdf.copy()
        tdf.insert(1, "pitch_from_midi", from_midi)
        tdf.insert(2, "pitch_to_midi", to_midi)
        tdf.insert(3, "note_from", [midi_to_note_name(x) for x in from_midi])
        tdf.insert(4, "note_to", [midi_to_note_name(x) for x in to_midi])
        out_frames.append(tdf)
    return pd.concat(out_frames, ignore_index=True)


def instrument_metrics_with_flow_components(df_instr: pd.DataFrame) -> pd.DataFrame:
    """
    Per-window, per-instrument metrics plus U,V matching the flow map quiver
    (U = A·cos μ, V = A·sin μ).
    """
    if df_instr.empty:
        return df_instr.copy()
    out = df_instr.copy()
    mu = out.get("mu")
    A = out.get("A_tensor", 0)
    if mu is not None:
        mu_arr = pd.to_numeric(mu, errors="coerce")
        A_arr = pd.to_numeric(A, errors="coerce").fillna(0)
        out["flow_U"] = A_arr * np.cos(mu_arr)
        out["flow_V"] = A_arr * np.sin(mu_arr)
    return out


def build_anisotropia_excel_bytes(
    df_out: pd.DataFrame,
    events_by_part: Dict[str, List[Event]],
    trans_by_part: Dict[str, pd.DataFrame],
    *,
    has_seconds: bool,
    analysis_metadata: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Single .xlsx with:
    - resultados_completo: full results table (same as CSV download)
    - metricas_instrumento: scope==instrumento + flow_U, flow_V
    - totais_conflito: aggregates 2A/2B and directional conflict rows
    - trajetorias_pitch: note events (pitch_midi + pitch_note, etc.)
    - transicoes: transitions + pitch_from_midi / pitch_to_midi / note_from / note_to
    """
    buf = io.BytesIO()
    df_instr = df_out[df_out["scope"] == "instrumento"].copy()
    df_instr_enriched = instrument_metrics_with_flow_components(df_instr)
    df_other = df_out[df_out["scope"] != "instrumento"].copy()

    traj = events_to_trajectories_df(events_by_part, has_seconds=has_seconds)
    trans_all = concat_transitions_by_part(trans_by_part)
    trans_all = enrich_transitions_with_note_names(trans_all, events_by_part)

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_out.to_excel(writer, sheet_name=_sheet_name("resultados_completo"), index=False)
        df_instr_enriched.to_excel(writer, sheet_name=_sheet_name("metricas_instrumento"), index=False)
        if not df_other.empty:
            df_other.to_excel(writer, sheet_name=_sheet_name("totais_conflito"), index=False)
        if not traj.empty:
            traj.to_excel(writer, sheet_name=_sheet_name("trajetorias_pitch"), index=False)
        if not trans_all.empty:
            trans_all.to_excel(writer, sheet_name=_sheet_name("transicoes"), index=False)
        if analysis_metadata:
            meta_df = pd.DataFrame([{"key": k, "value": json.dumps(v) if isinstance(v, (dict, list)) else v} for k, v in analysis_metadata.items()])
            meta_df.to_excel(writer, sheet_name=_sheet_name("metadata"), index=False)

    return buf.getvalue()
