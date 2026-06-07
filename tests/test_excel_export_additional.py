"""Additional focused tests for anisotropia.excel_export defensive and writer branches."""

from __future__ import annotations

import json
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from music21 import pitch as m21_pitch

from anisotropia.excel_export import (
    build_anisotropia_excel_bytes,
    concat_transitions_by_part,
    enrich_transitions_with_note_names,
    instrument_metrics_with_flow_components,
    midi_to_note_name,
)
from anisotropia.parsing import Event


def _result_row(scope: str, part: str) -> dict:
    return {
        "window": "m0-m4",
        "scope": scope,
        "part": part,
        "D": 0.1,
        "tau": 0.2,
        "A_tensor": 0.5,
        "mu": 1.0,
        "R": 0.6,
        "n": 10,
        "W": 1.0,
        "conflict": np.nan,
    }


def _events_and_trans() -> tuple[dict[str, list[Event]], dict[str, pd.DataFrame]]:
    events = {
        "X": [
            Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1),
            Event(t=1.0, ql=1.0, dur_ql=1.0, p=62.0, meas=1),
        ]
    }
    trans = {
        "X": pd.DataFrame(
            {
                "dp": [2.0],
                "dt_ql": [1.0],
                "dt_sec": [1.0],
                "w_dur": [1.0],
                "w_min": [1.0],
                "ql": [0.0],
                "t": [0.0],
                "meas": [1],
            }
        )
    }
    return events, trans


def _workbook_sheet_names(raw: bytes) -> list[str]:
    with pd.ExcelFile(BytesIO(raw)) as book:
        return list(book.sheet_names)


# --- 1. midi_to_note_name fallback --------------------------------------------


def test_midi_to_note_name_normal_music21_pitch():
    assert midi_to_note_name(67.0) == "G4"


def test_midi_to_note_name_returns_empty_when_name_with_octave_raises(monkeypatch):
    class _BrokenPitch:
        def __init__(self) -> None:
            self.midi = None

        @property
        def nameWithOctave(self) -> str:
            raise RuntimeError("nameWithOctave unavailable")

    monkeypatch.setattr(m21_pitch, "Pitch", _BrokenPitch)
    assert midi_to_note_name(60.0) == ""


def test_midi_to_note_name_non_finite_returns_empty():
    assert midi_to_note_name(float("nan")) == ""
    assert midi_to_note_name(float("inf")) == ""


# --- 2. Empty DataFrame concatenation -----------------------------------------


def test_concat_transitions_by_part_empty_returns_empty_dataframe():
    out = concat_transitions_by_part({})
    assert isinstance(out, pd.DataFrame)
    assert out.empty

    out2 = concat_transitions_by_part({"A": pd.DataFrame(), "B": None})
    assert out2.empty


# --- 3. enrich_transitions_with_note_names — empty / missing part -------------


def test_enrich_transitions_empty_input_unchanged():
    empty = pd.DataFrame()
    assert enrich_transitions_with_note_names(empty, {}).empty


def test_enrich_transitions_without_part_column_unchanged():
    trans = pd.DataFrame({"dp": [1.0], "dt_ql": [1.0]})
    out = enrich_transitions_with_note_names(trans, {"A": []})
    assert out.equals(trans)


# --- 4. enrich — empty instrument events still enriches structure -------------


def test_enrich_transitions_missing_part_events_uses_nan_note_columns():
    trans = pd.DataFrame({"part": ["Missing"], "dp": [1.0], "dt_ql": [1.0]})
    out = enrich_transitions_with_note_names(trans, {})
    assert out["note_from"].iloc[0] == ""
    assert out["note_to"].iloc[0] == ""
    assert np.isnan(out["pitch_from_midi"].iloc[0])


# --- 5. instrument_metrics empty branch ---------------------------------------


def test_instrument_metrics_with_flow_components_empty_copy():
    empty = pd.DataFrame(columns=["window", "part", "A_tensor", "mu"])
    out = instrument_metrics_with_flow_components(empty)
    assert out.empty
    assert list(out.columns) == list(empty.columns)


# --- 6–7. Excel writer branches and empty optional sheets -------------------


def test_build_excel_writes_expected_non_empty_sheets(tmp_path):
    events, trans = _events_and_trans()
    df_out = pd.DataFrame(
        [
            _result_row("instrumento", "X"),
            _result_row("total_2A", "TOTAL_2A"),
        ]
    )
    metadata = {
        "version": "2.4.0",
        "config": {"window_mode": "total"},
        "tags": ["synth", "test"],
    }
    raw = build_anisotropia_excel_bytes(
        df_out,
        events,
        trans,
        has_seconds=True,
        analysis_metadata=metadata,
    )
    assert raw[:2] == b"PK"

    sheets = _workbook_sheet_names(raw)
    assert "resultados_completo" in sheets
    assert "metricas_instrumento" in sheets
    assert "totais_conflito" in sheets
    assert "trajetorias_pitch" in sheets
    assert "transicoes" in sheets
    assert "metadata" in sheets

    meta = pd.read_excel(BytesIO(raw), sheet_name="metadata")
    row_map = dict(zip(meta["key"], meta["value"]))
    assert row_map["version"] == "2.4.0"
    assert json.loads(row_map["config"]) == {"window_mode": "total"}
    assert json.loads(row_map["tags"]) == ["synth", "test"]

    tmp_path.joinpath("out.xlsx").write_bytes(raw)


def test_build_excel_skips_empty_optional_sheets():
    df_out = pd.DataFrame([_result_row("instrumento", "X")])
    raw = build_anisotropia_excel_bytes(
        df_out,
        {},
        {},
        has_seconds=False,
        analysis_metadata=None,
    )
    sheets = _workbook_sheet_names(raw)
    assert "resultados_completo" in sheets
    assert "metricas_instrumento" in sheets
    assert "totais_conflito" not in sheets
    assert "trajetorias_pitch" not in sheets
    assert "transicoes" not in sheets
    assert "metadata" not in sheets
