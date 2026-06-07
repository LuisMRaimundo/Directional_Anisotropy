"""Additional focused tests for anisotropia.parsing symbolic event extraction."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import math
import pytest

from music21 import chord, converter, duration, note, percussion, stream

from anisotropia.config import GracePolicyNotImplementedError
from anisotropia.parsing import (
    Event,
    _collapse_same_ql,
    _is_grace_element,
    _midis_from_percussion_chord,
    _musicxml_text_for_part_ids,
    _part_dictionary_key,
    _stagger_simultaneous_onsets,
    _unpitched_display_midi,
    _voice_id,
    chord_pitch_rep,
    element_pitch_rep,
    parse_musicxml,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _minimal_bytes() -> bytes:
    return (FIXTURES / "minimal_score.xml").read_bytes()


def _build_two_voice_score(*, part_name: str = "Poly", part_id: str = "P1") -> stream.Score:
    """Score with two MusicXML-style voices on one part (voice attr set in memory)."""
    m = stream.Measure()
    for pitch, voice in (("C4", 1), ("E4", 2), ("D4", 1), ("G4", 2)):
        n = note.Note(pitch, quarterLength=1)
        n.voice = voice
        m.append(n)
    p = stream.Part()
    p.partName = part_name
    p.id = part_id
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    return sc


def _build_single_voice_score() -> stream.Score:
    m = stream.Measure()
    for pitch in ("C4", "D4"):
        n = note.Note(pitch, quarterLength=1)
        n.voice = 1
        m.append(n)
    p = stream.Part()
    p.partName = "Solo"
    p.id = "P1"
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    return sc


def _score_to_bytes(sc: stream.Score, filename: str = "test.xml") -> bytes:
    path = sc.write("musicxml")
    return Path(path).read_bytes()


def _patch_parse(monkeypatch: pytest.MonkeyPatch, sc) -> None:
    original = converter.parse

    def _fake_parse(_path):
        return sc

    monkeypatch.setattr(converter, "parse", _fake_parse)


# --- 1. Invalid pitch_space -------------------------------------------------


def test_invalid_pitch_space_raises_value_error():
    with pytest.raises(ValueError, match="written|sounding"):
        parse_musicxml(_minimal_bytes(), "minimal.xml", pitch_space="invalid")


# --- 2–4. split_voices grouping ---------------------------------------------


def test_split_voices_false_merges_voices_under_one_part_key(monkeypatch):
    sc = _build_two_voice_score()
    _patch_parse(monkeypatch, sc)
    events, _, _ = parse_musicxml(b"<score/>", "two_voice.xml", split_voices=False)
    assert len(events) == 1
    key = next(iter(events))
    assert "Poly" in key
    assert "| v" not in key
    evs = events[key]
    assert len(evs) == 4
    assert sorted(e.p for e in evs) == [60.0, 62.0, 64.0, 67.0]
    assert {e.voice for e in evs} == {1, 2}


def test_split_voices_true_preserves_separate_voice_labels(monkeypatch):
    sc = _build_two_voice_score()
    _patch_parse(monkeypatch, sc)
    events, _, _ = parse_musicxml(b"<score/>", "two_voice.xml", split_voices=True)
    assert len(events) == 2
    labels = sorted(events.keys())
    assert all("Poly" in lab for lab in labels)
    assert any(lab.endswith("| v1") for lab in labels)
    assert any(lab.endswith("| v2") for lab in labels)
    v1 = next(v for k, v in events.items() if k.endswith("| v1"))
    v2 = next(v for k, v in events.items() if k.endswith("| v2"))
    assert sorted(e.p for e in v1) == [60.0, 62.0]
    assert sorted(e.p for e in v2) == [64.0, 67.0]


def test_split_voices_true_single_voice_keeps_part_label_without_suffix(monkeypatch):
    sc = _build_single_voice_score()
    _patch_parse(monkeypatch, sc)
    events, _, _ = parse_musicxml(b"<score/>", "solo.xml", split_voices=True)
    assert len(events) == 1
    key = next(iter(events))
    assert "Solo" in key
    assert "| v" not in key
    assert len(events[key]) == 2


# --- 5–6. Repeat expansion warnings -----------------------------------------


def test_expand_repeats_none_appends_warning_and_continues(monkeypatch):
    sc = _build_single_voice_score()

    def _none_repeats():
        return None

    sc.expandRepeats = _none_repeats
    _patch_parse(monkeypatch, sc)
    events, _, warns = parse_musicxml(b"<score/>", "solo.xml", expand_repeats=True)
    assert len(events) == 1
    assert len(events[next(iter(events))]) == 2
    assert len(warns) == 1
    assert "expandRepeats() returned None" in warns[0]
    assert "unexpanded score" in warns[0]


def test_expand_repeats_exception_appends_warning_and_continues(monkeypatch):
    sc = _build_single_voice_score()

    def _boom():
        raise RuntimeError("repeat engine offline")

    sc.expandRepeats = _boom
    _patch_parse(monkeypatch, sc)
    events, _, warns = parse_musicxml(b"<score/>", "solo.xml", expand_repeats=True)
    assert len(events) == 1
    assert len(warns) == 1
    assert "expandRepeats() failed" in warns[0]
    assert "repeat engine offline" in warns[0]


# --- 7. Score without .parts fallback ---------------------------------------


def test_part_without_parts_attribute_parsed_as_single_part(monkeypatch):
    part = _build_single_voice_score().parts[0]

    def _parse_part_only(_path):
        return part

    monkeypatch.setattr(converter, "parse", _parse_part_only)
    assert not hasattr(part, "parts")
    events, _, _ = parse_musicxml(b"<score/>", "solo.xml")
    assert len(events) == 1
    assert len(next(iter(events.values()))) == 2


# --- 8. Grace policy validation -----------------------------------------------


def test_grace_policy_include_keeps_grace_notes(monkeypatch):
    sc = stream.Score()
    m = stream.Measure()
    main = note.Note("C4", quarterLength=1)
    grace = note.Note("E5")
    grace.duration = duration.GraceDuration()
    m.append(main)
    m.append(grace)
    p = stream.Part(partName="GracePart", id="P1")
    p.append(m)
    sc.insert(0, p)
    _patch_parse(monkeypatch, sc)

    excluded, _, _ = parse_musicxml(b"<score/>", "grace.xml", grace_policy="exclude")
    included, _, _ = parse_musicxml(b"<score/>", "grace.xml", grace_policy="include")
    assert len(next(iter(excluded.values()))) == 1
    assert len(next(iter(included.values()))) == 2


def test_invalid_grace_policy_raises_value_error():
    with pytest.raises(ValueError, match="grace_policy"):
        parse_musicxml(_minimal_bytes(), "minimal.xml", grace_policy="not-a-policy")


def test_grace_include_attached_raises_not_implemented():
    with pytest.raises(GracePolicyNotImplementedError, match="include_attached"):
        parse_musicxml(_minimal_bytes(), "minimal.xml", grace_policy="include_attached")


def test_exclude_grace_true_overrides_grace_policy(monkeypatch):
    sc = stream.Score()
    m = stream.Measure()
    m.append(note.Note("C4", quarterLength=1))
    gn = note.Note("G5")
    gn.duration = duration.GraceDuration()
    m.append(gn)
    p = stream.Part(partName="G", id="P1")
    p.append(m)
    sc.insert(0, p)
    _patch_parse(monkeypatch, sc)

    events, _, _ = parse_musicxml(
        b"<score/>", "grace.xml", exclude_grace=True, grace_policy="include"
    )
    assert len(next(iter(events.values()))) == 1


# --- 9. Measure-boundary fallback -------------------------------------------


def test_measure_boundary_failure_falls_back_without_crash(monkeypatch):
    sc = _build_single_voice_score()
    part = sc.parts[0]
    original_get = part.getElementsByClass

    def _failing_get(cls):
        if cls is stream.Measure:
            raise RuntimeError("measure index unavailable")
        return original_get(cls)

    part.getElementsByClass = _failing_get
    _patch_parse(monkeypatch, sc)
    events, _, _ = parse_musicxml(b"<score/>", "solo.xml")
    evs = next(iter(events.values()))
    assert len(evs) == 2
    assert all(e.meas == 0 for e in evs)


# --- 10. Offset fallback ------------------------------------------------------


def test_offset_fallback_when_hierarchy_offset_fails(monkeypatch):
    class _BrokenOffsetNote(note.Note):
        def getOffsetInHierarchy(self, _ctx):
            raise RuntimeError("hierarchy offset failed")

    sc = stream.Score()
    m = stream.Measure()
    n = _BrokenOffsetNote("A4", quarterLength=1)
    m.insert(3.5, n)
    p = stream.Part(partName="OffsetPart", id="P1")
    p.append(m)
    sc.insert(0, p)
    _patch_parse(monkeypatch, sc)

    events, _, _ = parse_musicxml(b"<score/>", "offset.xml")
    ev = next(iter(events.values()))[0]
    assert ev.ql == pytest.approx(3.5)
    assert ev.p == 69.0


# --- 11. Rests and empty elements -------------------------------------------


def test_rests_do_not_create_pitched_events():
    m = stream.Measure()
    m.append(note.Rest(quarterLength=1))
    m.append(note.Note("C4", quarterLength=1))
    p = stream.Part(partName="RestPart")
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    data = _score_to_bytes(sc, "rest.xml")
    events, _, _ = parse_musicxml(data, "rest.xml")
    evs = next(iter(events.values()))
    assert len(evs) == 1
    assert evs[0].p == 60.0


def test_empty_chord_skipped_without_crash():
    m = stream.Measure()
    m.append(chord.Chord([]))
    m.append(note.Note("D4", quarterLength=1))
    p = stream.Part(partName="EmptyChord")
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    data = _score_to_bytes(sc, "empty_chord.xml")
    events, _, _ = parse_musicxml(data, "empty_chord.xml")
    evs = next(iter(events.values()))
    assert len(evs) == 1
    assert evs[0].p == 62.0


def test_unusable_pitch_rep_skipped_without_crash(monkeypatch):
    sc = stream.Score()
    part = stream.Part(partName="NoPitch", id="P1")
    sc.insert(0, part)
    _patch_parse(monkeypatch, sc)

    unusable = note.Note("C4", quarterLength=1)
    usable = note.Note("E4", quarterLength=1)
    original_epr = element_pitch_rep

    def _epr(el, rep="centroid"):
        if el is unusable:
            return None
        return original_epr(el, rep=rep)

    monkeypatch.setattr("anisotropia.parsing.element_pitch_rep", _epr)

    original_recurse = part.recurse

    def _patched_recurse():
        r = original_recurse()

        class _R:
            def getElementsByClass(self, cls):
                if cls is note.NotRest:
                    return [unusable, usable]
                return r.getElementsByClass(cls)

        return _R()

    part.recurse = _patched_recurse
    events, _, _ = parse_musicxml(b"<score/>", "no_pitch.xml")
    evs = next(iter(events.values()))
    assert len(evs) == 1
    assert evs[0].p == 64.0


# --- 12. Unpitched / percussion branches -------------------------------------


def test_unpitched_only_percussion_chord_excluded_with_exclude_policy(monkeypatch):
    sc = stream.Score()
    m = stream.Measure()
    u1 = note.Unpitched()
    u1.displayStep = "F"
    u1.displayOctave = 4
    u2 = note.Unpitched()
    u2.displayStep = "A"
    u2.displayOctave = 4
    pc = percussion.PercussionChord([u1, u2])
    m.append(pc)
    m.append(note.Note("C4", quarterLength=1))
    p = stream.Part(partName="Perc", id="P1")
    p.append(m)
    sc.insert(0, p)
    _patch_parse(monkeypatch, sc)

    mapped, _, _ = parse_musicxml(
        b"<score/>", "perc.xml", unpitched_policy="map_display", expand_chord_pitches=False
    )
    excluded, _, _ = parse_musicxml(
        b"<score/>", "perc.xml", unpitched_policy="exclude", expand_chord_pitches=False
    )
    assert len(next(iter(mapped.values()))) == 2
    assert len(next(iter(excluded.values()))) == 1


def test_unpitched_display_midi_failure_returns_none():
    broken = note.Unpitched()

    def _boom():
        raise RuntimeError("no display pitch")

    broken.displayPitch = _boom
    assert _unpitched_display_midi(broken) is None
    assert element_pitch_rep(broken) is None


def test_percussion_chord_expand_pitches_skips_empty_midis(monkeypatch):
    sc = stream.Score()
    m = stream.Measure()
    u = note.Unpitched()
    u.displayPitch = lambda: None
    pc = percussion.PercussionChord([u])
    m.append(pc)
    m.append(note.Note("G4", quarterLength=1))
    p = stream.Part(partName="Perc2", id="P1")
    p.append(m)
    sc.insert(0, p)
    _patch_parse(monkeypatch, sc)

    events, _, _ = parse_musicxml(
        b"<score/>", "perc2.xml", expand_chord_pitches=True, unpitched_policy="map_display"
    )
    evs = next(iter(events.values()))
    assert len(evs) == 1
    assert evs[0].p == 67.0


# --- 13. Defensive continue / helper branches -------------------------------


def test_seconds_mapping_failure_falls_back_to_ql(monkeypatch):
    sc = _build_single_voice_score()

    class _BrokenSecondsNote(note.Note):
        def getOffsetInHierarchy(self, ctx):
            base = super().getOffsetInHierarchy(ctx)
            if hasattr(base, "seconds"):
                raise RuntimeError("seconds unavailable")
            return base

    part = sc.parts[0]
    for el in part.recurse().getElementsByClass(note.Note):
        el.__class__ = _BrokenSecondsNote

    _patch_parse(monkeypatch, sc)
    events, has_seconds, _ = parse_musicxml(b"<score/>", "solo.xml")
    assert has_seconds is False
    evs = next(iter(events.values()))
    assert len(evs) == 2
    assert all(e.t == e.ql for e in evs)


def test_strip_ties_failure_keeps_original_part(monkeypatch):
    sc = _build_single_voice_score()
    part = sc.parts[0]

    def _strip_fail(_inPlace=False):
        raise RuntimeError("strip ties failed")

    part.stripTies = _strip_fail
    _patch_parse(monkeypatch, sc)
    events, _, _ = parse_musicxml(b"<score/>", "solo.xml", merge_tied_notes=True)
    assert len(next(iter(events.values()))) == 2


def test_voice_id_defensive_defaults():
    assert _voice_id(SimpleNamespace(voice=None)) == 1
    assert _voice_id(SimpleNamespace(voice=0)) == 1
    assert _voice_id(SimpleNamespace(voice="bad")) == 1
    assert _voice_id(SimpleNamespace(voice=3)) == 3


def test_is_grace_element_without_duration_is_false():
    assert _is_grace_element(SimpleNamespace()) is False


def test_collapse_same_ql_merges_simultaneous_pitches():
    evs = [
        Event(t=0, ql=0, dur_ql=1, p=60, meas=1),
        Event(t=0, ql=0, dur_ql=0.5, p=64, meas=1),
    ]
    out = _collapse_same_ql(evs)
    assert len(out) == 1
    assert out[0].p == pytest.approx(62.0)
    assert out[0].dur_ql == pytest.approx(1.0)


def test_stagger_simultaneous_onsets_spreads_ql():
    evs = [
        Event(t=0, ql=0, dur_ql=1, p=60, meas=1),
        Event(t=0, ql=0, dur_ql=1, p=64, meas=1),
    ]
    out = _stagger_simultaneous_onsets(evs, has_seconds=False)
    assert len(out) == 2
    assert out[0].ql < out[1].ql


def test_expand_chord_pitches_false_collapses_chord_to_centroid():
    m = stream.Measure()
    m.append(chord.Chord(["C4", "E4", "G4"], quarterLength=1))
    p = stream.Part(partName="Ch")
    p.append(m)
    sc = stream.Score()
    sc.insert(0, p)
    data = _score_to_bytes(sc, "chord_collapse.xml")
    events, _, _ = parse_musicxml(
        data, "chord_collapse.xml", expand_chord_pitches=False, chord_rep="centroid"
    )
    evs = next(iter(events.values()))
    assert len(evs) == 1
    assert evs[0].p == pytest.approx(63.666666666666664)


def test_chord_pitch_rep_empty_returns_nan():
    assert math.isnan(chord_pitch_rep(chord.Chord([])))


def test_part_dictionary_key_grand_staff_merge():
    assert _part_dictionary_key("Piano", "P1-Staff1", merge_grand_staff=True) == "Piano (P1)"
    assert _part_dictionary_key("Piano", "P1-Staff2", merge_grand_staff=True) == "Piano (P1)"
    assert (
        _part_dictionary_key("Piano", "P1-Staff1", merge_grand_staff=False) == "Piano (P1-Staff1)"
    )


def test_musicxml_text_for_part_ids_plain_xml():
    xml = _minimal_bytes()
    text = _musicxml_text_for_part_ids(xml, "minimal.xml")
    assert text is not None
    assert "<score-part" in text


def test_fake_not_rest_with_invalid_duration_continues(monkeypatch):
    class _FakeElem:
        duration = SimpleNamespace(quarterLength=None)
        voice = 1
        offset = 0.0

        def getOffsetInHierarchy(self, _ctx):
            return 0.0

    sc = stream.Score()
    part = stream.Part(partName="Fake", id="P1")
    sc.insert(0, part)
    _patch_parse(monkeypatch, sc)

    original_recurse = part.recurse

    def _patched_recurse():
        r = original_recurse()

        class _R:
            def getElementsByClass(self, cls):
                if cls is note.NotRest:
                    return [_FakeElem(), note.Note("B4", quarterLength=1)]
                return r.getElementsByClass(cls)

        return _R()

    part.recurse = _patched_recurse
    events, _, _ = parse_musicxml(b"<score/>", "fake.xml")
    evs = next(iter(events.values()))
    assert len(evs) == 1
    assert evs[0].p == 71.0


def test_midis_from_percussion_chord_mixed_members():
    u = note.Unpitched()
    u.displayStep = "C"
    u.displayOctave = 4
    n = note.Note("E5")
    midis = _midis_from_percussion_chord(percussion.PercussionChord([u, n]))
    assert sorted(midis) == [60.0, 76.0]
