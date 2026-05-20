"""Tests for Excel export helpers."""

import numpy as np
import pandas as pd

from anisotropia.excel_export import (
    build_anisotropia_excel_bytes,
    concat_transitions_by_part,
    enrich_transitions_with_note_names,
    events_to_trajectories_df,
    instrument_metrics_with_flow_components,
    midi_to_note_name,
)
from anisotropia.parsing import Event


def test_midi_to_note_name():
    assert midi_to_note_name(60.0) == "C4"
    assert midi_to_note_name(62.0) == "D4"


def test_events_to_trajectories_df():
    evs = [Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1), Event(t=0.5, ql=1.0, dur_ql=1.0, p=62.0, meas=1)]
    d = events_to_trajectories_df({"Violin": evs}, has_seconds=True)
    assert len(d) == 2
    assert list(d["part"]) == ["Violin", "Violin"]
    assert d["pitch_midi"].tolist() == [60.0, 62.0]
    assert d["pitch_note"].tolist() == ["C4", "D4"]


def test_enrich_transitions_with_note_names():
    ev_a = [Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1), Event(t=1.0, ql=1.0, dur_ql=1.0, p=64.0, meas=1)]
    trans = pd.DataFrame({"dp": [4.0], "dt_ql": [1.0]})
    stacked = concat_transitions_by_part({"A": trans})
    out = enrich_transitions_with_note_names(stacked, {"A": ev_a})
    assert out["note_from"].iloc[0] == "C4"
    assert out["note_to"].iloc[0] == "E4"
    assert out["pitch_from_midi"].iloc[0] == 60.0
    assert out["pitch_to_midi"].iloc[0] == 64.0


def test_concat_transitions_by_part():
    t1 = pd.DataFrame({"dp": [1, -1], "dt_ql": [1.0, 1.0]})
    t2 = pd.DataFrame({"dp": [2], "dt_ql": [1.0]})
    out = concat_transitions_by_part({"A": t1, "B": t2})
    assert len(out) == 3
    assert out["part"].tolist() == ["A", "A", "B"]


def test_instrument_metrics_flow_components():
    df = pd.DataFrame(
        {
            "window": ["w1"],
            "part": ["P1"],
            "A_tensor": [0.8],
            "mu": [0.0],
        }
    )
    out = instrument_metrics_with_flow_components(df)
    assert np.isclose(out["flow_U"].iloc[0], 0.8)
    assert np.isclose(out["flow_V"].iloc[0], 0.0)


def test_build_anisotropia_excel_bytes_non_empty():
    df_out = pd.DataFrame(
        {
            "window": ["m0-m4"],
            "scope": ["instrumento"],
            "part": ["X"],
            "D": [0.1],
            "tau": [0.2],
            "A_tensor": [0.5],
            "mu": [1.0],
            "R": [0.6],
            "n": [10],
            "W": [1.0],
            "conflict": [np.nan],
        }
    )
    events = {"X": [Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1)]}
    trans = {"X": pd.DataFrame({"dp": [1], "dt_ql": [1.0], "dt_sec": [0.1], "w_dur": [1.0], "w_min": [1.0]})}
    raw = build_anisotropia_excel_bytes(df_out, events, trans, has_seconds=True)
    assert len(raw) > 200
    assert raw[:2] == b"PK"  # ZIP / xlsx signature
