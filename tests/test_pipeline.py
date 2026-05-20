"""Programmatic pipeline (no Streamlit)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


from anisotropia import AnalysisConfig, run_analysis
from anisotropia.config import GracePolicyNotImplementedError
from anisotropia.parsing import parse_musicxml
from corpus.benchmark_profile import BENCHMARK_CONFIG

FIXTURES = Path(__file__).parent / "fixtures"
REF = Path(__file__).resolve().parents[1] / "corpus" / "reference_outputs"


def test_pipeline_no_streamlit_import():
    for mod_name in (
        "anisotropia.pipeline",
        "anisotropia.metrics",
        "anisotropia.parsing",
        "anisotropia.transitions",
        "anisotropia.windowing",
        "anisotropia.sensitivity",
    ):
        mod = importlib.import_module(mod_name)
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import streamlit" not in src
        assert "from streamlit" not in src


def test_run_analysis_minimal_score():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    result = run_analysis(xml, "minimal_score.xml", BENCHMARK_CONFIG, corpus_id="SYNTH_MINIMAL_ASCENDING")
    assert result.ref_part
    m = result.windows[0].metrics_2b
    assert m is not None
    assert m.n == 3
    assert m.D > 0
    assert m.tau < 0.5
    assert m.A_tensor > 0.9
    assert m.R > 0.5
    assert "input_sha256" in result.reproducibility
    assert result.reproducibility["metric_schema_version"] == "1.0.0"


def test_run_analysis_matches_frozen_reference():
    ref_path = REF / "SYNTH_MINIMAL_ASCENDING.json"
    if not ref_path.exists():
        pytest.skip("frozen reference not generated")
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    result = run_analysis(xml, "minimal_score.xml", BENCHMARK_CONFIG)
    m = result.windows[0].metrics_2b
    exp = ref["metrics_2b"]
    assert abs(m.D - exp["D"]) < 1e-9
    assert abs(m.tau - exp["tau"]) < 1e-9
    assert abs(m.A_tensor - exp["A_tensor"]) < 1e-9
    assert abs(m.R - exp["R"]) < 1e-9
    assert m.n == exp["n"]


def test_run_analysis_deterministic():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    a = run_analysis(xml, "m.xml", cfg)
    b = run_analysis(xml, "m.xml", cfg)
    assert a.df_results.equals(b.df_results)


def test_global_zscore_warning():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False, standardization_mode="global_zscore")
    result = run_analysis(xml, "m.xml", cfg)
    assert any("global_zscore" in w for w in result.warnings)


def test_include_attached_raises():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    with pytest.raises(GracePolicyNotImplementedError):
        parse_musicxml(xml, "m.xml", grace_policy="include_attached")
