# Anisotropia 90+ Rubric — Notational Directional-Field Analyzer

**Scope:** This rubric evaluates **Anisotropia Direcional** only as a **systematic notational directional-field analyzer** on symbolic MusicXML pitch–time transitions. It does **not** require audio, listening tests, tonal function, harmony, Schenkerian analysis, orchestration density, or general texture analysis. Interpretive semantics and limits: [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md).

**Total:** 100 points

---

## 1. Scientific scope and terminology discipline (10)

The tool clearly states that it measures **notational directionality**, not audio, perception, harmony, or general texture. Documentation and UI avoid scope creep.

## 2. Formal metric correctness and documentation (15)

Implemented formulas match `MANUAL_TECNICO.md` and tests for:

- \(D\), \(\tau\), \(A_{\mathrm{tensor}}\), \(\mu_{\mathrm{axis}}\), \(R\)
- 2A, 2B, directional conflict
- bootstrap CI (transition-level)

## 3. Transition ontology and parsing robustness (15)

MusicXML parsing, voice-aware transitions, chord handling, written/sounding pitch, grace policy honesty, ties, unpitched events, MXL/XML errors, and edge cases are tested and documented.

## 4. Benchmark corpus and frozen outputs (20)

Classified symbolic benchmark manifest, frozen JSON/CSV outputs, checksums, reproducible tables. **Synthetic fixtures alone do not satisfy representative corpus requirements.**

## 5. Programmatic core architecture (15)

Analytical path importable without Streamlit; core numerics separable from UI, interpretation, and export.

## 6. Testing, CI, and quality gates (10)

Regression tests, formal behaviour tests, coverage thresholds, CI, optional lint/type checks.

## 7. Parameter transparency and sensitivity (10)

User-tuned analytical parameters documented; sensitivity analysis for robustness (not validation).

## 8. Reporting and export reproducibility (5)

Reports/exports include parameters, versions, hashes, corpus ID, metric schema version, transition ontology.

---

## Interpretation bands

| Score | Band |
|-------|------|
| 0–59 | Prototype / exploratory |
| 60–74 | Useful internal research software |
| 75–84 | Strong tool with corpus or architecture gaps |
| 85–89 | Near-publication-grade reference implementation |
| 90–94 | Publication-grade systematic notational method (corpus + frozen outputs + programmatic core + robust tests) |
| 95–100 | Field-level reference with broad benchmark adoption and independent reproducibility |

---

## Scoring worksheet (release 2.4.0)

| Dimension | Max | Evidence pointer |
|-----------|-----|------------------|
| 1. Scope | 10 | README, MANUAL_*, report §0 |
| 2. Metrics | 15 | `metrics.py`, `test_metrics.py`, `test_notational_behaviour_axioms.py` |
| 3. Parsing | 15 | `parsing.py`, `transitions.py`, `test_parsing_edge_cases.py` |
| 4. Corpus | 20 | `corpus/manifest.json`, `reference_outputs/` |
| 5. Architecture | 15 | `pipeline.py`, `config.py` |
| 6. Testing/CI | 10 | `tests/`, `.github/workflows/tests.yml` |
| 7. Sensitivity | 10 | `sensitivity.py`, `test_sensitivity.py` |
| 8. Reproducibility | 5 | `reproducibility.py`, report/export metadata |

See `docs/anisotropia_current_rating.md` for the current scored total.
