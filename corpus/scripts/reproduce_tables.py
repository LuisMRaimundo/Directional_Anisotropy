#!/usr/bin/env python3
"""Reproduce corpus summary tables from manifest + pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anisotropia.pipeline import run_analysis

from corpus.benchmark_profile import BENCHMARK_CONFIG

MANIFEST_PATH = ROOT / "corpus" / "manifest.json"

TABLES_DIR = ROOT / "corpus" / "tables"


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = []
    for entry in manifest["entries"]:
        path = ROOT / entry["file_path"]
        if not path.exists():
            continue
        try:
            result = run_analysis(
                path.read_bytes(),
                path.name,
                BENCHMARK_CONFIG,
                corpus_id=entry["corpus_id"],
            )
        except ValueError:
            continue
        m = result.windows[0].metrics_2b
        if m is None:
            continue
        rows.append(
            {
                "corpus_id": entry["corpus_id"],
                "corpus_status": entry["corpus_status"],
                "include_in_official_benchmark": entry["include_in_official_benchmark"],
                "n_transitions_2b": m.n,
                "D": m.D,
                "tau": m.tau,
                "A_tensor": m.A_tensor,
                "R": m.R,
            }
        )
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    csv_path = TABLES_DIR / "benchmark_summary.csv"
    df.to_csv(csv_path, index=False)
    print(f"Wrote {csv_path} ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
