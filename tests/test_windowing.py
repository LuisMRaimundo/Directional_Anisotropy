"""Testes para funções de janelamento."""

import pandas as pd

from anisotropia.windowing import parse_event_window_label, window_slices_for_part, window_sort_key


def test_parse_event_window_label_valid():
    assert parse_event_window_label("e25–e74") == (25, 74)
    assert parse_event_window_label("e0–e49") == (0, 49)


def test_parse_event_window_label_invalid():
    assert parse_event_window_label("invalid") == (None, None)
    assert parse_event_window_label("e25") == (None, None)
    assert parse_event_window_label("") == (None, None)


def test_window_slices_total():
    df = pd.DataFrame({"meas": [1, 2, 3], "t": [0.0, 1.0, 2.0]})
    wins = window_slices_for_part(df, "total", 1, 1)
    assert len(wins) == 1
    assert wins[0][0] == "total"
    assert len(wins[0][1]) == 3


def test_window_sort_key():
    """Numeric ordering: m2 < m4 < m10, e0 < e25, t0 < t2.5, total=0."""
    assert window_sort_key("m2–m5") < window_sort_key("m4–m7")
    assert window_sort_key("m4–m7") < window_sort_key("m10–m13")
    assert window_sort_key("total") == 0.0
    assert sorted(["m10–m13", "m4–m7", "m2–m5"], key=window_sort_key) == ["m2–m5", "m4–m7", "m10–m13"]


def test_window_slices_events():
    df = pd.DataFrame({"meas": [1] * 50, "t": range(50)})
    wins = window_slices_for_part(df, "events", window_size=10, step=5)
    assert len(wins) >= 1
    assert wins[0][0].startswith("e")


def test_window_slices_empty():
    df = pd.DataFrame({"meas": [], "t": []})
    assert window_slices_for_part(df, "measures", 4, 2) == []


def test_window_slices_measures():
    df = pd.DataFrame({"meas": [1, 1, 2, 3, 4, 4], "t": [0.0, 0.5, 1.0, 2.0, 3.0, 4.0]})
    wins = window_slices_for_part(df, "measures", window_size=2, step=2)
    assert len(wins) >= 1
    assert all("m" in w[0] for w in wins)


def test_window_slices_measures_all_zero_uses_seconds():
    """meas ≡ 0 aciona fallback para janelas em segundos."""
    df = pd.DataFrame({"meas": [0, 0, 0], "t": [0.0, 1.0, 4.0]})
    wins = window_slices_for_part(df, "measures", window_size=2.0, step=1.0)
    assert len(wins) >= 1
    assert wins[0][0].startswith("t")


def test_window_slices_seconds():
    df = pd.DataFrame({"meas": [1, 2, 3], "t": [0.0, 2.0, 5.0]})
    wins = window_slices_for_part(df, "seconds", window_size=2.0, step=1.0)
    assert len(wins) >= 1
    assert wins[0][0].startswith("t")


def test_window_sort_key_variants():
    assert window_sort_key("t1.50–6.50") == 1.5
    assert window_sort_key("e25–e74") == 25.0
    assert window_sort_key("not-a-window") == 0.0
    assert window_sort_key("mxx\u2013myy") == 0.0  # parse failure → fallback


def test_parse_event_window_label_bad_inner():
    # en-dash (U+2013), igual ao usado nos rótulos e em parse_event_window_label
    assert parse_event_window_label("e\u2013e") == (None, None)
