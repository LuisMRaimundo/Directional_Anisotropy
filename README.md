# Anisotropia Direcional

**Systematic notational directional-field analyzer** for symbolic **MusicXML** scores.

Anisotropia Direcional measures **notational directionality** in pitch–time transitions \((\Delta t, \Delta p)\): drift \(D\), tortuosity \(\tau\), tensor anisotropy \(A_{\mathrm{tensor}}\), principal axis \(\mu_{\mathrm{axis}}\), angular coherence \(R\), aggregations 2A/2B, and directional conflict.

**It is not:** audio analysis, a perception model, harmonic or Schenkerian analysis, orchestration density, or general texture analysis. The structure-tensor analogy applies to **discrete notational data**, not waveforms or images.

**Package version:** 2.4.0 (`anisotropia/__init__.py`)  
**Python:** ≥ 3.10

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

## One-click install (no Python knowledge required)

Download or clone the project, then use **one file** for your system:

| System | First-time install | Later (already installed) |
|--------|--------------------|---------------------------|
| **Windows 10/11** | Double-click **`instalers/windows/INSTALL.bat`** (or **`INSTALL-WINDOWS.bat`** at repo root) | **`START-Anisotropia.bat`** |
| **macOS** | Double-click **`INSTALL-MAC.command`** | **`START-Anisotropia.command`** |
| **Linux** | **`bash instalers/linux/install-easy.sh`** (or **`INSTALL-LINUX.sh`**) | **`./START-Anisotropia.sh`** |

The installer will install Python 3.10+ if needed, create `.venv/`, install dependencies, and open the app in your browser. Details: [`instalers/README.md`](instalers/README.md).

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

## Legal and citation

| File | Purpose |
|------|---------|
| **[NOTICE.md](NOTICE.md)** | Copyright and use terms (proprietary; no open-source licence granted). |
| **[CITATION.cff](CITATION.cff)** | Citation metadata for software recognition. |

## Installers (optional)

**Repository:** https://github.com/LuisMRaimundo/Music_xml_anisotropy

End users without Python: see **[`instalers/`](instalers/)** — especially on Windows, double-click **`instalers/windows/INSTALL.bat`** (installs Python if needed, sets up `.venv`, installs libraries, launches the app).

| Folder | Standard install | Portable build (PyInstaller) |
|--------|------------------|------------------------------|
| [`instalers/windows/`](instalers/windows/) | **`INSTALL.bat`** | *Not in git* |
| [`instalers/mac/`](instalers/mac/) | `install-easy.sh` / `install.sh` | *Not in git* |
| [`instalers/linux/`](instalers/linux/) | `install-easy.sh` / `install.sh` | *Not in git* |

Built `.exe` / `.app` / `.dmg` / `.tar.gz` files are **not** in git — use [GitHub Releases](https://github.com/LuisMRaimundo/Music_xml_anisotropy/releases) if you distribute frozen builds.

## Acknowledgements

This project was developed by **Luís Raimundo** with the support and funding of the **Fundação para a Ciência e a Tecnologia (FCT)** and **Universidade NOVA de Lisboa**.

**Funding DOI:** [https://doi.org/10.54499/2020.08817.BD](https://doi.org/10.54499/2020.08817.BD)

The author also gratefully acknowledges **Isabel Pires** for her support throughout the development of this work.
