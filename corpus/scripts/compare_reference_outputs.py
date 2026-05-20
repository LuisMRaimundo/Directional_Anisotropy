#!/usr/bin/env python3
"""Compare live pipeline output to frozen reference_outputs/*.json."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anisotropia.pipeline import run_analysis

from corpus.benchmark_profile import BENCHMARK_CONFIG

MANIFEST_PATH = ROOT / "corpus" / "manifest.json"
OUT_DIR = ROOT / "corpus" / "reference_outputs"

TOL = 1e-9


def _close(a: float, b: float) -> bool:
    if a is None or b is None:
        return a is b
    if not (math.isfinite(a) and math.isfinite(b)):
        return (not math.isfinite(a)) and (not math.isfinite(b))
    return abs(a - b) <= TOL


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    failures = 0
    for entry in manifest["entries"]:
        cid = entry["corpus_id"]
        ref_path = OUT_DIR / f"{cid}.json"
        if not ref_path.exists():
            print(f"MISSING reference: {ref_path.name}")
            failures += 1
            continue
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        if ref.get("metrics_2b") is None:
            print(f"SKIP {cid}: reference has no metrics (documented skip)")
            continue
        xml_path = ROOT / entry["file_path"]
        result = run_analysis(xml_path.read_bytes(), xml_path.name, BENCHMARK_CONFIG, corpus_id=cid)
        live = result.windows[0].metrics_2b
        if live is None:
            print(f"FAIL {cid}: no 2B metrics")
            failures += 1
            continue
        expected = ref["metrics_2b"]
        for key in ("D", "tau", "A_tensor", "R", "n"):
            if not _close(float(getattr(live, key)), float(expected[key])):
                print(f"FAIL {cid}.{key}: live={getattr(live, key)} ref={expected[key]}")
                failures += 1
    if failures:
        print(f"{failures} comparison failure(s)")
        return 1
    print("All reference comparisons passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
