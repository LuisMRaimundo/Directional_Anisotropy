#!/usr/bin/env python3
"""
Inspect Phase 1 anisotropy regression fixtures (exploratory, non-golden).

Run from repository root:
    python corpus/scripts/create_anisotropy_regression_fixtures.py
    python corpus/scripts/inspect_anisotropy_regression.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from anisotropia.config import AnalysisConfig
from anisotropia.pipeline import run_analysis

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "corpus" / "fixtures" / "anisotropy_regression"
REPORT_DIR = REPO_ROOT / "corpus" / "reports"

DEFAULT_CONFIG = AnalysisConfig(
    window_mode="total",
    bootstrap_ci=False,
    standardization_mode="local_zscore",
    legacy_mixed_mode=False,
)

WINDOW_CONFIG = AnalysisConfig(
    window_mode="measures",
    window_size=2,
    step=2,
    bootstrap_ci=False,
    standardization_mode="local_zscore",
    legacy_mixed_mode=False,
)


def _flow(m) -> tuple[float, float]:
    if m is None or not np.isfinite(m.A_tensor) or not np.isfinite(m.mu):
        return float("nan"), float("nan")
    return float(m.A_tensor * math.cos(m.mu)), float(m.A_tensor * math.sin(m.mu))


def _metrics_dict(m, conflict: float = float("nan")) -> Dict[str, Any]:
    fu, fv = _flow(m)
    return {
        "n_transitions": int(m.n) if m else 0,
        "D": float(m.D) if m else float("nan"),
        "tau": float(m.tau) if m else float("nan"),
        "A_tensor": float(m.A_tensor) if m else float("nan"),
        "R": float(m.R) if m else float("nan"),
        "mu": float(m.mu) if m else float("nan"),
        "flow_U": fu,
        "flow_V": fv,
        "directional_conflict": float(conflict) if np.isfinite(conflict) else None,
    }


def inspect_fixture(path: Path, config: AnalysisConfig) -> Dict[str, Any]:
    result = run_analysis(path.read_bytes(), path.name, config)
    n_events = sum(len(v) for v in result.events_by_part.values())
    n_trans = sum(len(df) for df in result.trans_by_part.values())
    win = result.windows[0] if result.windows else None
    m2b = win.metrics_2b if win else None
    conflict = win.directional_conflict if win else float("nan")
    note = "total window, 2B aggregate"
    if config.window_mode != "total" and result.windows:
        windows_out = []
        for w in result.windows:
            m = w.metrics_2b
            fu, fv = _flow(m)
            windows_out.append(
                {
                    "window": w.window_label,
                    **_metrics_dict(m, w.directional_conflict),
                }
            )
        return {
            "fixture": path.stem,
            "config": config.window_mode,
            "n_events": n_events,
            "n_transitions_total": n_trans,
            "windows": windows_out,
            "interpretation": "Windowed inspection for directional change.",
        }
    return {
        "fixture": path.stem,
        "config": config.window_mode,
        "n_events": n_events,
        "n_transitions_total": n_trans,
        "metrics_2b": _metrics_dict(m2b, conflict),
        "interpretation": note,
    }


def _interpretation_blurb(entry: Dict[str, Any]) -> str:
    name = entry["fixture"]
    m = entry.get("metrics_2b") or (entry.get("windows") or [{}])[0]
    if "windows" in entry:
        return f"{name}: windowed profile — compare D sign across measure windows (not flow_V; μ≈π/2)."
    a = m.get("A_tensor", float("nan"))
    r = m.get("R", float("nan"))
    d = m.get("D", float("nan"))
    if name == "static_repetition":
        return "Repeated pitch: Δp=0 transitions; temporal symbolic motion, not registral drift."
    if name == "uniform_ascending_steps":
        return f"Monotone ascent: D≈{d:.3f}, high concentration (A≈{a:.3f}, R≈{r:.3f}); flow_V>0 does not imply ascent alone."
    if name == "uniform_descending_steps":
        return f"Monotone descent: D≈{d:.3f}; flow_V may still be positive when μ≈π/2 — use D for registral direction."
    if name == "dense_events_no_direction":
        return f"Many alternating events; concentration may stay moderate (R≈{r:.3f}) despite high n."
    return f"Exploratory snapshot D={d:.3f}, A={a:.3f}, R={r:.3f}."


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = sorted(FIXTURE_DIR.glob("*.xml"))
    if not fixtures:
        raise SystemExit(f"No fixtures in {FIXTURE_DIR}. Run create_anisotropy_regression_fixtures.py first.")

    records: List[Dict[str, Any]] = []
    for path in fixtures:
        cfg = WINDOW_CONFIG if path.stem == "directional_change_by_window" else DEFAULT_CONFIG
        entry = inspect_fixture(path, cfg)
        entry["interpretation"] = _interpretation_blurb(entry)
        records.append(entry)

    json_path = REPORT_DIR / "anisotropy_regression_inspection.json"
    def _json_default(obj: Any) -> Any:
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        raise TypeError(f"Not JSON serializable: {type(obj)!r}")

    json_path.write_text(
        json.dumps(records, indent=2, default=_json_default),
        encoding="utf-8",
    )

    lines = [
        "# Anisotropy regression fixture inspection (exploratory)",
        "",
        "Non-golden exploratory report. Values are **not** strict regression references.",
        "",
        f"Fixtures: `{FIXTURE_DIR.relative_to(REPO_ROOT)}`",
        "",
    ]
    for entry in records:
        lines.append(f"## {entry['fixture']}")
        lines.append("")
        lines.append(f"- Events: {entry['n_events']}")
        lines.append(f"- Transitions (horizontal, all parts): {entry['n_transitions_total']}")
        lines.append(f"- Config window_mode: `{entry['config']}`")
        if "windows" in entry:
            for w in entry["windows"]:
                lines.append(
                    f"- Window `{w['window']}`: A={w['A_tensor']:.4f}, R={w['R']:.4f}, "
                    f"μ={w['mu']:.4f}, flow_V={w['flow_V']:.4f}"
                )
        else:
            m = entry["metrics_2b"]
            lines.append(
                f"- 2B: A={m['A_tensor']:.4f}, R={m['R']:.4f}, μ={m['mu']:.4f}, "
                f"D={m['D']:.4f}, τ={m['tau']:.4f}, flow_U={m['flow_U']:.4f}, flow_V={m['flow_V']:.4f}"
            )
            if m.get("directional_conflict") is not None:
                lines.append(f"- Directional conflict: {m['directional_conflict']:.4f}")
        lines.append(f"- Note: {entry['interpretation']}")
        lines.append("")

    md_path = REPORT_DIR / "anisotropy_regression_inspection.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
