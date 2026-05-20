"""Shared benchmark analysis profile for frozen outputs and comparison scripts."""

from anisotropia.config import AnalysisConfig

BENCHMARK_CONFIG = AnalysisConfig(
    window_mode="total",
    bootstrap_ci=False,
    compute_2a=True,
    compute_2b=True,
    standardization_mode="local_zscore",
    legacy_mixed_mode=False,
)
