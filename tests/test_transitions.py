"""Transition ontology: horizontal vs vertical, legacy mixed mode."""

from anisotropia.parsing import Event
from anisotropia.transitions import build_directional_transition_tables


def test_horizontal_melodic_no_fake_chord_chain():
    """Coincident chord tones collapse to one onset; one step to next time."""
    evs = [
        Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1, voice=1, is_chord_tone=True, is_unpitched=False),
        Event(t=0.0, ql=0.0, dur_ql=1.0, p=64.0, meas=1, voice=1, is_chord_tone=True, is_unpitched=False),
        Event(t=1.0, ql=1.0, dur_ql=1.0, p=67.0, meas=1, voice=1, is_chord_tone=False, is_unpitched=False),
    ]
    res = build_directional_transition_tables(
        evs, epsilon_dt=1e-9, legacy_mixed_mode=False, has_seconds=True,
    )
    assert len(res.horizontal) == 1
    # Collapse (60,64)->62 MIDI, then 62->67 melodic step (not 60->64->67 chain).
    assert abs(float(res.horizontal.iloc[0]["dp"]) - 5.0) < 1e-6


def test_legacy_mixed_preserves_stagger_style_pairs():
    """Legacy path uses transitions_from_events behaviour on ordered list."""
    evs = [
        Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1, voice=1),
        Event(t=1e-9, ql=1e-8, dur_ql=1.0, p=64.0, meas=1, voice=1),
    ]
    res = build_directional_transition_tables(
        evs, epsilon_dt=1e-12, legacy_mixed_mode=True, has_seconds=True,
    )
    assert res.stats.get("n_candidate_transitions_legacy", 0) >= 1


def test_epsilon_excludes_tiny_dt_in_legacy():
    evs = [
        Event(t=0.0, ql=0.0, dur_ql=1.0, p=60.0, meas=1, voice=1),
        Event(t=1e-15, ql=1e-15, dur_ql=1.0, p=61.0, meas=1, voice=1),
    ]
    res = build_directional_transition_tables(
        evs, epsilon_dt=1e-6, legacy_mixed_mode=True, has_seconds=False,
    )
    # dt_ql tiny -> vertical bucket in legacy split
    assert len(res.horizontal) == 0 or res.horizontal["dt_ql"].abs().min() > 1e-9
