# Current rating — Anisotropia Direcional (notational 90 rubric)

**Tool identity:** systematic notational directional-field analyzer  
**Rubric:** `docs/anisotropia_90_rubric.md`  
**Release:** 2.4.0 (consolidation patch)  
**Date:** 2026-05-20

---

## Overall score: **88 / 100**

**Band:** 85–89 — near-publication-grade reference implementation; **not** yet 90+ without a licensed representative benchmark.

---

## Evidence by dimension

| Dimension | Max | Score | Evidence |
|-----------|-----|-------|----------|
| 1. Scope & terminology | 10 | **9** | Scope disclaimers; `include_attached` removed from UI |
| 2. Metric correctness | 15 | **14** | Formulas unchanged; axiom tests |
| 3. Parsing & ontology | 15 | **13** | Edge tests; `include_attached` → `NotImplementedError` |
| 4. Corpus & frozen outputs | 20 | **12** | Manifest + 2 frozen metrics; **0 official** benchmarks |
| 5. Programmatic core | 15 | **14** | Streamlit uses `run_analysis()` |
| 6. Testing & CI | 10 | **9** | 138 tests; coverage ~85%; ruff blocking in CI |
| 7. Sensitivity | 10 | **8** | `sensitivity.py` + tests |
| 8. Reproducibility | 5 | **5** | `config_sha256` always set; warnings in metadata/report |

---

## Consolidation patch (2.4.0) highlights

- **Deterministic `config_sha256`** from effective analysis parameters (`reproducibility.py`)
- **Automatic warnings:** low-n (`N_MIN_STABLE`), unpitched display-pitch proxy, parse fallbacks (`sounding_pitch_fallback`, `expand_repeats_fallback`), bootstrap n
- **Streamlit → `run_analysis()`** for core metrics (no formula changes)
- **`grace_policy=include_attached`:** not selectable; raises `GracePolicyNotImplementedError`
- **Ruff** cleanup; CI lint step blocking

---

## Remaining blockers to **90+**

1. Licensed representative benchmark corpus (`include_in_official_benchmark: true`, ≥10–20 scores)
2. Frozen outputs for that corpus
3. Parsing coverage ≥85% on real edge fixtures
4. Optional: implement `include_attached` or keep disabled permanently in docs

---

## Distinctions

| Lens | Assessment |
|------|------------|
| Research software quality | Strong |
| Systematic notational method | Near publication-grade **implementation** |
| Broad repertoire claims | **Not supported** (synthetic fixtures only) |

**Formulas:** unchanged. **Default behaviour:** unchanged (except `include_attached` now errors instead of silent exclude).
