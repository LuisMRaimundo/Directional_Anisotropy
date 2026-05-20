"""Corpus manifest and frozen output integrity."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.json"
REF_DIR = ROOT / "corpus" / "reference_outputs"
TABLES = ROOT / "corpus" / "tables" / "benchmark_summary.csv"

REQUIRED = (
    "corpus_id",
    "file_path",
    "format",
    "corpus_status",
    "composer",
    "work_title",
    "excerpt_label",
    "instrumentation",
    "measure_range",
    "source",
    "license_status",
    "license_note",
    "limitations",
    "include_in_official_benchmark",
)


def test_manifest_loads():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "entries" in data
    assert len(data["entries"]) >= 1


@pytest.mark.parametrize("entry", json.loads(MANIFEST.read_text(encoding="utf-8"))["entries"])
def test_manifest_entry_fields(entry):
    for key in REQUIRED:
        assert key in entry, f"missing {key} in {entry.get('corpus_id')}"


def test_synthetic_fixtures_labelled():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for e in data["entries"]:
        if e["corpus_status"] == "synthetic_fixture":
            assert e["include_in_official_benchmark"] is False


def test_no_unknown_license_in_official_benchmark():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for e in data["entries"]:
        if e["include_in_official_benchmark"]:
            assert e["corpus_status"] != "unknown_license_excluded"


def test_frozen_outputs_no_spurious_nan():
    for path in REF_DIR.glob("*.json"):
        ref = json.loads(path.read_text(encoding="utf-8"))
        for block in (ref.get("metrics_2b"), ref.get("metrics_2a")):
            if block is None:
                continue
            for k, v in block.items():
                if v is None:
                    continue
                if isinstance(v, float) and not math.isfinite(v):
                    pytest.fail(f"{path.name} {k} non-finite")


def test_benchmark_table_exists_after_reproduce():
    if not TABLES.exists():
        pytest.skip("run corpus/scripts/reproduce_tables.py first")
    df = pd.read_csv(TABLES)
    assert len(df) >= 1
    assert "corpus_status" in df.columns
