"""Parsing de MusicXML e extracção de transições."""

from __future__ import annotations

import io
import math
import os
import re
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from music21 import converter, stream, note, chord, percussion

from anisotropia.config import validate_grace_policy

# Constants
EPSILON = 1e-9
# Synthetic spread for simultaneous chord tones / same-beat notes (ql units); keeps dt>0 for metrics
STAGGER_QL = 1e-8
STAGGER_T_SEC = 1e-9
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
VALID_SUFFIXES = (".mxl", ".musicxml", ".xml")


@dataclass
class Event:
    t: float
    ql: float
    dur_ql: float
    p: float
    meas: int
    voice: int = 1
    is_chord_tone: bool = False
    is_unpitched: bool = False


def chord_pitch_rep(ch: chord.Chord, rep: str = "centroid") -> float:
    midis = [p.midi for p in ch.pitches]
    if not midis:
        return float("nan")
    if rep == "top":
        return float(max(midis))
    if rep == "bottom":
        return float(min(midis))
    return float(sum(midis) / len(midis))


def _unpitched_display_midi(u: note.Unpitched) -> float | None:
    """MIDI from staff display step/octave (MusicXML unpitched percussion)."""
    try:
        pp = u.displayPitch()
        if pp is not None:
            return float(pp.midi)
    except Exception:
        pass
    return None


def _midis_from_percussion_chord(pc: percussion.PercussionChord) -> List[float]:
    """Collect MIDI values from Unpitched (display) and Note members."""
    midis: List[float] = []
    for n in pc.notes:
        if isinstance(n, note.Unpitched):
            m = _unpitched_display_midi(n)
            if m is not None and math.isfinite(m):
                midis.append(m)
        elif isinstance(n, note.Note) and n.pitch is not None:
            midis.append(float(n.pitch.midi))
    return midis


def _chord_rep_from_midis(midis: List[float], rep: str) -> float | None:
    if not midis:
        return None
    if rep == "top":
        return float(max(midis))
    if rep == "bottom":
        return float(min(midis))
    return float(sum(midis) / len(midis))


def element_pitch_rep(el, rep: str = "centroid") -> float | None:
    if isinstance(el, note.Note):
        if el.pitch is None:
            return None
        return float(el.pitch.midi)
    if isinstance(el, note.Unpitched):
        return _unpitched_display_midi(el)
    if isinstance(el, percussion.PercussionChord):
        return _chord_rep_from_midis(_midis_from_percussion_chord(el), rep)
    if isinstance(el, chord.Chord):
        return chord_pitch_rep(el, rep=rep)
    return None


def _is_grace_element(el) -> bool:
    try:
        return bool(el.duration.isGrace)
    except Exception:
        return False


def _voice_id(el) -> int:
    v = getattr(el, "voice", None)
    if v is None or v == 0:
        return 1
    try:
        return int(v)
    except Exception:
        return 1


def _musicxml_text_for_part_ids(file_bytes: bytes, filename: str) -> str | None:
    """
    Raw MusicXML text for metadata extraction. music21 may rewrite ``<score-part id>``
    when building :class:`~music21.stream.Part` objects, so grand-staff ids are read here.
    """
    lower = filename.lower()
    try:
        if lower.endswith(".mxl"):
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                inner_name: str | None = None
                if "META-INF/container.xml" in zf.namelist():
                    container = zf.read("META-INF/container.xml").decode("utf-8", errors="replace")
                    m = re.search(r'full-path\s*=\s*["\']([^"\']+)["\']', container)
                    if m:
                        cand = m.group(1).replace("\\", "/")
                        if cand in zf.namelist():
                            inner_name = cand
                if inner_name is None:
                    for n in zf.namelist():
                        if n.lower().endswith(".xml") and "META-INF" not in n.replace("\\", "/"):
                            inner_name = n
                            break
                if inner_name is None:
                    return None
                return zf.read(inner_name).decode("utf-8", errors="replace")
        if lower.endswith((".xml", ".musicxml")):
            return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return None
    return None


