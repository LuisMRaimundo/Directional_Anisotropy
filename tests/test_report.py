"""Tests for report generation."""

import pandas as pd

from anisotropia.report import generate_report


def test_generate_report_basic():
    """Report is generated with expected structure."""
    df = pd.DataFrame([
        {
            "window": "total", "scope": "total_2A", "part": "TOTAL_2A", "D": 0.5, "tau": 0.3, "A_tensor": 0.8,
            "mu": 1.57, "mu_axis": 1.57, "cos_mu": 0.0, "sin_mu": 1.0, "mu_doubled_angle": 3.14, "R": 0.9, "n": 100, "W": 50.0,
        },
        {
            "window": "total", "scope": "total_2B", "part": "TOTAL_2B", "D": 0.4, "tau": 0.35, "A_tensor": 0.75,
            "mu": 1.5, "mu_axis": 1.5, "cos_mu": 0.07, "sin_mu": 1.0, "R": 0.85, "n": 100, "W": 50.0,
        },
    ])
    params = {"chord_rep": "centroid", "weight_mode": "dur", "window_mode": "total", "window_size": 1, "step": 1, "scientific_mode": True}
    report = generate_report("test.xml", df, params, n_parts=5, n_windows=1, total_transitions=100)
    assert "Notational Anisotropy Analysis Report" in report
    assert "Technical Report" in report
    assert "Plain-Language Summary" in report
    assert "D = " in report or "Drift" in report
    assert "test.xml" in report
    assert "0.8000" in report or "0.8" in report
