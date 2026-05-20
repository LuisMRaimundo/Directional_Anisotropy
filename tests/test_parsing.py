"""Testes de parsing MusicXML."""

import pytest
from pathlib import Path

from anisotropia.parsing import (
    Event,
    parse_musicxml,
    transitions_from_events,
    chord_pitch_rep,
    element_pitch_rep,
)
from music21 import note, chord, percussion, stream


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_musicxml_minimal():
    """Parse de partitura mínima (4 notas ascendentes)."""
    xml_path = FIXTURES_DIR / "minimal_score.xml"
    if not xml_path.exists():
        pytest.skip("minimal_score.xml não encontrado")
    xml_bytes = xml_path.read_bytes()
    events_by_part, has_seconds = parse_musicxml(xml_bytes, "minimal.xml", chord_rep="centroid")
    assert len(events_by_part) >= 1
    part_name = list(events_by_part.keys())[0]
    evs = events_by_part[part_name]
    assert len(evs) == 4
    pitches = [e.p for e in evs]
    assert pitches[0] == 60
    assert pitches[-1] == 65
    assert all(e.meas >= 0 for e in evs)


def test_parse_musicxml_file_too_large():
    """Ficheiro acima do limite deve levantar ValueError."""
    large = b"x" * (51 * 1024 * 1024)
    with pytest.raises(ValueError, match="demasiado grande"):
        parse_musicxml(large, "large.xml")


def test_transitions_from_events():
    """Transições a partir de eventos."""
    evs = [
        Event(t=0, ql=0, dur_ql=1, p=60, meas=1),
        Event(t=1, ql=1, dur_ql=1, p=62, meas=1),
        Event(t=2, ql=2, dur_ql=1, p=64, meas=1),
    ]
    df = transitions_from_events(evs)
    assert len(df) == 2
    assert list(df["dp"]) == [2, 2]
    assert "dt_ql" in df.columns
    assert "w_dur" in df.columns


def test_transitions_from_events_single_note():
    """Uma única nota: sem transições."""
    evs = [Event(t=0, ql=0, dur_ql=1, p=60, meas=1)]
    df = transitions_from_events(evs)
    assert len(df) == 0
    assert "dp" in df.columns
    assert "dt_ql" in df.columns and "dt_sec" in df.columns
    assert list(df.columns) == ["ql", "t", "meas", "dp", "dt_ql", "dt_sec", "w_dur", "w_min"]


def test_chord_pitch_rep():
    """Representante de acorde: centroid, top, bottom."""
    c = chord.Chord([60, 64, 67])
    assert chord_pitch_rep(c, "centroid") == 63.666666666666664
    assert chord_pitch_rep(c, "top") == 67
    assert chord_pitch_rep(c, "bottom") == 60


def test_element_pitch_rep_note():
    """Representante de nota."""
    n = note.Note("C4")
    assert element_pitch_rep(n) == 60.0


def test_element_pitch_rep_unpitched_display_midi():
    """Unpitched: MIDI from display step/octave (score position)."""
    u = note.Unpitched()
    u.displayStep = "F"
    u.displayOctave = 4
    assert element_pitch_rep(u) == 65.0


def test_element_pitch_rep_percussion_chord_centroid():
    """PercussionChord: centroid of unpitched + note members."""
    pc = percussion.PercussionChord([note.Unpitched("C4"), note.Note("E5")])
    assert abs(element_pitch_rep(pc, "centroid") - (60.0 + 76.0) / 2) < 1e-6


def test_parse_musicxml_expand_chord_yields_one_event_per_pitch():
    """Each chord tone becomes an event; stagger keeps dt>0 between simultaneous tones."""
    m = stream.Measure()
    m.append(chord.Chord(["C4", "E4", "G4"], quarterLength=1))
    p = stream.Part()
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    tmp_path = sc.write("musicxml")
    data = Path(tmp_path).read_bytes()
    evs_by_part, _ = parse_musicxml(
        data, "chord.xml", expand_chord_pitches=True, chord_simultaneity="stagger",
    )
    evs = list(evs_by_part.values())[0]
    assert len(evs) == 3
    assert len({e.ql for e in evs}) == 3  # staggered ql (legacy micro-timing)
    assert sorted(e.p for e in evs) == [60.0, 64.0, 67.0]


def test_parse_musicxml_includes_unpitched_events():
    """Parts with only MusicXML unpitched notes produce events (Tom-style)."""
    m = stream.Measure()
    u = note.Unpitched()
    u.displayStep = "G"
    u.displayOctave = 5
    u.duration.quarterLength = 1
    m.append(u)
    u2 = note.Unpitched()
    u2.displayStep = "A"
    u2.displayOctave = 5
    u2.duration.quarterLength = 1
    m.append(u2)
    p = stream.Part()
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    tmp_path = sc.write("musicxml")
    data = Path(tmp_path).read_bytes()
    evs_by_part, _ = parse_musicxml(data, "unpitched.xml")
    evs = list(evs_by_part.values())[0]
    assert len(evs) == 2
    assert evs[0].p < evs[1].p


