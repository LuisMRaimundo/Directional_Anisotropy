#!/usr/bin/env python3
"""Generate frozen reference outputs for manifest entries (synthetic fixtures only)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anisotropia import METRIC_SCHEMA_VERSION, __version__
from anisotropia.pipeline import run_analysis

from corpus.benchmark_profile import BENCHMARK_CONFIG

MANIFEST_PATH = ROOT / "corpus" / "manifest.json"
OUT_DIR = ROOT / "corpus" / "reference_outputs"
CHECKSUMS_PATH = OUT_DIR / "checksums.sha256"


def _metrics_row(m) -> dict:
    return {
        "D": float(m.D),
        "tau": float(m.tau),
        "A_tensor": float(m.A_tensor),
        "mu": float(m.mu) if m.mu == m.mu else None,
        "R": float(m.R),
        "n": int(m.n),
    }


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checksum_lines: list[str] = []

    for entry in manifest["entries"]:
        cid = entry["corpus_id"]
        rel = entry["file_path"]
        path = ROOT / rel
        if not path.exists():
            print(f"SKIP missing: {rel}")
            continue
        xml_bytes = path.read_bytes()
        try:
            result = run_analysis(
                xml_bytes,
                path.name,
                BENCHMARK_CONFIG,
                corpus_id=cid,
            )
        except ValueError as exc:
            payload = {
                "corpus_id": cid,
                "file_path": rel,
                "software_version": __version__,
                "metric_schema_version": METRIC_SCHEMA_VERSION,
                "config": BENCHMARK_CONFIG.to_dict(),
                "input_sha256": hashlib.sha256(xml_bytes).hexdigest(),
                "error": str(exc),
                "metrics_2b": None,
                "metrics_2a": None,
                "corpus_status": entry["corpus_status"],
                "include_in_official_benchmark": entry["include_in_official_benchmark"],
            }
            out_path = OUT_DIR / f"{cid}.json"
            text = json.dumps(payload, indent=2, sort_keys=True)
            out_path.write_text(text + "\n", encoding="utf-8")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            checksum_lines.append(f"{digest}  {out_path.relative_to(ROOT).as_posix()}")
            print(f"Wrote {out_path.name} (skipped metrics: {exc})")
            continue
        w0 = result.windows[0]
        payload = {
            "corpus_id": cid,
            "file_path": rel,
            "software_version": __version__,
            "metric_schema_version": METRIC_SCHEMA_VERSION,
            "config": BENCHMARK_CONFIG.to_dict(),
            "input_sha256": hashlib.sha256(xml_bytes).hexdigest(),
            "summary_counts": result.summary_counts,
            "metrics_2b": _metrics_row(w0.metrics_2b) if w0.metrics_2b else None,
            "metrics_2a": _metrics_row(w0.metrics_2a) if w0.metrics_2a else None,
            "corpus_status": entry["corpus_status"],
            "include_in_official_benchmark": entry["include_in_official_benchmark"],
        }
        out_path = OUT_DIR / f"{cid}.json"
        text = json.dumps(payload, indent=2, sort_keys=True)
        out_path.write_text(text + "\n", encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        checksum_lines.append(f"{digest}  {out_path.relative_to(ROOT).as_posix()}")
        print(f"Wrote {out_path.name}")

    CHECKSUMS_PATH.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(f"Wrote checksums: {CHECKSUMS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
