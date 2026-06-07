#!/usr/bin/env python3
"""
Generate deterministic MusicXML fixtures for Phase 1 anisotropy regression.

Run from repository root:
    python corpus/scripts/create_anisotropy_regression_fixtures.py
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "corpus" / "fixtures" / "anisotropy_regression"

Pitch = Tuple[str, int, int]  # (step, octave, alter)

PITCHES: Dict[str, Pitch] = {
    "C3": ("C", 3, 0),
    "D3": ("D", 3, 0),
    "C#4": ("C", 4, 1),
    "D#4": ("D", 4, 1),
    "F#4": ("F", 4, 1),
    "G#4": ("G", 4, 1),
    "C4": ("C", 4, 0),
    "D4": ("D", 4, 0),
    "E4": ("E", 4, 0),
    "F4": ("F", 4, 0),
    "G4": ("G", 4, 0),
    "A4": ("A", 4, 0),
    "B4": ("B", 4, 0),
    "C5": ("C", 5, 0),
    "D5": ("D", 5, 0),
    "E5": ("E", 5, 0),
    "F5": ("F", 5, 0),
    "G5": ("G", 5, 0),
}


def _note_element(pitch_name: str, duration: int = 1, note_type: str = "quarter") -> ET.Element:
    step, octave, alter = PITCHES[pitch_name]
    note = ET.Element("note")
    pitch = ET.SubElement(note, "pitch")
    ET.SubElement(pitch, "step").text = step
    if alter:
        ET.SubElement(pitch, "alter").text = str(alter)
    ET.SubElement(pitch, "octave").text = str(octave)
    ET.SubElement(note, "duration").text = str(duration)
    ET.SubElement(note, "type").text = note_type
    return note


def _attributes(divisions: int = 1) -> ET.Element:
    attrs = ET.Element("attributes")
    ET.SubElement(attrs, "divisions").text = str(divisions)
    key = ET.SubElement(attrs, "key")
    ET.SubElement(key, "fifths").text = "0"
    time_sig = ET.SubElement(attrs, "time")
    ET.SubElement(time_sig, "beats").text = "4"
    ET.SubElement(time_sig, "beat-type").text = "4"
    clef = ET.SubElement(attrs, "clef")
    ET.SubElement(clef, "sign").text = "G"
    ET.SubElement(clef, "line").text = "2"
    return attrs


def _score_partwise(
    parts: Sequence[Tuple[str, str, Sequence[Tuple[str, int]]]],
    *,
    filename: str,
) -> None:
    """
    Write a score-partwise MusicXML file.

    ``parts``: sequence of (part_id, part_name, note_specs) where each note spec
    is (pitch_name, duration).
    """
    root = ET.Element("score-partwise", version="4.0")
    part_list = ET.SubElement(root, "part-list")
    for part_id, part_name, _ in parts:
        score_part = ET.SubElement(part_list, "score-part", id=part_id)
        ET.SubElement(score_part, "part-name").text = part_name

    for part_id, _, notes in parts:
        part_el = ET.SubElement(root, "part", id=part_id)
        measure = ET.SubElement(part_el, "measure", number="1")
        measure.append(_attributes())
        for pitch_name, dur in notes:
            ntype = "quarter" if dur == 1 else "half" if dur == 2 else "quarter"
            measure.append(_note_element(pitch_name, duration=dur, note_type=ntype))

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    out_path = OUT_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="UTF-8", xml_declaration=True)


def _score_multimeasure_single_part(
    measures_notes: Sequence[Sequence[Tuple[str, int]]],
    *,
    filename: str,
    part_name: str = "Melody",
) -> None:
    root = ET.Element("score-partwise", version="4.0")
    part_list = ET.SubElement(root, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = part_name
    part_el = ET.SubElement(root, "part", id="P1")
    for mnum, notes in enumerate(measures_notes, start=1):
        measure = ET.SubElement(part_el, "measure", number=str(mnum))
        if mnum == 1:
            measure.append(_attributes())
        for pitch_name, dur in notes:
            ntype = "quarter" if dur == 1 else "half" if dur == 2 else "quarter"
            measure.append(_note_element(pitch_name, duration=dur, note_type=ntype))
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    out_path = OUT_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="UTF-8", xml_declaration=True)


def build_all_fixtures() -> List[str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created: List[str] = []

    ascending = ["C4", "D4", "E4", "F4", "G4"]
    descending = ["G4", "F4", "E4", "D4", "C4"]
    alternating = ["C4", "D4", "C4", "D4", "C4", "D4"]
    balanced = [
        "C4", "E4", "C4", "C4", "G4", "D4", "D4", "A4", "E4",
    ]
    dense_alt = alternating * 4  # 24 notes
    sparse = ["C4", "G4", "C5"]

    specs = [
        ("static_repetition.xml", [("P1", "Static", [("C4", 1)] * 4)]),
        ("uniform_ascending_steps.xml", [("P1", "Ascend", [(p, 1) for p in ascending])]),
        ("uniform_descending_steps.xml", [("P1", "Descend", [(p, 1) for p in descending])]),
        ("alternating_up_down_same_axis.xml", [("P1", "Alternate", [(p, 1) for p in alternating])]),
        ("balanced_four_directions.xml", [("P1", "Balanced", [(p, 1) for p in balanced])]),
        (
            "parallel_ascending_parts.xml",
            [
                ("P1", "PartA", [(p, 1) for p in ascending]),
                ("P2", "PartB", [(p, 1) for p in ascending]),
            ],
        ),
        (
            "contrary_motion_symmetric.xml",
            [
                ("P1", "Ascend", [(p, 1) for p in ascending]),
                ("P2", "Descend", [(p, 1) for p in descending]),
            ],
        ),
        (
            "oblique_motion.xml",
            [
                ("P1", "Static", [("C4", 1)] * 5),
                ("P2", "Ascend", [(p, 1) for p in ascending]),
            ],
        ),
        (
            "time_stretched_same_contour.xml",
            [("P1", "Stretched", [(p, 2) for p in ascending])],
        ),
        ("dense_events_no_direction.xml", [("P1", "Dense", [(p, 1) for p in dense_alt])]),
        ("sparse_strong_direction.xml", [("P1", "Sparse", [(p, 1) for p in sparse])]),
    ]

    for filename, parts in specs:
        _score_partwise(parts, filename=filename)
        created.append(filename)

    # Transposed: explicit octave-up spelling
    transposed = ["C5", "D5", "E5", "F5", "G5"]
    _score_partwise([("P1", "Transposed", [(p, 1) for p in transposed])], filename="transposed_same_contour.xml")
    created.append("transposed_same_contour.xml")

    # Pitch inversion around E4 (MIDI mirror): C4-D4-E4-F4-G4 -> G#4-F#4-E4-D#4-C#4
    inverted = ["G#4", "F#4", "E4", "D#4", "C#4"]
    _score_partwise(
        [("P1", "Inverted", [(p, 1) for p in inverted])],
        filename="pitch_inversion_same_rhythm.xml",
    )
    created.append("pitch_inversion_same_rhythm.xml")

    # Directional change: measures 1-2 ascend, 3-4 descend
    _score_multimeasure_single_part(
        [
            [("C4", 1), ("D4", 1), ("E4", 1), ("F4", 1)],
            [("G4", 1), ("A4", 1), ("B4", 1), ("C5", 1)],
            [("C5", 1), ("B4", 1), ("A4", 1), ("G4", 1)],
            [("F4", 1), ("E4", 1), ("D4", 1), ("C4", 1)],
        ],
        filename="directional_change_by_window.xml",
        part_name="ContourChange",
    )
    created.append("directional_change_by_window.xml")

    return sorted(set(created))


if __name__ == "__main__":
    names = build_all_fixtures()
    print(f"Created {len(names)} fixtures in {OUT_DIR}")
    for name in names:
        print(f"  - {name}")
