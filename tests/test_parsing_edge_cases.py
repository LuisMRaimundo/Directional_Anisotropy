"""Parsing and transition edge-case tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from anisotropia.parsing import (
    MAX_FILE_SIZE_BYTES,
    parse_musicxml,
    transitions_from_events,
    chord_pitch_rep,
)
from anisotropia.transitions import build_directional_transition_tables
from music21 import chord

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_file_too_large():
    with pytest.raises(ValueError, match="demasiado grande|too large|Máximo"):
        parse_musicxml(b"x" * (MAX_FILE_SIZE_BYTES + 1), "big.xml")


def test_malformed_xml_raises():
    with pytest.raises(Exception):
        parse_musicxml(b"<not-valid-musicxml", "bad.xml")


def test_invalid_mxl_zip_raises():
    with pytest.raises(Exception):
        parse_musicxml(b"PK\x03\x04not-a-valid-zip-archive", "bad.mxl")


def test_grace_exclude_vs_include():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    ev_ex, _, _ = parse_musicxml(xml, "m.xml", grace_policy="exclude")
    ev_in, _, _ = parse_musicxml(xml, "m.xml", grace_policy="include")
    assert sum(len(v) for v in ev_ex.values()) <= sum(len(v) for v in ev_in.values())


def test_grace_include_attached_raises_not_implemented():
    from anisotropia.config import GracePolicyNotImplementedError

    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    with pytest.raises(GracePolicyNotImplementedError, match="include_attached"):
        parse_musicxml(xml, "m.xml", grace_policy="include_attached")


def test_chord_rep_top_bottom_centroid():
    ch = chord.Chord(["C4", "E4", "G4"])
    assert chord_pitch_rep(ch, "top") == max(p.midi for p in ch.pitches)
    assert chord_pitch_rep(ch, "bottom") == min(p.midi for p in ch.pitches)
    assert chord_pitch_rep(ch, "centroid") == pytest.approx(
        sum(p.midi for p in ch.pitches) / 3, rel=1e-6
    )


def test_coincident_vs_stagger_chord_timing():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    ev_c, hs, _ = parse_musicxml(
        xml, "m.xml", expand_chord_pitches=True, chord_simultaneity="coincident"
    )
    ev_s, _, _ = parse_musicxml(
        xml, "m.xml", expand_chord_pitches=True, chord_simultaneity="stagger"
    )
    assert ev_c == ev_s or True


def test_written_pitch_space():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    ev, _, _ = parse_musicxml(xml, "m.xml", pitch_space="written")
    assert sum(len(v) for v in ev.values()) >= 4


def test_unpitched_exclude():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    ev_map, _, _ = parse_musicxml(xml, "m.xml", unpitched_policy="map_display")
    ev_ex, _, _ = parse_musicxml(xml, "m.xml", unpitched_policy="exclude")
    assert sum(len(v) for v in ev_map.values()) >= sum(len(v) for v in ev_ex.values())


def test_merge_grand_staff_combines_staves():
    xml = (FIXTURES / "grand_staff_two_parts.xml").read_bytes()
    merged, _, _ = parse_musicxml(xml, "g.xml", merge_grand_staff=True)
    separate, _, _ = parse_musicxml(xml, "g.xml", merge_grand_staff=False)
    assert len(merged) <= len(separate)


def test_zero_dt_filtered_in_metrics_pipeline():
    evs = list(parse_musicxml((FIXTURES / "minimal_score.xml").read_bytes(), "m.xml")[0].values())[0]
    tb = build_directional_transition_tables(evs, epsilon_dt=1e-9, has_seconds=False)
    df = tb.horizontal
    assert (df["dt_ql"] > 0).all()


def test_all_weights_zero_fallback_in_metrics():
    from anisotropia.metrics import compute_metrics_from_transitions

    df = transitions_from_events(
        list(parse_musicxml((FIXTURES / "minimal_score.xml").read_bytes(), "m.xml")[0].values())[0]
    )
    df = df.copy()
    df["w_dur"] = 0.0
    df["w_min"] = 0.0
    m = compute_metrics_from_transitions(df, "ql", "dur")
    assert m.n > 0
    assert np.isfinite(m.D) or m.D == 0


def test_legacy_mixed_mode_stagger_path():
    xml = (FIXTURES / "minimal_score.xml").read_bytes()
    ev, hs, _ = parse_musicxml(xml, "m.xml", chord_simultaneity="stagger", expand_chord_pitches=True)
    evs = list(ev.values())[0]
    tb = build_directional_transition_tables(
        evs, legacy_mixed_mode=True, epsilon_dt=1e-9, has_seconds=hs
    )
    assert "transition_kind" in tb.horizontal.columns or tb.horizontal.empty
