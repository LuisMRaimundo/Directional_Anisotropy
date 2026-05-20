"""
Parameter sensitivity analysis for notational directional-field metrics.

Sensitivity analysis is robustness analysis, not validation against a gold standard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np

from anisotropia.config import AnalysisConfig
from anisotropia.pipeline import run_analysis

ALLOWED_GRID_KEYS = frozenset({
    "chord_rep",
    "standardization_mode",
    "weight_mode",
    "window_mode",
    "window_size",
    "step",
    "epsilon_dt",
})


@dataclass
class SensitivityVariant:
    parameter: str
    value: Any
    A_tensor_2b: float
    D_2b: float
    R_2b: float
    tau_2b: float
    n_2b: int
    delta_A_tensor: float
    delta_D: float
    delta_R: float
    warnings: List[str] = field(default_factory=list)


@dataclass
class SensitivityReport:
    baseline: Dict[str, Any]
    variants: List[SensitivityVariant]
    disclaimer: str = (
        "Sensitivity analysis is robustness analysis, not validation. "
        "It does not establish correctness against an external corpus."
    )
    warnings: List[str] = field(default_factory=list)


def _summary_from_result(result) -> Dict[str, Any]:
    df = result.df_results
    row = df[(df["scope"] == "total_2B") & (df["part"] == "TOTAL_2B")]
    if row.empty:
        row = df[df["scope"] == "instrumento"]
        if row.empty:
            return {"A_tensor": np.nan, "D": np.nan, "R": np.nan, "tau": np.nan, "n": 0}
        r0 = row.iloc[0]
    else:
        r0 = row.iloc[0]
    return {
        "A_tensor": float(r0.get("A_tensor", np.nan)),
        "D": float(r0.get("D", np.nan)),
        "R": float(r0.get("R", np.nan)),
        "tau": float(r0.get("tau", np.nan)),
        "n": int(r0.get("n", 0)),
    }


def run_parameter_sensitivity(
    xml_bytes: bytes,
    filename: str,
    base_config: AnalysisConfig,
    parameter_grid: Dict[str, List[Any]],
) -> SensitivityReport:
    """
    Run baseline analysis and one variant per (parameter, value) in ``parameter_grid``.

    Unsupported keys raise ValueError. Does not modify default analysis behaviour elsewhere.
    """
    bad = set(parameter_grid) - ALLOWED_GRID_KEYS
    if bad:
        raise ValueError(f"Unsupported sensitivity parameters: {sorted(bad)}")

    baseline_result = run_analysis(xml_bytes, filename, base_config)
    baseline = _summary_from_result(baseline_result)
    variants: List[SensitivityVariant] = []
    report_warnings: List[str] = list(baseline_result.warnings)

    for param, values in parameter_grid.items():
        for val in values:
            cfg_dict = base_config.to_dict()
            cfg_dict[param] = val
            variant_cfg = AnalysisConfig(**{k: v for k, v in cfg_dict.items() if k in AnalysisConfig.__dataclass_fields__})
            try:
                res = run_analysis(xml_bytes, filename, variant_cfg)
            except ValueError as exc:
                variants.append(
                    SensitivityVariant(
                        parameter=param,
                        value=val,
                        A_tensor_2b=np.nan,
                        D_2b=np.nan,
                        R_2b=np.nan,
                        tau_2b=np.nan,
                        n_2b=0,
                        delta_A_tensor=np.nan,
                        delta_D=np.nan,
                        delta_R=np.nan,
                        warnings=[str(exc)],
                    )
                )
                continue
            s = _summary_from_result(res)
            variants.append(
                SensitivityVariant(
                    parameter=param,
                    value=val,
                    A_tensor_2b=s["A_tensor"],
                    D_2b=s["D"],
                    R_2b=s["R"],
                    tau_2b=s["tau"],
                    n_2b=s["n"],
                    delta_A_tensor=s["A_tensor"] - baseline["A_tensor"]
                    if np.isfinite(s["A_tensor"]) and np.isfinite(baseline["A_tensor"])
                    else np.nan,
                    delta_D=s["D"] - baseline["D"]
                    if np.isfinite(s["D"]) and np.isfinite(baseline["D"])
                    else np.nan,
                    delta_R=s["R"] - baseline["R"]
                    if np.isfinite(s["R"]) and np.isfinite(baseline["R"])
                    else np.nan,
                    warnings=list(res.warnings),
                )
            )

    return SensitivityReport(baseline=baseline, variants=variants, warnings=report_warnings)
