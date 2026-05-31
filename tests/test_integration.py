"""Integration tests: full pipeline, window ordering, report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from anisotropia.metrics import (
    compute_directional_conflict,
    compute_metrics_from_transitions,
    aggregate_2A,
    aggregate_2B,
)
from anisotropia.parsing import parse_musicxml, transitions_from_events
from anisotropia.report import generate_report
from anisotropia.windowing import window_slices_for_part, window_sort_key


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_full_pipeline_single_part():
    """Full pipeline: parse -> transitions -> windowing -> metrics -> aggregate -> report."""
    xml_path = FIXTURES_DIR / "minimal_score.xml"
    if not xml_path.exists():
        pytest.skip("minimal_score.xml not found")
    xml_bytes = xml_path.read_bytes()
    events_by_part, has_sec, _ = parse_musicxml(xml_bytes, "minimal.xml")
    trans_by_part = {p: transitions_from_events(evs) for p, evs in events_by_part.items()}
    ref_part = max(trans_by_part.keys(), key=lambda k: len(trans_by_part[k]))
    windows = window_slices_for_part(trans_by_part[ref_part], "total", 1, 1)
    assert len(windows) == 1
    win_label, ref_wdf = windows[0]
    trans_windowed = {p: trans_by_part[p] for p in trans_by_part}
    metrics_part = {p: compute_metrics_from_transitions(trans_windowed[p], "ql", "dur") for p in trans_windowed}
    mB = aggregate_2B(trans_windowed, "ql", "dur")
    conflict = compute_directional_conflict(metrics_part)
    assert mB.n > 0
    assert mB.A_tensor > 0
    assert not isinstance(conflict, str)
    rows = [dict(window=win_label, scope="total_2B", part="TOTAL_2B", D=mB.D, tau=mB.tau, A_tensor=mB.A_tensor, mu=mB.mu, R=mB.R, n=mB.n)]
    df = pd.DataFrame(rows)
    report = generate_report("minimal.xml", df, dict(chord_rep="centroid", weight_mode="dur", window_mode="total", window_size=1, step=1, scientific_mode=False), 1, 1, 3)
    assert "Notational Anisotropy" in report
    assert "References" in report
    assert "Rousseeuw" in report
    assert "Weickert" not in report


def test_full_pipeline_multi_part_with_conflict():
    """Full pipeline with 2 parts: conflict computed, report includes conflict section."""
    xml_path = FIXTURES_DIR / "minimal_two_parts.xml"
    if not xml_path.exists():
        pytest.skip("minimal_two_parts.xml not found")
    xml_bytes = xml_path.read_bytes()
    events_by_part, _, _ = parse_musicxml(xml_bytes, "minimal_two.xml")
    trans_by_part = {p: transitions_from_events(evs) for p, evs in events_by_part.items()}
    ref_part = max(trans_by_part.keys(), key=lambda k: len(trans_by_part[k]))
    windows = window_slices_for_part(trans_by_part[ref_part], "total", 1, 1)
    assert len(windows) == 1
    win_label, _ = windows[0]
    trans_windowed = {p: trans_by_part[p] for p in trans_by_part}
    metrics_part = {p: compute_metrics_from_transitions(trans_windowed[p], "ql", "dur") for p in trans_windowed}
    mA = aggregate_2A(metrics_part)
    mB = aggregate_2B(trans_windowed, "ql", "dur")
    conflict = compute_directional_conflict(metrics_part)
    assert len(metrics_part) >= 2
    assert mA.n > 0
    assert mB.n > 0
    assert 0 <= conflict <= 1 or (conflict != conflict)  # nan is ok for aligned
    rows = [
        dict(window=win_label, scope="instrumento", part=p, D=m.D, tau=m.tau, A_tensor=m.A_tensor, mu=m.mu, R=m.R, n=m.n) for p, m in metrics_part.items()
    ]
    rows.append(dict(window=win_label, scope="total_2A", part="TOTAL_2A", D=mA.D, tau=mA.tau, A_tensor=mA.A_tensor, mu=mA.mu, R=mA.R, n=mA.n))
    rows.append(dict(window=win_label, scope="conflito", part="DIRECTIONAL_CONFLICT", conflict=conflict))
    df = pd.DataFrame(rows)
    report = generate_report("minimal_two.xml", df, dict(chord_rep="centroid", weight_mode="dur", window_mode="total", scientific_mode=False), 2, 1, 6)
    assert "Conflict" in report or "conflito" in report.lower() or "Conflito" in report


def test_window_ordering_numeric():
    """window_sort_key orders m10 after m4, m4 after m2; t and e by numeric value."""
    assert window_sort_key("m2–m5") < window_sort_key("m4–m7")
    assert window_sort_key("m4–m7") < window_sort_key("m10–m13")
    assert window_sort_key("m10–m13") < window_sort_key("m20–m23")
    assert window_sort_key("e0–e49") < window_sort_key("e25–e74")
    assert window_sort_key("e25–e74") < window_sort_key("e100–e149")
    assert window_sort_key("t0.00–5.00") < window_sort_key("t2.50–7.50")
    assert window_sort_key("total") == 0.0
    ordered = sorted(["m10–m13", "m4–m7", "m2–m5", "m20–m23"], key=window_sort_key)
    assert ordered == ["m2–m5", "m4–m7", "m10–m13", "m20–m23"]
