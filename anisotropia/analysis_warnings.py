"""Structured analysis warnings (notational directional-field analyzer)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from anisotropia.metrics import N_MIN_BOOTSTRAP, N_MIN_STABLE
from anisotropia.parsing import Event


@dataclass
class AnalysisWarning:
    warning_type: str
    message: str
    target: Optional[str] = None
    n: Optional[int] = None
    threshold: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _low_n_message(n: int, threshold: int = N_MIN_STABLE) -> str:
    return (
        f"Low transition count: estimates may be unstable. "
        f"n={n}, recommended minimum={threshold}."
    )


def parts_with_unpitched_events(events_by_part: Dict[str, List[Event]]) -> List[str]:
    return sorted(
        p for p, evs in events_by_part.items() if any(getattr(e, "is_unpitched", False) for e in evs)
    )


def collect_unpitched_display_warnings(
    events_by_part: Dict[str, List[Event]],
    unpitched_policy: str,
) -> List[AnalysisWarning]:
    if unpitched_policy != "map_display":
        return []
    parts = parts_with_unpitched_events(events_by_part)
    if not parts:
        return []
    part_list = ", ".join(parts)
    return [
        AnalysisWarning(
            warning_type="unpitched_display_pitch_proxy",
            message=(
                "Unpitched events mapped through display pitch; directional metrics use "
                "notated/display pitch proxy, not acoustic pitch."
                + (f" Affected parts: {part_list}." if part_list else "")
            ),
            target=part_list or None,
        )
    ]


def collect_low_n_warnings(
    df_results: pd.DataFrame,
    ontology_meta: Dict[str, Any],
    summary_counts: Dict[str, Any],
) -> List[AnalysisWarning]:
    warnings: List[AnalysisWarning] = []
    ref_n = int(summary_counts.get("n_reference_part_horizontal", 0))
    if 0 < ref_n < N_MIN_STABLE:
        ref_part = summary_counts.get("reference_part_name")
        warnings.append(
            AnalysisWarning(
                warning_type="low_n_reference_part",
                message=_low_n_message(ref_n),
                target=str(ref_part) if ref_part else "reference_part",
                n=ref_n,
                threshold=N_MIN_STABLE,
            )
        )
    for part, stats in ontology_meta.get("parts", {}).items():
        nh = int(stats.get("n_horizontal_main", 0))
        if 0 < nh < N_MIN_STABLE:
            warnings.append(
                AnalysisWarning(
                    warning_type="low_n_part_horizontal",
                    message=_low_n_message(nh),
                    target=part,
                    n=nh,
                    threshold=N_MIN_STABLE,
                )
            )
    if df_results.empty:
        return warnings
    instr = df_results[df_results["scope"] == "instrumento"]
    for _, row in instr.iterrows():
        n = int(row.get("n", 0))
        if 0 < n < N_MIN_STABLE:
            warnings.append(
                AnalysisWarning(
                    warning_type="low_n_window_instrument",
                    message=_low_n_message(n),
                    target=f"{row.get('part')} @ {row.get('window')}",
                    n=n,
                    threshold=N_MIN_STABLE,
                )
            )
    for win in df_results["window"].drop_duplicates():
        wdf = df_results[df_results["window"] == win]
        for scope_key, part_key in (("total_2A", "TOTAL_2A"), ("total_2B", "TOTAL_2B")):
            rows = wdf[(wdf["scope"] == scope_key) & (wdf["part"] == part_key)]
            if rows.empty:
                continue
            n = int(rows.iloc[0].get("n", 0))
            if 0 < n < N_MIN_STABLE:
                warnings.append(
                    AnalysisWarning(
                        warning_type="low_n_window_aggregate",
                        message=_low_n_message(n),
                        target=f"{part_key} @ {win}",
                        n=n,
                        threshold=N_MIN_STABLE,
                    )
                )
    return warnings


def collect_bootstrap_unavailable_warnings(
    df_results: pd.DataFrame,
    bootstrap_ci: bool,
) -> List[AnalysisWarning]:
    if not bootstrap_ci:
        return []
    warnings: List[AnalysisWarning] = []
    if df_results.empty:
        return warnings
    for _, row in df_results.iterrows():
        n = int(row.get("n", 0))
        if n <= 0:
            continue
        has_a_ci = "A_tensor_ci_lo" in row and pd.notna(row.get("A_tensor_ci_lo"))
        if n < N_MIN_BOOTSTRAP and not has_a_ci:
            warnings.append(
                AnalysisWarning(
                    warning_type="bootstrap_ci_unavailable",
                    message=(
                        f"Bootstrap CI unavailable: n={n} < {N_MIN_BOOTSTRAP} "
                        f"(recommended minimum for CI)."
                    ),
                    target=f"{row.get('part')} @ {row.get('window')}",
                    n=n,
                    threshold=N_MIN_BOOTSTRAP,
                )
            )
    return warnings


def collect_all_analysis_warnings(
    *,
    df_results: pd.DataFrame,
    events_by_part: Dict[str, List[Event]],
    ontology_meta: Dict[str, Any],
    summary_counts: Dict[str, Any],
    unpitched_policy: str,
    bootstrap_ci: bool,
    extra_messages: Optional[List[str]] = None,
) -> List[AnalysisWarning]:
    warnings: List[AnalysisWarning] = []
    warnings.extend(collect_unpitched_display_warnings(events_by_part, unpitched_policy))
    warnings.extend(collect_low_n_warnings(df_results, ontology_meta, summary_counts))
    warnings.extend(collect_bootstrap_unavailable_warnings(df_results, bootstrap_ci))
    if extra_messages:
        for msg in extra_messages:
            warnings.append(AnalysisWarning(warning_type="pipeline", message=msg))
    return _dedupe_warnings(warnings)


def _dedupe_warnings(warnings: List[AnalysisWarning]) -> List[AnalysisWarning]:
    seen: set[tuple] = set()
    out: List[AnalysisWarning] = []
    for w in warnings:
        key = (w.warning_type, w.message, w.target)
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out


def warnings_as_strings(warnings: List[AnalysisWarning]) -> List[str]:
    return [w.message for w in warnings]


def warnings_to_metadata(warnings: List[AnalysisWarning]) -> Dict[str, Any]:
    return {
        "warnings": warnings_as_strings(warnings),
        "warnings_structured": [w.to_dict() for w in warnings],
    }
