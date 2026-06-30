# Directional_Anisotropy

**Canonical tool name:** **Directional_Anisotropy**  
**Systematic notational directional-field analyzer** for symbolic **MusicXML** scores.

Directional_Anisotropy measures **notational directionality** in pitch–time transitions \((\Delta t, \Delta p)\): drift \(D\), tortuosity \(\tau\), tensor anisotropy \(A_{\mathrm{tensor}}\), principal axis \(\mu_{\mathrm{axis}}\), angular coherence \(R\), aggregations 2A/2B, and directional conflict.

**It is not:** audio analysis, a perception model, harmonic or Schenkerian analysis, orchestration density, or general texture analysis. The structure-tensor analogy applies to **discrete notational data**, not waveforms or images.

**Package version:** 2.4.0 (`anisotropia`; canonical tool name **Directional_Anisotropy**)  
**Python:** ≥ 3.10

**Estrutura:** `anisotropia/` (parsing, metrics, transitions, **pipeline**, sensitivity) + `Anisotropia.py` (Streamlit UI).

**CI:** GitHub Actions — tests (**254**), coverage ≥78% (~**93%**), frozen corpus comparison, **ruff** (blocking) — see `.github/workflows/tests.yml`.

> **📘 [MANUAL_TECNICO.md](MANUAL_TECNICO.md)** — Fórmulas e algoritmos  
> **📖 [MANUAL_METRICAS.md](MANUAL_METRICAS.md)** — Resumo das métricas  
> **🧭 [docs/METRIC_SEMANTICS.md](docs/METRIC_SEMANTICS.md)** — Significado interpretativo, limites e uso musicológico das métricas  
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

## One-click install (no Python knowledge required)

Download or clone the project, then use **one file** for your system:

| System | First-time install | Later (already installed) |
|--------|--------------------|---------------------------|
| **Windows 10/11** | Double-click **`installers/windows/INSTALL.bat`** (or **`INSTALL-WINDOWS.bat`** at repo root) | **`START-Directional-Anisotropy.bat`** |
| **macOS** | Double-click **`INSTALL-MAC.command`** | **`START-Directional-Anisotropy.command`** |
| **Linux** | **`bash installers/linux/install-easy.sh`** (or **`INSTALL-LINUX.sh`**) | **`./START-Directional-Anisotropy.sh`** |

The installer will install Python 3.10+ if needed, create `.venv/`, install dependencies, and open the app in your browser. Details: [`installers/README.md`](installers/README.md).

## Streamlit UI (manual / developers)

```bash
pip install -r requirements.txt
streamlit run Anisotropia.py
```

Runtime-only deps: `requirements-app.txt` (used by installers).

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
- Automatic **low-n**, **unpitched display-pitch proxy**, and **parse fallback** warnings (failed `toSoundingPitch` / `expandRepeats`) in reports/exports.
- Bootstrap resamples **transitions**, not hierarchical score units.
- Representative benchmark corpus: **0 official** entries (`include_in_official_benchmark: true`); synthetic fixtures only — primary **90+** blocker.

## Metrics

Symbolic **notational** descriptors only — not audio, spectral, or perceptual measures. See **[docs/METRIC_SEMANTICS.md](docs/METRIC_SEMANTICS.md)** for interpretive meaning, limits, and musicological use.

| Metric | Description |
|--------|-------------|
| **D** | Drift (weighted signed pitch change) |
| **τ** | Tortuosity |
| **$A_{\mathrm{tensor}}$** | Tensor anisotropy in \((\Delta t, \Delta p)\) — not acoustic anisotropy |
| **μ** | Principal orientation (radians) in the model's Δt–Δp plane |
| **R** | Angular coherence (directional concentration, not movement amount) |
| **Directional conflict** | Misalignment of per-part μ (\(1 - R_{\mathrm{inst}}\)) — not harmonic dissonance |

## Legal and citation

| File | Purpose |
|------|---------|
| **[NOTICE.md](NOTICE.md)** | Copyright and use terms (proprietary; no open-source licence granted). |
| **[CITATION.cff](CITATION.cff)** | Citation metadata for software recognition. |

## Installers (optional)

**Repository:** https://github.com/LuisMRaimundo/Directional_Anisotropy

End users without Python: see **[`installers/`](installers/)** — especially on Windows, double-click **`installers/windows/INSTALL.bat`** (installs Python if needed, sets up `.venv`, installs libraries, launches the app).

| Folder | Standard install | Portable build (PyInstaller) |
|--------|------------------|------------------------------|
| [`installers/windows/`](installers/windows/) | **`INSTALL.bat`** | *Not in git* |
| [`installers/mac/`](installers/mac/) | `install-easy.sh` / `install.sh` | *Not in git* |
| [`installers/linux/`](installers/linux/) | `install-easy.sh` / `install.sh` | *Not in git* |

Built `.exe` / `.app` / `.dmg` / `.tar.gz` files are **not** in git — use [GitHub Releases](https://github.com/LuisMRaimundo/Directional_Anisotropy/releases) if you distribute frozen builds.

## Acknowledgements

This project was developed by **Luís Raimundo** with the support and funding of the **Fundação para a Ciência e a Tecnologia (FCT)** and **Universidade NOVA de Lisboa**.

**Funding DOI:** [https://doi.org/10.54499/2020.08817.BD](https://doi.org/10.54499/2020.08817.BD)

The author also gratefully acknowledges **Isabel Pires** for her support throughout the development of this work.