def test_parse_musicxml_ties_merged_to_one_onset_chain():
    """Tied continuation notes must not appear as a separate melodic step (stripTies)."""
    from music21 import stream, tie

    m = stream.Measure()
    n1 = note.Note("C4", quarterLength=2)
    n2 = note.Note("C4", quarterLength=2)
    n1.tie = tie.Tie("start")
    n2.tie = tie.Tie("stop")
    m.append(n1)
    m.append(n2)
    p = stream.Part()
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    tmp_path = sc.write("musicxml")
    data = Path(tmp_path).read_bytes()
    evs_by_part, _ = parse_musicxml(data, "tied.xml")
    evs = list(evs_by_part.values())[0]
    assert len(evs) == 1
    assert evs[0].p == 60.0


def test_parse_musicxml_multi_measure_ordering():
    """ql_offset deve ser global na parte (getOffsetInHierarchy), não local à medida.
    Com el.offset, notas na medida 2 teriam offset 0,1... e ordenariam mal."""
    p = stream.Part()
    m1 = stream.Measure(number=1)
    m1.append(note.Note("C4", quarterLength=1))
    m1.append(note.Note("D4", quarterLength=1))
    p.append(m1)
    m2 = stream.Measure(number=2)
    m2.append(note.Note("E4", quarterLength=1))
    p.append(m2)
    sc = stream.Score()
    sc.insert(0, p)
    tmp_path = sc.write("musicxml")
    data = Path(tmp_path).read_bytes()
    evs_by_part, _ = parse_musicxml(data, "multi_measure.xml")
    evs = list(evs_by_part.values())[0]
    qls = [e.ql for e in evs]
    # Ordem correta: C4(0), D4(1), E4(2)
    assert qls == [0.0, 1.0, 2.0], f"ql incorretos (esperado [0,1,2]): {qls}"
    assert [e.p for e in evs] == [60, 62, 64]
    assert [e.dur_ql for e in evs] == [1.0, 1.0, 1.0]


def test_parse_musicxml_merge_tied_notes_false_keeps_tie_heads():
    """merge_tied_notes=False: each written note under a tie counts (more events)."""
    from music21 import stream, tie

    m = stream.Measure()
    n1 = note.Note("C4", quarterLength=2)
    n2 = note.Note("C4", quarterLength=2)
    n1.tie = tie.Tie("start")
    n2.tie = tie.Tie("stop")
    m.append(n1)
    m.append(n2)
    p = stream.Part()
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    tmp_path = sc.write("musicxml")
    data = Path(tmp_path).read_bytes()
    merged, _ = parse_musicxml(data, "tied2.xml", merge_tied_notes=True)
    split, _ = parse_musicxml(data, "tied2.xml", merge_tied_notes=False)
    assert len(list(merged.values())[0]) == 1
    assert len(list(split.values())[0]) == 2


def test_parse_musicxml_merge_grand_staff_two_staves_one_instrument():
    """P1-Staff1 + P1-Staff2 (same partName) → one key and combined events when merge_grand_staff."""
    xml_path = FIXTURES_DIR / "grand_staff_two_parts.xml"
    if not xml_path.exists():
        pytest.skip("grand_staff_two_parts.xml não encontrado")
    data = xml_path.read_bytes()

    merged, _ = parse_musicxml(data, "grand_staff_two_parts.xml", merge_grand_staff=True)
    assert len(merged) == 1
    assert "Piano (P1)" in merged
    evs = merged["Piano (P1)"]
    assert len(evs) == 2
    assert sorted(e.p for e in evs) == [55.0, 60.0]

    split, _ = parse_musicxml(data, "grand_staff_two_parts.xml", merge_grand_staff=False)
    assert len(split) == 2
    assert sum(len(v) for v in split.values()) == 2


def test_parse_musicxml_expand_repeats_smoke():
    """expand_repeats=True must not break; minimal score has no repeats so count unchanged."""
    xml_path = FIXTURES_DIR / "minimal_score.xml"
    if not xml_path.exists():
        pytest.skip("minimal_score.xml não encontrado")
    xml_bytes = xml_path.read_bytes()
    a, _ = parse_musicxml(xml_bytes, "minimal.xml", expand_repeats=False)
    b, _ = parse_musicxml(xml_bytes, "minimal.xml", expand_repeats=True)
    assert sum(len(v) for v in a.values()) == sum(len(v) for v in b.values())

