# Anisotropia Direcional

**Systematic notational directional-field analyzer** for symbolic **MusicXML** scores.

Anisotropia Direcional measures **notational directionality** in pitch–time transitions \((\Delta t, \Delta p)\): drift \(D\), tortuosity \(\tau\), tensor anisotropy \(A_{\mathrm{tensor}}\), principal axis \(\mu_{\mathrm{axis}}\), angular coherence \(R\), aggregations 2A/2B, and directional conflict.

**It is not:** audio analysis, a perception model, harmonic or Schenkerian analysis, orchestration density, or general texture analysis. The structure-tensor analogy applies to **discrete notational data**, not waveforms or images.

**Estrutura:** `anisotropia/` (parsing, metrics, transitions, **pipeline**, sensitivity) + `Anisotropia.py` (Streamlit UI).

**CI:** GitHub Actions — tests (138), coverage ≥78% (~85%), frozen corpus comparison, **ruff** (blocking) — see `.github/workflows/tests.yml`.

> **📘 [MANUAL_TECNICO.md](MANUAL_TECNICO.md)** — Fórmulas e algoritmos  
> **📖 [MANUAL_METRICAS.md](MANUAL_METRICAS.md)** — Resumo das métricas  
> **📋 [CORPUS_REFERENCIA.md](CORPUS_REFERENCIA.md)** — Fixtures e benchmark  
> **📊 [docs/anisotropia_90_rubric.md](docs/anisotropia_90_rubric.md)** — Rubrica 90+ (notacional)  
> **📈 [docs/anisotropia_current_rating.md](docs/anisotropia_current_rating.md)** — Pontuação actual (88/100)

## Programmatic usage (no Streamlit)

```python
from anisotropia import AnalysisConfig, run_analysis

xml_bytes = open("score.musicxml", "rb").read()
result = run_analysis(xml_bytes, "score.musicxml", AnalysisConfig(window_mode="total"))
print(result.df_results)
```

See `docs/STREAMLIT_PIPELINE_MIGRATION.md` for UI integration status.

## Streamlit UI

```bash
pip install -r requirements.txt
streamlit run Anisotropia.py
```

## Tests and corpus scripts

```bash
pytest tests/ -q
pytest tests/ --cov=anisotropia --cov-report=term-missing
ruff check anisotropia tests corpus/benchmark_profile.py
python corpus/scripts/generate_reference_outputs.py
python corpus/scripts/compare_reference_outputs.py
python corpus/scripts/reproduce_tables.py
```

**Maintenance:** `docs/cleanup_inventory.md` · `docs/cleanup_report.md` · `archive/` (obsolete exports only).

## Limitations (summary)

- Pitch spelling / enharmonic semantics are limited (MIDI semitones).
- Chord representative collapses simultaneities for horizontal directionality.
- \(D\) is signed pitch drift, not tonal function.
- `global_zscore` is currently an **alias** of `local_zscore` (not corpus-global).
- `grace_policy=include_attached` is **not implemented** (not in UI; programmatic use raises `NotImplementedError`).
- **`config_sha256`** is computed for every analysis (deterministic effective-config hash).
- Automatic **low-n** and **unpitched display-pitch proxy** warnings in reports/exports.
- Bootstrap resamples **transitions**, not hierarchical score units.
- Representative benchmark corpus: **0 official** entries (`include_in_official_benchmark: true`); synthetic fixtures only — primary **90+** blocker.

## Metrics

| Metric | Description |
|--------|-------------|
| **D** | Drift (weighted signed pitch change) |
| **τ** | Tortuosity |
| **$A_{\mathrm{tensor}}$** | Tensor anisotropy in \((\Delta t, \Delta p)\) |
| **μ** | Principal orientation (radians) |
| **R** | Angular coherence |

## License

Use freely for research and education.
