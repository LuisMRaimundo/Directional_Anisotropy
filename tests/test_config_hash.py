"""Deterministic config_sha256 tests."""

from __future__ import annotations

from anisotropia.config import AnalysisConfig
from anisotropia.pipeline import run_analysis
from anisotropia.reproducibility import (
    config_hash,
    config_hash_from_dict,
    effective_config_dict,
    effective_config_dict_from_overrides,
)
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_config_hash_stable_order():
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    h1 = config_hash(cfg, time_axis_effective="ql")
    h2 = config_hash(cfg, time_axis_effective="ql")
    assert h1 == h2
    assert len(h1) == 64


def test_config_hash_changes_with_field():
    a = AnalysisConfig(window_mode="total", chord_rep="centroid", bootstrap_ci=False)
    b = AnalysisConfig(window_mode="total", chord_rep="top", bootstrap_ci=False)
    assert config_hash(a, time_axis_effective="ql") != config_hash(b, time_axis_effective="ql")


def test_effective_config_dict_from_overrides_complete():
    overrides = effective_config_dict(
        AnalysisConfig(window_mode="total", bootstrap_ci=False),
        time_axis_effective="ql",
    )
    h = config_hash_from_dict(overrides)
    h2 = config_hash_from_dict(effective_config_dict_from_overrides(overrides))
    assert h == h2


def test_run_analysis_metadata_has_config_sha256():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    result = run_analysis(xml, "m.xml", cfg)
    assert result.reproducibility.get("config_sha256")
    assert len(result.reproducibility["config_sha256"]) == 64
    assert result.reproducibility.get("input_sha256")
    assert result.reproducibility["config_sha256"] != result.reproducibility["input_sha256"]
