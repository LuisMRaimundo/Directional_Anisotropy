# Streamlit ↔ programmatic pipeline

**Status (release 2.4.0):** The Streamlit app routes **main metric calculation** through `run_analysis()`.

```python
from anisotropia import run_analysis
from anisotropia.config import analysis_config_from_ui

cfg = analysis_config_from_ui(...)  # sidebar parameters
result = run_analysis(xml_bytes, filename, cfg)
df_out = result.df_results
```

## Completed

- Core orchestration delegated to `anisotropia/pipeline.py`
- `AnalysisConfig` built via `analysis_config_from_ui()`
- Reproducibility metadata (`config_sha256`, warnings) from pipeline result
- Visualizations and interpretation remain in `Anisotropia.py` (UI layer)

## Remaining (optional)

- Cache `run_analysis` with `st.cache_data` keyed on input hash + config hash
- Further slim `Anisotropia.py` by moving interpretation helpers to `anisotropia/report.py` or a UI module

Metric formulas are unchanged. Numeric outputs match the voice-aware horizontal pipeline for the same `AnalysisConfig`.

**Rating:** 88/100 (not 90+). Official representative benchmark count: **0**. See `docs/anisotropia_current_rating.md`.
