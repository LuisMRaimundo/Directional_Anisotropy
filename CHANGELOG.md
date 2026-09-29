# Changelog

## 2.5.0

**Breaking for results** when an analysis uses the default standardisation.

- New mode `rms_scale`: each component (\(\Delta t\), \(\Delta p\)) is divided by its weighted root mean square. The weighted mean is not subtracted, so the structure tensor stays uncentred. This is now the default of `AnalysisConfig.standardization_mode` and of the Streamlit selector.
- `local_zscore`, `robust_scale`, `none`, and `global_zscore` are unchanged and remain selectable. `standardize=True` still means `local_zscore`; `standardize=False` still means `none`.
- Earlier analyses (versions ≤ 2.4.0) are only reproducible with `standardization_mode="local_zscore"`.
- `metric_schema_version` is **1.1.0**. `config_sha256` already includes `standardization_mode`, so a default configuration hashes differently from a 2.4.0 default. Frozen regression fixtures and `BENCHMARK_CONFIG` stay pinned to `local_zscore`. `THESIS_PROFILE` uses `rms_scale`.

### fix: axial mean of μ

The 2A mean of μ and directional conflict now use axial statistics (angle doubling; Mardia & Jupp, 2000). C and S are formed on \(2\mu\); the mean axis is \(\tfrac{1}{2}\operatorname{atan2}(S, C)\), and conflict is \(1 - \sqrt{C^2 + S^2}\). μ and μ+π are the same axis, so opposite eigenvector signs no longer cancel or produce spurious conflict. Perpendicular axes (difference π/2), equally weighted, give conflict 1.
