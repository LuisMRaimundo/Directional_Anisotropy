"""Result models for programmatic analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from anisotropia.analysis_warnings import AnalysisWarning
from anisotropia.config import AnalysisConfig
from anisotropia.metrics import Metrics
from anisotropia.parsing import Event


@dataclass
class WindowResult:
    window_label: str
    metrics_by_part: Dict[str, Metrics]
    metrics_2a: Optional[Metrics]
    metrics_2b: Optional[Metrics]
    directional_conflict: float
    trans_by_part_windowed: Dict[str, pd.DataFrame]


@dataclass
class AnalysisResult:
    """Full output of :func:`anisotropia.pipeline.run_analysis`."""

    df_results: pd.DataFrame
    events_by_part: Dict[str, List[Event]]
    trans_by_part: Dict[str, pd.DataFrame]
    trans_vertical_by_part: Dict[str, pd.DataFrame]
    windows: List[WindowResult]
    has_seconds: bool
    ref_part: Optional[str]
    config: AnalysisConfig
    warnings: List[str] = field(default_factory=list)
    structured_warnings: List[AnalysisWarning] = field(default_factory=list)
    trans_by_window: Dict[str, pd.DataFrame] = field(default_factory=dict)
    time_axis: str = "ql"
    ontology_meta: Dict[str, Any] = field(default_factory=dict)
    summary_counts: Dict[str, Any] = field(default_factory=dict)
    reproducibility: Dict[str, Any] = field(default_factory=dict)
    report_params: Dict[str, Any] = field(default_factory=dict)
