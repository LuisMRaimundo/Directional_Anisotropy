"""rms_scale: uncentred weighted-RMS standardisation of (Δt, Δp)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from anisotropia.config import AnalysisConfig
from anisotropia.metrics import (
    _compute_tensor_and_R_internal,
    _standardize_dt_dp,
    compute_metrics_from_transitions,
)
from anisotropia.pipeline import run_analysis
from corpus.benchmark_profile import BENCHMARK_CONFIG, THESIS_PROFILE

N = 16
TOL = 1e-9
FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
REF = Path(__file__).resolve().parents[1] / "corpus" / "reference_outputs"


def _frame(dt: list[float] | np.ndarray, dp: list[float] | np.ndarray) -> pd.DataFrame:
    dt_a = np.asarray(dt, dtype=float)
    dp_a = np.asarray(dp, dtype=float)
    assert len(dt_a) == N and len(dp_a) == N
    w = np.ones(N)
    return pd.DataFrame(
        {
            "dt_ql": dt_a,
            "dt_sec": dt_a,
            "dp": dp_a,
            "w_dur": w,
            "w_min": w,
        }
    )


def _A(df: pd.DataFrame, mode: str = "rms_scale") -> float:
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize=mode)
    return float(m.A_tensor)


def test_a_regular_chromatic_scale_is_anisotropic():
    df = _frame(np.ones(N), np.ones(N))
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize="rms_scale")
    assert m.A_tensor == pytest.approx(1.0, abs=TOL)
    m_z = compute_metrics_from_transitions(df, "ql", "dur", standardize="local_zscore")
    assert m.D == pytest.approx(m_z.D, abs=TOL)
    assert m.tau == pytest.approx(m_z.tau, abs=TOL)
    assert m.R == pytest.approx(m_z.R, abs=TOL)


def test_b_alternating_neighbour_note_is_isotropic():
    dp = np.array([1.0, -1.0] * (N // 2))
    df = _frame(np.ones(N), dp)
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize="rms_scale")
    assert m.A_tensor == pytest.approx(0.0, abs=TOL)
    m_z = compute_metrics_from_transitions(df, "ql", "dur", standardize="local_zscore")
    assert m.R == pytest.approx(m_z.R, abs=TOL)


def test_c_alternating_figure_is_invariant_to_dt_unit():
    dp = np.array([1.0, -1.0] * (N // 2))
    df = _frame(np.full(N, 0.25), dp)
    assert _A(df) == pytest.approx(0.0, abs=TOL)


def test_d_repeated_notes_are_finite_and_anisotropic():
    df = _frame(np.ones(N), np.zeros(N))
    m = compute_metrics_from_transitions(df, "ql", "dur", standardize="rms_scale")
    assert math.isfinite(m.A_tensor)
    assert m.A_tensor == pytest.approx(1.0, abs=TOL)
    assert not math.isnan(m.A_tensor)


def test_e_scale_invariance_of_A_tensor():
    dp = np.tile(np.array([1.0, 2.0, -1.0, 3.0]), N // 4)
    base = _frame(np.ones(N), dp)
    scaled = _frame(np.ones(N) * 3.0, dp * 2.0)
    assert _A(base) == pytest.approx(_A(scaled), abs=TOL)


def test_f_rms_scale_does_not_centre():
    v1 = np.array([1.0, 1.0, 1.0, 1.0])
    v2 = np.array([1.0, 2.0, 3.0, 4.0])
    w = np.array([1.0, 1.0, 2.0, 1.0])
    wsum = float(np.sum(w))
    out1, out2 = _standardize_dt_dp(v1, v2, w, wsum, "rms_scale")
    mean2 = float(np.sum(w * out2) / wsum)
    assert mean2 > 0.0
    assert np.all(out2 > 0.0)
    assert np.all(np.sign(out2) == np.sign(v2))
    assert np.all(np.sign(out1) == np.sign(v1))


def test_g_local_zscore_frozen_reference_unchanged():
    assert BENCHMARK_CONFIG.standardization_mode == "local_zscore"
    assert THESIS_PROFILE.standardization_mode == "rms_scale"
    ref_path = REF / "SYNTH_MINIMAL_ASCENDING.json"
    if not ref_path.exists():
        pytest.skip("frozen reference not generated")
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    result = run_analysis(xml, "minimal_score.xml", BENCHMARK_CONFIG)
    m = result.windows[0].metrics_2b
    exp = ref["metrics_2b"]
    assert abs(m.D - exp["D"]) < TOL
    assert abs(m.tau - exp["tau"]) < TOL
    assert abs(m.A_tensor - exp["A_tensor"]) < TOL
    assert abs(m.R - exp["R"]) < TOL
    assert m.n == exp["n"]


def test_report_and_metadata_record_the_mode():
    from anisotropia.report import generate_report
    from anisotropia.reproducibility import build_reproducibility_metadata

    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
    meta = build_reproducibility_metadata(filename="m.xml", xml_bytes=xml, config=cfg, time_axis_effective="ql")
    assert meta["standardization_mode"] == "rms_scale"
    result = run_analysis(xml, "m.xml", cfg)
    text = generate_report("m.xml", result.df_results, {**result.report_params, **result.reproducibility}, 1, 1, 1)
    assert "rms_scale" in text
    assert "No centring is applied" in text


def test_bool_true_still_means_local_zscore():
    df = _frame(np.ones(N), np.ones(N))
    m_true = compute_metrics_from_transitions(df, "ql", "dur", standardize=True)
    m_z = compute_metrics_from_transitions(df, "ql", "dur", standardize="local_zscore")
    m_rms = compute_metrics_from_transitions(df, "ql", "dur", standardize="rms_scale")
    assert math.isnan(m_true.A_tensor)
    assert math.isnan(m_z.A_tensor)
    assert m_rms.A_tensor == pytest.approx(1.0, abs=TOL)
    assert AnalysisConfig().standardization_mode == "rms_scale"


def test_bool_false_still_means_none():
    dt = np.array([1.0, 2.0, 3.0, 4.0])
    dp = np.array([1.0, -1.0, 2.0, -2.0])
    w = np.ones(4)
    a_false = _compute_tensor_and_R_internal(dt, dp, w, False)[0]
    a_none = _compute_tensor_and_R_internal(dt, dp, w, "none")[0]
    assert a_false == pytest.approx(a_none, abs=TOL)
