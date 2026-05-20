"""Janelamento por compassos, segundos, transições ou total."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


def window_sort_key(win_label: str) -> float:
    """
    Return numeric key for chronological ordering of window labels.
    m4–m7 -> 4, m10–m13 -> 10, t1.50–6.50 -> 1.5, e25–e74 -> 25, total -> 0.
    """
    if not win_label or win_label == "total":
        return 0.0
    s = win_label.strip()
    if s.startswith("m") and "–" in s:
        try:
            pre = s.split("–")[0].strip().lstrip("m")
            return float(int(pre))
        except ValueError:
            pass
    if s.startswith("t") and "–" in s:
        try:
            pre = s.split("–")[0].strip().lstrip("t")
            return float(pre)
        except ValueError:
            pass
    if s.startswith("e") and "–" in s:
        try:
            pre = s.split("–")[0].strip().lstrip("e")
            return float(int(pre))
        except ValueError:
            pass
    return 0.0


def parse_event_window_label(win_label: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse 'e25–e74' -> (i0, i1_last). Retorna (None, None) em falha."""
    parts = win_label.split("–")
    if len(parts) != 2:
        return None, None
    try:
        i0_str = parts[0].strip().lstrip("e")
        i1_str = parts[1].strip().lstrip("e")
        return int(i0_str), int(i1_str)
    except ValueError:
        return None, None


def window_slices_for_part(
    df_trans: pd.DataFrame,
    window_mode: str,
    window_size: float,
    step: float,
) -> List[Tuple[str, pd.DataFrame]]:
    """
    Janelas: 'measures' | 'seconds' | 'events' | 'total'.
    Retorna [(label, df_window), ...].
    """
    if df_trans.empty:
        return []
    windows: List[Tuple[str, pd.DataFrame]] = []
    if window_mode == "total":
        return [("total", df_trans.copy())]
    if window_mode == "measures":
        meas = df_trans["meas"].to_numpy()
        if np.all(meas == 0):
            window_mode = "seconds"
        else:
            mmin = int(np.min(meas))
            mmax = int(np.max(meas))
            size = max(int(window_size), 1)
            stp = max(int(step), 1)
            for m0 in range(mmin, mmax + 1, stp):
                m1 = m0 + size
                wdf = df_trans[(df_trans["meas"] >= m0) & (df_trans["meas"] < m1)]
                windows.append((f"m{m0}–m{m1-1}", wdf))
            return windows
    if window_mode == "seconds":
        t = df_trans["t"].to_numpy(dtype=float)
        tmin, tmax = float(np.min(t)), float(np.max(t))
        size = float(window_size)
        stp = float(step)
        if size <= 0:
            size = (tmax - tmin) if (tmax > tmin) else 1.0
        if stp <= 0:
            stp = size
        cur = tmin
        while cur <= tmax:
            wdf = df_trans[(df_trans["t"] >= cur) & (df_trans["t"] < cur + size)]
            windows.append((f"t{cur:.2f}–{(cur+size):.2f}", wdf))
            cur += stp
        return windows
    if window_mode == "events":
        n = len(df_trans)
        size = max(int(window_size), 1)
        stp = max(int(step), 1)
        for i0 in range(0, n, stp):
            i1 = min(i0 + size, n)
            wdf = df_trans.iloc[i0:i1]
            windows.append((f"e{i0}–e{i1-1}", wdf))
        return windows
    return windows