def _score_part_ids_in_order(xml_text: str) -> List[str]:
    """``<score-part id=...>`` values in ``<part-list>`` order (parallel to ``score.parts``)."""
    m = re.search(r"<part-list[^>]*>(.*?)</part-list>", xml_text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    block = m.group(1)
    return re.findall(r'<score-part[^>]+id\s*=\s*["\']([^"\']+)["\']', block, re.IGNORECASE)


def _part_dictionary_key(
    part_name: str,
    part_id: str | None,
    *,
    merge_grand_staff: bool,
) -> str:
    """
    Label for ``events_by_part``.

    When ``merge_grand_staff`` is True, parts whose MusicXML id follows the common
    pattern ``<base>-Staff<n>`` (e.g. ``P1-Staff1``, ``P1-Staff2`` for piano/harp)
    share one key ``"{part_name} ({base})"`` so the two staves are one instrument.
    Otherwise each physical part keeps ``"{part_name} ({full_id})"`` to avoid collisions.
    """
    if merge_grand_staff and part_id:
        m = re.match(r"^(.+)-Staff\d+$", str(part_id))
        if m:
            return f"{part_name} ({m.group(1)})"
    if part_id:
        return f"{part_name} ({part_id})"
    return part_name


def _collapse_same_ql(evs: List[Event]) -> List[Event]:
    """Merge events at identical onset (same part/voice) into one centroid pitch."""
    if not evs:
        return []
    evs = sorted(evs, key=lambda e: (e.ql, e.p))
    collapsed: List[Event] = []
    i = 0
    while i < len(evs):
        j = i + 1
        same = [evs[i]]
        while j < len(evs) and abs(evs[j].ql - evs[i].ql) < EPSILON:
            same.append(evs[j])
            j += 1
        if len(same) == 1:
            collapsed.append(same[0])
        else:
            centroid = float(np.mean([x.p for x in same]))
            dur_max = float(max(x.dur_ql for x in same))
            collapsed.append(Event(t=same[0].t, ql=same[0].ql, dur_ql=dur_max, p=centroid, meas=same[0].meas))
        i = j
    return collapsed


def _stagger_simultaneous_onsets(evs: List[Event], *, has_seconds: bool) -> List[Event]:
    """
    Same beat may contain several note heads (expanded chord). Spread ql (and t) by tiny
    increments so consecutive transitions have dt>0 and are not dropped by metrics.
    """
    if not evs:
        return []
    evs = sorted(evs, key=lambda e: (e.ql, e.p))
    out: List[Event] = []
    i = 0
    while i < len(evs):
        j = i + 1
        same = [evs[i]]
        while j < len(evs) and abs(evs[j].ql - evs[i].ql) < EPSILON:
            same.append(evs[j])
            j += 1
        for k, e in enumerate(same):
            dq = k * STAGGER_QL
            dt_extra = k * STAGGER_T_SEC if has_seconds else dq
            out.append(
                Event(
                    t=float(e.t + dt_extra),
                    ql=float(e.ql + dq),
                    dur_ql=e.dur_ql,
                    p=e.p,
                    meas=e.meas,
                )
            )
        i = j
    return out


def parse_musicxml(
    file_bytes: bytes,
    filename: str,
    chord_rep: str = "centroid",
    *,
    exclude_grace: bool | None = None,
    grace_policy: str | None = None,
    split_voices: bool = False,
    expand_chord_pitches: bool = True,
    chord_simultaneity: str = "coincident",
    merge_tied_notes: bool = True,
    expand_repeats: bool = False,
    merge_grand_staff: bool = True,
    pitch_space: str = "sounding",
    unpitched_policy: str = "map_display",
) -> Tuple[Dict[str, List[Event]], bool]:
    """
    Parse MusicXML into onset events per part (or per part+voice if ``split_voices``).

    **merge_tied_notes:** If True (default), ``stripTies()`` merges sustained pitches into
    one logical onset (fewer events). If False, **every written notehead** under a tie
    is kept — **more events**; Δp across a tie may be 0. Use for a “count everything
    printed” extraction.

    **expand_repeats:** If True, ``Score.expandRepeats()`` duplicates passages under
    repeat / volta / segno structures where music21 can expand them — **more events**
    for playback-like length.

    **Coverage:** Collects all ``NotRest`` elements — ``Note``, ``Chord``, ``Unpitched``,
    and ``PercussionChord``. Unpitched percussion uses ``displayPitch().midi`` (staff
    position), not General MIDI drum mapping.

    **expand_chord_pitches:** If True (default), each pitch in a chord / percussion chord
    becomes its own event (sorted by MIDI). ``chord_simultaneity`` chooses whether those
    share the same ``ql`` (``coincident``, recommended) or use the legacy micro-stagger.

    **grace_policy:** ``exclude`` (default, recommended for directional analysis), ``include``,
    or ``include_attached`` (currently treated as ``exclude``; full attachment not implemented).

    **pitch_space:** ``sounding`` (default, cross-instrument comparison) or ``written``.
    Applies ``Score.toSoundingPitch()`` when ``sounding``.

    **unpitched_policy:** ``map_display`` (default, staff position as MIDI proxy) or
    ``exclude`` (skip unpitched elements).

    Parameters
    ----------
    exclude_grace
        Deprecated: if set, overrides ``grace_policy`` (True → exclude, False → include).
    grace_policy
        ``exclude`` | ``include`` | ``include_attached``.
    split_voices
        If True, build **separate** event lists per MusicXML voice within each part
        (labels ``Name | v1``, ``Name | v2``, …). If only one voice exists, the part
        name has no suffix. Improves polyphonic precision vs. collapsing all voices
        into one mixed time-ordered line.

    **Part keys:** When a :class:`~music21.stream.Part` has an ``id`` (e.g. ``P1-Staff1``),
    the default key is ``"{partName} ({id})"`` so distinct parts do not overwrite.

    **merge_grand_staff:** If True (default), ``<score-part id>`` values matching
    ``<base>-Staff<n>`` (grand staff in many exports) are merged into one key
    ``"{partName} ({base})"`` and one combined event list (time-ordered). Raw XML ids are
    used when possible because music21 may rename duplicate part ``id`` attributes to the
    part name. Set False to keep each staff as a separate series (legacy behaviour).
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Ficheiro demasiado grande ({len(file_bytes) / 1024 / 1024:.1f} MB). "
            f"Máximo: {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB."
        )
    lower = filename.lower()
    suffix = next((s for s in VALID_SUFFIXES if lower.endswith(s)), ".xml")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, f"score{suffix}")
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)
        sc = converter.parse(tmp_path)
    if pitch_space == "sounding":
        try:
            sc.toSoundingPitch(inPlace=True)
        except Exception:
            pass
    elif pitch_space not in ("written", "sounding"):
        raise ValueError("pitch_space must be 'written' or 'sounding'")
    xml_text = _musicxml_text_for_part_ids(file_bytes, filename)
    score_part_ids = _score_part_ids_in_order(xml_text) if xml_text else []

    if expand_repeats:
        try:
            sc_exp = sc.expandRepeats()
            if sc_exp is not None:
                sc = sc_exp
        except Exception:
            pass
    parts_list = sc.parts if hasattr(sc, "parts") else [sc]
    use_xml_part_ids = bool(score_part_ids and len(score_part_ids) == len(parts_list))
    has_seconds = True
    try:
        _ = sc.secondsMap
    except Exception:
        has_seconds = False
    # Accumulate across parts so grand-staff pairs (P1-Staff1 + P1-Staff2) merge into one key.
    acc: Dict[str, Dict[int, List[Event]]] = defaultdict(lambda: defaultdict(list))
    _gp = grace_policy if grace_policy is not None else "exclude"
    if exclude_grace is not None:
        skip_grace = bool(exclude_grace)
        if grace_policy is not None:
            validate_grace_policy(_gp)
    else:
        _gp = validate_grace_policy(_gp)
        skip_grace = _gp == "exclude"

    parts = parts_list
    for idx, p in enumerate(parts):
        part_name = p.partName or p.id or f"Part_{idx+1}"
        # Prefer raw MusicXML score-part ids so P1-Staff1 / P1-Staff2 survive music21 import.
        pid = score_part_ids[idx] if use_xml_part_ids else getattr(p, "id", None)
        part_key = _part_dictionary_key(
            part_name,
            pid if pid else None,
            merge_grand_staff=merge_grand_staff,
        )
        measure_bounds: List[Tuple[float, int]] = []
        try:
            for m in p.getElementsByClass(stream.Measure):
                moff = float(m.offset)
                mnum = int(m.number) if m.number is not None else 0
                measure_bounds.append((moff, mnum))
            measure_bounds.sort(key=lambda x: x[0])
        except Exception:
            measure_bounds = []

        def measure_number_at_offset(ql_offset: float) -> int:
            if not measure_bounds:
                return 0
            lo, hi = 0, len(measure_bounds) - 1
            ans = measure_bounds[0][1]
            while lo <= hi:
                mid = (lo + hi) // 2
                if measure_bounds[mid][0] <= ql_offset:
                    ans = measure_bounds[mid][1]
                    lo = mid + 1
                else:
                    hi = mid - 1
            return ans

        p_work: stream.Part = p
        if merge_tied_notes:
            try:
                merged_ties = p.stripTies(inPlace=False)
                if merged_ties is not None:
                    p_work = merged_ties
            except Exception:
                p_work = p

        # NotRest: Note, Chord, Unpitched, PercussionChord (not Rest)
        raw_elems = list(p_work.recurse().getElementsByClass(note.NotRest))

        groups: Dict[int, List[Event]] = defaultdict(list)

        for el in raw_elems:
            if skip_grace and _is_grace_element(el):
                continue
            if unpitched_policy == "exclude":
                if isinstance(el, note.Unpitched):
                    continue
                if isinstance(el, percussion.PercussionChord):
                    if el.notes and all(isinstance(n, note.Unpitched) for n in el.notes):
                        continue
            try:
                oh = el.getOffsetInHierarchy(p_work)
                ql_offset = float(getattr(oh, "quarterLength", oh) if hasattr(oh, "quarterLength") else oh)
            except Exception:
                ql_offset = float(el.offset)
            dur_ql = float(getattr(el.duration, "quarterLength", 0.0) or 0.0)
            meas = measure_number_at_offset(ql_offset)
            if has_seconds:
                try:
                    t_sec = float(el.getOffsetInHierarchy(sc).seconds)
                except Exception:
                    has_seconds = False
                    t_sec = ql_offset
            else:
                t_sec = ql_offset

            vid = _voice_id(el)
            pitch_list: List[float] | None = None
            if expand_chord_pitches and isinstance(el, chord.Chord):
                pitch_list = sorted({float(p.midi) for p in el.pitches})
            elif expand_chord_pitches and isinstance(el, percussion.PercussionChord):
                pitch_list = sorted(set(_midis_from_percussion_chord(el)))

            if pitch_list is not None:
                if not pitch_list:
                    continue
                n_pc = len(pitch_list)
                for pv in pitch_list:
                    groups[vid].append(
                        Event(
                            t=t_sec,
                            ql=ql_offset,
                            dur_ql=dur_ql,
                            p=float(pv),
                            meas=meas,
                            voice=vid,
                            is_chord_tone=n_pc > 1,
                            is_unpitched=False,
                        )
                    )
                continue

            p_rep = element_pitch_rep(el, rep=chord_rep)
            if p_rep is None or (isinstance(p_rep, float) and math.isnan(p_rep)):
                continue
            is_u = isinstance(el, note.Unpitched) or (
                isinstance(el, percussion.PercussionChord)
                and el.notes
                and all(isinstance(n, note.Unpitched) for n in el.notes)
            )
            ev = Event(
                t=t_sec,
                ql=ql_offset,
                dur_ql=dur_ql,
                p=float(p_rep),
                meas=meas,
                voice=vid,
                is_chord_tone=False,
                is_unpitched=is_u,
            )
            groups[vid].append(ev)

        def _finalize(lst: List[Event]) -> List[Event]:
            lst.sort(key=lambda e: (e.ql, e.p))
            if expand_chord_pitches:
                if chord_simultaneity == "stagger":
                    return _stagger_simultaneous_onsets(lst, has_seconds=has_seconds)
                return lst
            return _collapse_same_ql(lst)

        if not split_voices:
            merged: List[Event] = []
            for vk in sorted(groups.keys()):
                merged.extend(groups[vk])
            acc[part_key][0].extend(merged)
        else:
            n_voices = len([k for k, lst in groups.items() if lst])
            for vid, lst in sorted(groups.items()):
                if not lst:
                    continue
                if n_voices <= 1:
                    acc[part_key][0].extend(lst)
                else:
                    acc[part_key][vid].extend(lst)

    events_by_part: Dict[str, List[Event]] = {}
    for pk, vdict in acc.items():
        if not split_voices:
            merged_all: List[Event] = []
            for lst in vdict.values():
                merged_all.extend(lst)
            events_by_part[pk] = _finalize(merged_all)
        else:
            n_voices = len([k for k, lst in vdict.items() if lst])
            for vid, lst in sorted(vdict.items()):
                if not lst:
                    continue
                collapsed = _finalize(lst)
                if n_voices <= 1:
                    label = pk
                else:
                    label = f"{pk} | v{vid}"
                events_by_part[label] = collapsed

    return events_by_part, has_seconds


def transitions_from_events(evs: List[Event]) -> pd.DataFrame:
    """
    Legacy global consecutive-pair transitions (ql, t, meas, dp, dt_ql, dt_sec, w_dur, w_min).

    Prefer :func:`anisotropia.transitions.build_directional_transition_tables` or
    :func:`anisotropia.pipeline.run_analysis` for the default voice-aware horizontal ontology.
    """
    if len(evs) < 2:
        return pd.DataFrame(columns=["ql", "t", "meas", "dp", "dt_ql", "dt_sec", "w_dur", "w_min"])
    rows = []
    for a, b in zip(evs[:-1], evs[1:]):
        dp = b.p - a.p
        dt_ql = b.ql - a.ql
        dt_sec = b.t - a.t
        w_dur = max(a.dur_ql, 0.0)
        w_min = max(min(a.dur_ql, dt_ql if dt_ql > 0 else a.dur_ql), 0.0)
        rows.append(dict(ql=a.ql, t=a.t, meas=a.meas, dp=dp, dt_ql=dt_ql, dt_sec=dt_sec, w_dur=w_dur, w_min=w_min))
    return pd.DataFrame(rows)
