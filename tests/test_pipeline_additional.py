"""Additional focused tests for anisotropia.pipeline control-flow and helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from anisotropia.config import AnalysisConfig
from anisotropia.metrics import Metrics
from anisotropia.parsing import Event, parse_musicxml
from anisotropia.pipeline import (
    _metrics_to_row,
    _slice_transitions_for_window,
    run_analysis,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _sample_trans_by_part() -> dict[str, pd.DataFrame]:
    return {
        "Part1": pd.DataFrame(
            {
                "meas": [1, 2, 2, 3, 4],
                "t": [0.0, 1.0, 1.5, 2.5, 4.0],
                "ql": [0.0, 1.0, 1.5, 2.5, 4.0],
                "dp": [1.0, 2.0, -1.0, 3.0, 1.0],
                "dt_ql": [1.0, 0.5, 1.0, 1.5, 1.0],
                "dt_sec": [1.0, 0.5, 1.0, 1.5, 1.0],
                "w_dur": [1.0, 1.0, 1.0, 1.0, 1.0],
                "w_min": [1.0, 0.5, 1.0, 1.0, 1.0],
            }
        ),
        "Part2": pd.DataFrame(
            {
                "meas": [1, 2, 3],
                "t": [0.5, 1.5, 3.0],
                "ql": [0.5, 1.5, 3.0],
                "dp": [2.0, 1.0, 2.0],
                "dt_ql": [1.0, 1.5, 1.0],
                "dt_sec": [1.0, 1.5, 1.0],
                "w_dur": [1.0, 1.0, 1.0],
                "w_min": [1.0, 1.0, 1.0],
            }
        ),
    }


def _base_metrics(**overrides: float | int) -> Metrics:
    defaults = dict(
        D=0.1,
        tau=0.2,
        A_tensor=0.5,
        mu=0.3,
        R=0.8,
        n=10,
        weight_sum=5.0,
    )
    defaults.update(overrides)
    return Metrics(**defaults)


# --- 1. Confidence interval recording -----------------------------------------


def test_metrics_to_row_records_finite_confidence_intervals():
    m = _base_metrics(
        A_tensor_ci_lo=0.41,
        A_tensor_ci_hi=0.59,
        R_ci_lo=0.71,
        R_ci_hi=0.89,
    )
    row = _metrics_to_row(m, window="total", scope="instrumento", part_name="Part1")
    assert row["A_tensor_ci_lo"] == pytest.approx(0.41)
    assert row["A_tensor_ci_hi"] == pytest.approx(0.59)
    assert row["R_ci_lo"] == pytest.approx(0.71)
    assert row["R_ci_hi"] == pytest.approx(0.89)


def test_metrics_to_row_omits_non_finite_confidence_intervals():
    m = _base_metrics(
        A_tensor_ci_lo=np.nan,
        A_tensor_ci_hi=np.nan,
        R_ci_lo=np.inf,
        R_ci_hi=0.9,
    )
    row = _metrics_to_row(m, window="total", scope="instrumento", part_name="Part1")
    assert "A_tensor_ci_lo" not in row
    assert "A_tensor_ci_hi" not in row
    assert "R_ci_lo" not in row
    assert "R_ci_hi" not in row


# --- 2–4. _slice_transitions_for_window ---------------------------------------


def test_slice_transitions_measures_mode_filters_by_reference_window():
    trans = _sample_trans_by_part()
    ref_wdf = trans["Part1"].iloc[1:3].copy()
    cfg = AnalysisConfig(window_mode="measures", window_size=2, step=1)
    out = _slice_transitions_for_window("m2–m3", ref_wdf, trans, cfg, "measures")
    assert set(out.keys()) == {"Part1", "Part2"}
    assert list(out["Part1"]["meas"]) == [2, 2]
    assert list(out["Part2"]["meas"]) == [2]


def test_slice_transitions_measures_empty_reference_returns_empty():
    trans = _sample_trans_by_part()
    cfg = AnalysisConfig(window_mode="measures", window_size=2, step=1)
    out = _slice_transitions_for_window("m1–m2", pd.DataFrame(), trans, cfg, "measures")
    assert out == {}


def test_slice_transitions_seconds_mode_filters_by_time_range():
    trans = _sample_trans_by_part()
    ref_wdf = pd.DataFrame({"meas": [2], "t": [1.0]})
    cfg = AnalysisConfig(window_mode="seconds", window_size=2.0, step=1.0)
    out = _slice_transitions_for_window("t1.00–3.00", ref_wdf, trans, cfg, "seconds")
    assert list(out["Part1"]["t"]) == [1.0, 1.5, 2.5]
    assert list(out["Part2"]["t"]) == [1.5]


def test_slice_transitions_seconds_empty_reference_returns_empty():
    trans = _sample_trans_by_part()
    cfg = AnalysisConfig(window_mode="seconds", window_size=2.0, step=1.0)
    out = _slice_transitions_for_window("t0.00–2.00", pd.DataFrame(), trans, cfg, "seconds")
    assert out == {}


def test_slice_transitions_events_mode_slices_by_index_label():
    trans = _sample_trans_by_part()
    ref_wdf = trans["Part1"].iloc[0:3].copy()
    cfg = AnalysisConfig(window_mode="events", window_size=2, step=1)
    out = _slice_transitions_for_window("e0–e2", ref_wdf, trans, cfg, "events")
    assert len(out["Part1"]) == 3
    assert len(out["Part2"]) == 3
    assert out["Part1"].iloc[0]["dp"] == pytest.approx(1.0)
    assert out["Part2"].iloc[-1]["dp"] == pytest.approx(2.0)


def test_slice_transitions_events_invalid_label_returns_empty():
    trans = _sample_trans_by_part()
    ref_wdf = trans["Part1"].iloc[0:2].copy()
    cfg = AnalysisConfig(window_mode="events", window_size=2, step=1)
    out = _slice_transitions_for_window("not-an-event-window", ref_wdf, trans, cfg, "events")
    assert out == {}


def test_slice_transitions_events_empty_reference_returns_empty():
    trans = _sample_trans_by_part()
    cfg = AnalysisConfig(window_mode="events", window_size=2, step=1)
    out = _slice_transitions_for_window("e0–e1", pd.DataFrame(), trans, cfg, "events")
    assert out == {}


def test_slice_transitions_events_index_beyond_length_yields_empty_slice():
    trans = {"Part1": _sample_trans_by_part()["Part1"].iloc[:2].copy()}
    ref_wdf = trans["Part1"].copy()
    cfg = AnalysisConfig(window_mode="events", window_size=2, step=2)
    out = _slice_transitions_for_window("e5–e9", ref_wdf, trans, cfg, "events")
    assert out["Part1"].empty


def test_slice_transitions_total_mode_passes_full_tables():
    trans = _sample_trans_by_part()
    cfg = AnalysisConfig(window_mode="total")
    out = _slice_transitions_for_window("total", trans["Part1"], trans, cfg, "total")
    assert len(out["Part1"]) == len(trans["Part1"])
    assert len(out["Part2"]) == len(trans["Part2"])


# --- Integration: window modes through run_analysis --------------------------------


def test_run_analysis_measures_seconds_and_events_window_modes():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    for mode in ("measures", "seconds", "events"):
        cfg = AnalysisConfig(window_mode=mode, window_size=2, step=1, bootstrap_ci=False)
        result = run_analysis(xml, "minimal_score.xml", cfg)
        assert result.windows
        assert not result.df_results.empty
        assert all(w.window_label for w in result.windows)


# --- 5. seconds unavailable fallback ------------------------------------------


def test_run_analysis_seconds_window_unavailable_falls_back_to_ql(monkeypatch):
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    events_by_part, _, _ = parse_musicxml(xml, "minimal_score.xml")

    def _no_seconds_parse(*_args, **_kwargs):
        return events_by_part, False, []

    monkeypatch.setattr("anisotropia.pipeline.parse_musicxml", _no_seconds_parse)
    cfg = AnalysisConfig(window_mode="seconds", window_size=2.0, step=1.0, bootstrap_ci=False)
    result = run_analysis(xml, "minimal_score.xml", cfg)
    assert result.time_axis == "ql"
    assert any("seconds window unavailable" in w for w in result.warnings)


# --- 6. insufficient horizontal transitions ---------------------------------


def test_run_analysis_insufficient_horizontal_transitions_raises(monkeypatch):
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    single_event = {
        "Part1": [Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1)],
    }

    def _single_event_parse(*_args, **_kwargs):
        return single_event, True, []

    monkeypatch.setattr("anisotropia.pipeline.parse_musicxml", _single_event_parse)
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    with pytest.raises(ValueError, match="Insufficient horizontal transitions for metrics."):
        run_analysis(xml, "minimal_score.xml", cfg)


# --- 7. no windows created ----------------------------------------------------


def test_run_analysis_no_windows_created_raises(monkeypatch):
    xml = (FIXTURES / "minimal_score.xml").read_bytes()

    def _no_windows(*_args, **_kwargs):
        return []

    monkeypatch.setattr("anisotropia.pipeline.window_slices_for_part", _no_windows)
    cfg = AnalysisConfig(window_mode="measures", window_size=2, step=1, bootstrap_ci=False)
    with pytest.raises(ValueError, match="No windows could be created with current parameters."):
        run_analysis(xml, "minimal_score.xml", cfg)
