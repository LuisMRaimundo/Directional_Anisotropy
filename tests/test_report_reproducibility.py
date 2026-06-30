"""Report and export reproducibility metadata."""

from __future__ import annotations

from pathlib import Path


from anisotropia.config import AnalysisConfig
from anisotropia.pipeline import run_analysis
from anisotropia.report import generate_report
from anisotropia.reproducibility import build_reproducibility_metadata

FIXTURES = Path(__file__).parent / "fixtures"


def test_report_contains_reproducibility_and_scope():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    result = run_analysis(xml, "minimal.xml", cfg, corpus_id="SYNTH_MINIMAL_ASCENDING")
    df = result.df_results
    params = {**result.report_params, **result.reproducibility}
    text = generate_report("minimal.xml", df, params, 1, 1, 3, summary_counts=result.summary_counts)
    assert "notational" in text.lower() or "Notational" in text
    assert "not audio" in text.lower() or "not** audio" in text.lower()
    assert "metric_schema_version" in text or "1.0.0" in text
    assert "horizontal" in text.lower()
    assert "not harmonic" in text.lower() or "not audio" in text.lower()


def test_repro_metadata_keys():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    meta = build_reproducibility_metadata(
        filename="m.xml", xml_bytes=xml, config=cfg, corpus_id="SYNTH_MINIMAL_ASCENDING"
    )
    for key in (
        "canonical_tool_name",
        "package_name",
        "software_version",
        "input_sha256",
        "config_sha256",
        "bootstrap_random_seed",
        "N_BOOTSTRAP",
    ):
        assert key in meta
    assert meta["canonical_tool_name"] == "Directional_Anisotropy"
    assert meta["package_name"] == "anisotropia"
    assert "global_zscore" in meta["global_zscore_note"]


def test_repro_metadata_without_config_requires_axis():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    meta = build_reproducibility_metadata(
        filename="m.xml",
        xml_bytes=xml,
        config=cfg,
        time_axis_effective="ql",
    )
    assert meta["software_version"]
    assert meta["input_sha256"]
    assert meta["config_sha256"]
    assert len(meta["config_sha256"]) == 64
