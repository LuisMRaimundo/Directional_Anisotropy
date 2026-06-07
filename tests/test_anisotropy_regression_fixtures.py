"""
Phase 1 musicological regression suite — symbolic directional anisotropy.

Qualitative and metamorphic assertions only (no strict golden numerics).
Fixtures: corpus/fixtures/anisotropy_regression/
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from anisotropia.config import AnalysisConfig
from anisotropia.pipeline import run_analysis

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "corpus" / "fixtures" / "anisotropy_regression"
DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "ANISOTROPY_REGRESSION_FIXTURES.md"

REGRESSION_CONFIG = AnalysisConfig(
    window_mode="total",
    bootstrap_ci=False,
    standardization_mode="local_zscore",
    legacy_mixed_mode=False,
)

WINDOW_MEASURES_CONFIG = AnalysisConfig(
    window_mode="measures",
    window_size=2,
    step=2,
    bootstrap_ci=False,
    standardization_mode="local_zscore",
    legacy_mixed_mode=False,
)

EXPECTED_FIXTURES = frozenset(
    {
        "static_repetition.xml",
        "uniform_ascending_steps.xml",
        "uniform_descending_steps.xml",
        "alternating_up_down_same_axis.xml",
        "balanced_four_directions.xml",
        "parallel_ascending_parts.xml",
        "contrary_motion_symmetric.xml",
        "oblique_motion.xml",
        "directional_change_by_window.xml",
        "transposed_same_contour.xml",
        "pitch_inversion_same_rhythm.xml",
        "time_stretched_same_contour.xml",
        "dense_events_no_direction.xml",
        "sparse_strong_direction.xml",
    }
)


def _fixture_path(stem: str) -> Path:
    return FIXTURE_DIR / f"{stem}.xml"


def _run(stem: str, config: AnalysisConfig = REGRESSION_CONFIG):
    path = _fixture_path(stem)
    if not path.exists():
        pytest.skip(f"Fixture missing: {path}")
    return run_analysis(path.read_bytes(), path.name, config)


def _metrics_2b(result):
    return result.windows[0].metrics_2b


def _flow_v(m) -> float:
    if m is None or not np.isfinite(m.A_tensor) or not np.isfinite(m.mu):
        return float("nan")
    return float(m.A_tensor * math.sin(m.mu))


def _flow_u(m) -> float:
    if m is None or not np.isfinite(m.A_tensor) or not np.isfinite(m.mu):
        return float("nan")
    return float(m.A_tensor * math.cos(m.mu))


def _conflict(result) -> float:
    return float(result.windows[0].directional_conflict)


# --- 1. Parse / pipeline smoke -------------------------------------------------


@pytest.mark.parametrize("fixture_file", sorted(EXPECTED_FIXTURES))
def test_all_anisotropy_regression_fixtures_parse(fixture_file: str):
    stem = fixture_file.replace(".xml", "")
    cfg = WINDOW_MEASURES_CONFIG if stem == "directional_change_by_window" else REGRESSION_CONFIG
    result = _run(stem, cfg)
    assert result.ref_part
    assert result.windows
    assert not result.df_results.empty
    m2b = _metrics_2b(result)
    assert m2b is not None


# --- 2. Ascending / descending symmetry ----------------------------------------


def test_ascending_descending_symmetry():
    asc = _metrics_2b(_run("uniform_ascending_steps"))
    desc = _metrics_2b(_run("uniform_descending_steps"))
    assert np.isfinite(asc.A_tensor) and np.isfinite(desc.A_tensor)
    assert abs(asc.A_tensor - desc.A_tensor) < 0.15
    assert abs(asc.R - desc.R) < 0.15
    # Signed pitch drift D encodes registral direction; tensor axis μ ≈ π/2 for both.
    assert asc.D > 0.5
    assert desc.D < -0.5
    assert asc.D * desc.D < 0


# --- 3. Transposition invariance ------------------------------------------------


def test_transposition_invariance():
    base = _metrics_2b(_run("uniform_ascending_steps"))
    trans = _metrics_2b(_run("transposed_same_contour"))
    for attr in ("A_tensor", "R", "mu"):
        assert abs(getattr(base, attr) - getattr(trans, attr)) < 0.05
    assert abs(_flow_u(base) - _flow_u(trans)) < 0.05
    assert abs(_flow_v(base) - _flow_v(trans)) < 0.05


# --- 4. Pitch inversion ---------------------------------------------------------


def test_pitch_inversion_inverts_D_not_flow_V_sign():
    """Inversion preserves axial/circular concentration; registral sign is in D, not flow_V."""
    base = _metrics_2b(_run("uniform_ascending_steps"))
    inv = _metrics_2b(_run("pitch_inversion_same_rhythm"))
    assert abs(base.A_tensor - inv.A_tensor) < 0.15
    assert abs(base.R - inv.R) < 0.15
    assert base.D > 0.5 and inv.D < -0.5
    assert base.D * inv.D < 0
    # flow_V may stay positive for both when μ ≈ π/2 — do not assert opposite flow_V.
    if np.isfinite(_flow_v(base)) and np.isfinite(_flow_v(inv)):
        assert _flow_v(base) > 0 and _flow_v(inv) > 0


# --- 5. Alternating vs uniform --------------------------------------------------


def test_alternating_axis_vs_uniform_direction():
    uniform = _metrics_2b(_run("uniform_ascending_steps"))
    alt = _metrics_2b(_run("alternating_up_down_same_axis"))
    assert alt.R < uniform.R - 0.2
    assert alt.tau > uniform.tau + 0.3
    assert abs(alt.D) < abs(uniform.D)
    # Axial anisotropy (A_tensor) may stay high while circular coherence R drops.
    if np.isfinite(alt.A_tensor) and np.isfinite(uniform.A_tensor):
        assert alt.A_tensor >= 0.5


# --- 6. Balanced four directions ------------------------------------------------


def test_balanced_four_directions_lower_concentration():
    uniform = _metrics_2b(_run("uniform_ascending_steps"))
    balanced = _metrics_2b(_run("balanced_four_directions"))
    assert balanced.R < uniform.R - 0.2
    assert balanced.tau > uniform.tau + 0.3


# --- 7. Parallel vs contrary ----------------------------------------------------


def test_parallel_vs_contrary_conflict():
    parallel = _run("parallel_ascending_parts")
    contrary = _run("contrary_motion_symmetric")
    c_par = _conflict(parallel)
    c_con = _conflict(contrary)
    # μ-based conflict is low for both (symmetric contours share principal axis μ).
    assert np.isfinite(c_par) and c_par < 0.15
    assert np.isfinite(c_con) and c_con < 0.15
    m_par = _metrics_2b(parallel)
    m_con = _metrics_2b(contrary)
    # Pooled transition field shows cancellation for contrary motion.
    assert m_par.R > m_con.R + 0.2
    assert abs(m_con.D) < 0.2
    parts_con = contrary.windows[0].metrics_by_part
    d_vals = [m.D for m in parts_con.values() if np.isfinite(m.D)]
    assert len(d_vals) >= 2
    assert d_vals[0] * d_vals[1] < 0


# --- 8. Oblique motion ----------------------------------------------------------


def test_oblique_motion_intermediate_or_distinct():
    parallel = _metrics_2b(_run("parallel_ascending_parts"))
    contrary = _metrics_2b(_run("contrary_motion_symmetric"))
    oblique = _metrics_2b(_run("oblique_motion"))
    assert oblique.R < parallel.R
    assert oblique.R > contrary.R - 0.1
    assert oblique.D != contrary.D or oblique.R != parallel.R


# --- 9. Windowed directional change ---------------------------------------------


def test_windowed_directional_change():
    result = _run("directional_change_by_window", WINDOW_MEASURES_CONFIG)
    assert len(result.windows) >= 2
    d_vals = []
    for w in result.windows:
        m = w.metrics_2b
        assert m is not None and m.n > 0
        d_vals.append(m.D)
    assert d_vals[0] > 0.5
    assert d_vals[-1] < -0.5


# --- 10. Dense vs sparse --------------------------------------------------------


def test_dense_events_not_equal_anisotropy():
    dense = _metrics_2b(_run("dense_events_no_direction"))
    sparse = _metrics_2b(_run("sparse_strong_direction"))
    assert dense.n > sparse.n
    assert sparse.R > dense.R + 0.2
    assert abs(sparse.D) > abs(dense.D)


# --- 11. Documentation completeness ---------------------------------------------


def test_documentation_lists_all_fixtures():
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "Important semantic findings from Phase 1" in text
    for finding in (
        "D, not flow_V",
        "axial",
        "Contrary contrapuntal motion",
        "Windowed analysis",
        "Time stretching",
    ):
        assert finding in text, f"Phase 1 finding missing from {DOC_PATH.name}: {finding!r}"
    for fixture_file in sorted(EXPECTED_FIXTURES):
        stem = fixture_file.replace(".xml", "")
        assert stem in text, f"{stem} missing from {DOC_PATH.name}"


# --- Static repetition (fixture-specific smoke) --------------------------------


def test_static_repetition_zero_pitch_displacement():
    result = _run("static_repetition")
    m = _metrics_2b(result)
    assert m.D == 0.0
    assert m.tau == 0.0
    assert not np.isfinite(_flow_v(m)) or abs(_flow_v(m)) < 0.15
    trans = result.trans_by_part[result.ref_part]
    assert (trans["dp"].abs() < 1e-9).all()


def test_uniform_ascending_positive_drift_and_concentration():
    m = _metrics_2b(_run("uniform_ascending_steps"))
    assert m.D > 0.5
    assert m.R > 0.5
    assert m.A_tensor > 0.5


def test_time_stretched_same_contour_stable():
    base = _metrics_2b(_run("uniform_ascending_steps"))
    stretched = _metrics_2b(_run("time_stretched_same_contour"))
    assert np.isfinite(stretched.A_tensor) and np.isfinite(stretched.R)
    assert abs(base.A_tensor - stretched.A_tensor) < 0.15
    assert abs(base.R - stretched.R) < 0.15
