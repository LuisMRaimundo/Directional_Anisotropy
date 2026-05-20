"""Parameter sensitivity analysis tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from anisotropia.config import AnalysisConfig
from anisotropia.pipeline import run_analysis
from anisotropia.sensitivity import run_parameter_sensitivity

FIXTURES = Path(__file__).parent / "fixtures"


def test_sensitivity_deterministic():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    base = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    grid = {"chord_rep": ["centroid", "top"]}
    r1 = run_parameter_sensitivity(xml, "m.xml", base, grid)
    r2 = run_parameter_sensitivity(xml, "m.xml", base, grid)
    assert len(r1.variants) == len(r2.variants)
    assert r1.baseline == r2.baseline


def test_chord_rep_change_reported():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    base = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    report = run_parameter_sensitivity(
        xml, "m.xml", base, {"chord_rep": ["centroid", "bottom"]}
    )
    params = {v.parameter for v in report.variants}
    assert "chord_rep" in params


def test_unsupported_parameter_raises():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    with pytest.raises(ValueError, match="Unsupported"):
        run_parameter_sensitivity(
            xml, "m.xml", AnalysisConfig(), {"rose_bins": [8, 16]}
        )


def test_default_analysis_unchanged_by_importing_sensitivity():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    before = run_analysis(xml, "m.xml", cfg)
    run_parameter_sensitivity(xml, "m.xml", cfg, {"standardization_mode": ["none", "local_zscore"]})
    after = run_analysis(xml, "m.xml", cfg)
    assert before.df_results.equals(after.df_results)
