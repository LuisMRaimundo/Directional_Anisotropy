"""Validação em corpus de referência."""

import pytest
from pathlib import Path

from anisotropia.parsing import parse_musicxml, transitions_from_events
from anisotropia.metrics import aggregate_2B
from anisotropia.windowing import window_slices_for_part


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_reference_corpus_minimal_score():
    """
    Legacy-path smoke on minimal_score.xml (transitions_from_events + aggregate_2B).

    Frozen benchmark comparison uses run_analysis via test_pipeline / corpus scripts.
    See CORPUS_REFERENCIA.md for expected behaviour.
    """
    xml_path = FIXTURES_DIR / "minimal_score.xml"
    if not xml_path.exists():
        pytest.skip("minimal_score.xml não encontrado")
    xml_bytes = xml_path.read_bytes()
    events_by_part, _ = parse_musicxml(xml_bytes, "minimal.xml")
    trans_by_part = {
        part: transitions_from_events(evs)
        for part, evs in events_by_part.items()
    }
    ref_part = max(trans_by_part.keys(), key=lambda k: len(trans_by_part[k]))
    windows = window_slices_for_part(trans_by_part[ref_part], "total", 1, 1)
    assert len(windows) == 1
    _, ref_wdf = windows[0]
    trans_windowed = {p: df for p, df in trans_by_part.items()}
    m = aggregate_2B(trans_windowed, "ql", "dur", standardize=True, bootstrap_ci=False)
    assert m.D > 0
    assert m.tau < 0.5
    assert m.A_tensor > 0.3
    assert m.R > 0.5
    assert m.n == 3
