"""Analysis warning generation tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from anisotropia.analysis_warnings import (
    collect_low_n_warnings,
    collect_parse_warnings,
    collect_unpitched_display_warnings,
)
from anisotropia.config import AnalysisConfig, GracePolicyNotImplementedError
from anisotropia.metrics import N_MIN_STABLE
from anisotropia.parsing import Event, parse_musicxml
from anisotropia.pipeline import run_analysis
from anisotropia.report import generate_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_low_n_part_warning():
    df = pd.DataFrame([{"window": "total", "scope": "instrumento", "part": "P", "n": 5}])
    ontology = {"parts": {"P": {"n_horizontal_main": 5}}}
    summary = {"n_reference_part_horizontal": 5}
    warns = collect_low_n_warnings(df, ontology, summary)
    assert any(w.warning_type.startswith("low_n") for w in warns)
    assert all(w.threshold == N_MIN_STABLE for w in warns if w.threshold)


def test_no_low_n_when_above_threshold():
    n_ok = N_MIN_STABLE + 5
    df = pd.DataFrame([{"window": "total", "scope": "instrumento", "part": "P", "n": n_ok}])
    ontology = {"parts": {"P": {"n_horizontal_main": n_ok}}}
    summary = {"n_reference_part_horizontal": n_ok}
    warns = collect_low_n_warnings(df, ontology, summary)
    assert not any(w.warning_type.startswith("low_n_window") for w in warns)


def test_unpitched_proxy_warning_when_map_display():
    evs = {
        "Drums": [Event(t=0, ql=0, dur_ql=1, p=60, meas=1, is_unpitched=True)],
    }
    warns = collect_unpitched_display_warnings(evs, "map_display")
    assert len(warns) == 1
    assert "display pitch" in warns[0].message.lower()


def test_parse_warnings_sounding_and_repeats_types():
    msgs = [
        "toSoundingPitch() failed; analysis used written pitch instead of sounding pitch.",
        "expandRepeats() failed; analysis used the unexpanded score.",
    ]
    warns = collect_parse_warnings(msgs)
    assert warns[0].warning_type == "sounding_pitch_fallback"
    assert warns[1].warning_type == "expand_repeats_fallback"


def test_pipeline_includes_sounding_pitch_fallback_warning(monkeypatch):
    from music21 import converter

    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    original_parse = converter.parse

    def fake_parse(path):
        sc = original_parse(path)

        def fail(*_a, **_k):
            raise RuntimeError("mock transpose failure")

        sc.toSoundingPitch = fail
        return sc

    monkeypatch.setattr(converter, "parse", fake_parse)
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False, pitch_space="sounding")
    result = run_analysis(xml, "m.xml", cfg)
    assert any("toSoundingPitch" in w for w in result.warnings)
    assert any(
        sw.warning_type == "sounding_pitch_fallback" for sw in result.structured_warnings
    )


def test_unpitched_exclude_no_proxy_warning():
    evs = {"Drums": [Event(t=0, ql=0, dur_ql=1, p=60, meas=1, is_unpitched=True)]}
    assert not collect_unpitched_display_warnings(evs, "exclude")


def test_include_attached_raises():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    with pytest.raises(GracePolicyNotImplementedError):
        parse_musicxml(xml, "m.xml", grace_policy="include_attached")


def test_pipeline_warnings_in_report():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    result = run_analysis(xml, "m.xml", cfg)
    text = generate_report(
        "m.xml",
        result.df_results,
        result.report_params,
        1,
        1,
        3,
        summary_counts=result.summary_counts,
    )
    assert "config_sha256" in text or result.reproducibility.get("config_sha256")
