# Anisotropy regression fixtures (Phase 1)

**Location:** `corpus/fixtures/anisotropy_regression/`  
**Tests:** `tests/test_anisotropy_regression_fixtures.py`  
**Exploratory inspection:** `corpus/reports/anisotropy_regression_inspection.md` (non-golden)

---

## Purpose

Phase 1 provides a **musicological regression suite** for **symbolic directional anisotropy** in Directional_Anisotropy. The fixtures are small deterministic MusicXML scores designed to validate **interpretive semantics** of the implemented metrics through:

- pipeline smoke tests (parse → transitions → metrics without crash);
- **qualitative** expectations (e.g. higher vs lower concentration);
- **metamorphic** relations (ascent vs descent, transposition, inversion, windowed contour change).

This suite does **not** freeze strict numerical golden values. It complements unit tests in `tests/test_metrics.py` and formal axioms in `tests/test_notational_behaviour_axioms.py`.

Beyond validating the pipeline, Phase 1 **disciplines interpretation**: it documents what the implemented metrics do and do **not** mean in musicological terms.

---

## Important semantic findings from Phase 1

These are **methodological findings** from the fixture suite and inspection reports. They are implementation-specific unless a future release changes the formulas.

1. **\(D\), not flow_V, carries registral ascent/descent.** For regular quarter-note stepwise lines, \(\mu \approx \pi/2\) and **flow_V may be positive** for both ascending and descending contours. Signed registral tendency is read from **\(D\)** (and contour balance from **\(\tau\)**), not from the sign of flow_V alone.

2. **\(A_{\mathrm{tensor}}\) is axial; \(R\) is circular/vectorial and can decrease under directional cancellation.** A high tensor anisotropy value means a dominant **axis** in \((\Delta t, \Delta p)\) space; it does not guarantee a single **signed** direction of movement. Alternating motion on the same axis can leave \(A_{\mathrm{tensor}}\) high while **\(R\)** falls (see `alternating_up_down_same_axis`).

3. **Contrary contrapuntal motion is not automatically high directional conflict.** The implemented metric `compute_directional_conflict` compares per-part principal axes **\(\mu\)**, not traditional contrapuntal opposition in **\(D\)** or interval terms. Symmetric stepwise ascent in one part and descent in another can share the same \(\mu\) while **\(D\)** opposes — **conflict stays low**; pooled **\(R\)** and net **\(D\)** reflect cancellation instead (see `contrary_motion_symmetric` vs `parallel_ascending_parts`). *Conflito direccional* must not be equated with “movimento contrário” in the conventional contrapuntal sense without checking \(\mu\), \(D\), and \(R\) together.

4. **Windowed analysis is necessary for directional reversal processes.** A single global window can smooth or cancel ascent and descent (e.g. `directional_change_by_window` under `window_mode="total"`). Segmenting by measures (or events/seconds) is required to detect **sign change in \(D\)** across phases of the score.

5. **Time stretching is stable for \(A_{\mathrm{tensor}}\) and \(R\) under the current standardisation** — but this is **implementation-specific.** Doubling note durations while preserving the pitch contour (`time_stretched_same_contour`) leaves \(A_{\mathrm{tensor}}\) and \(R\) near the unstretched case under `local_zscore` per window. Do not treat this as a general invariance under all weight modes, time axes, or standardisation settings without re-checking.

---

## Methodological status

| In scope | Out of scope |
|----------|--------------|
| Symbolic MusicXML pitch–time transitions | Audio, spectral, or waveform analysis |
| Notational drift \(D\), tortuosity \(\tau\) | Psychoacoustic or listener validation |
| Structure-tensor anisotropy \(A_{\mathrm{tensor}}\), axis \(\mu\) | Harmonic dissonance or tonal function |
| Circular coherence \(R\) | Orchestration density or timbre |
| Directional conflict (\(\mu\)-based) | Perceptual tension |

See also [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) for full interpretive limits.

---

## Tensor / circular directionality

| Concept | Implementation | Regression focus |
|---------|----------------|------------------|
| **Axial anisotropy** | \(A_{\mathrm{tensor}} = (\lambda_1-\lambda_2)/(\lambda_1+\lambda_2)\) on standardised \((\Delta t,\Delta p)\) | May stay **high** when vectors align on one **axis** even if directions along that axis cancel |
| **Vectorial directional flow** | \(R\) from mean of \(\theta_i=\mathrm{atan2}(\Delta p,\Delta t)\); \(D\) from signed \(\Delta p\) | Captures **net** direction and angular alignment |
| **flow_U / flow_V** | \(A_{\mathrm{tensor}}\cos\mu\), \(A_{\mathrm{tensor}}\sin\mu\) | Plot/export components of **tensor axis**, not signed pitch drift |

### Registral ascent/descent: use D, not flow_V

In the current implementation, **registral ascent/descent** should be interpreted primarily through **\(D\)**, not through the sign of **flow_V**. For regular quarter-note ascending and descending lines, \(\mu\) may remain approximately \(\pi/2\), yielding **positive flow_V in both cases**. Therefore **flow_V must not be used alone** as a proxy for melodic ascent/descent. The regression tests assert **\(D\)** (and pooled **\(R\)** where relevant), not opposing flow_V signs between ascent and descent.

**Directional conflict** compares per-part **\(\mu\)** (principal tensor axes). Symmetric contrary stepwise parts can share the same \(\mu\) while **\(D\)** opposes — conflict stays low; pooled **\(R\)** drops instead.

---

## Fixture catalogue

| Fixture | Musical sketch | Expected behaviour (qualitative) |
|---------|----------------|--------------------------------|
| **static_repetition** | C4–C4–C4–C4 | All \(\Delta p=0\); \(D=0\); horizontal symbolic motion in time; flow_V not meaningful (NaN) |
| **uniform_ascending_steps** | C4–D4–E4–F4–G4 | Positive \(D\); high \(R\), high \(A_{\mathrm{tensor}}\) |
| **uniform_descending_steps** | G4–F4–E4–D4–C4 | Negative \(D\); similar \(A_{\mathrm{tensor}}\), \(R\) to ascending |
| **alternating_up_down_same_axis** | C4–D4–C4–D4–C4–D4 | High \(\tau\); lower \(R\) than uniform ascent; \(A_{\mathrm{tensor}}\) may remain high (axial) |
| **balanced_four_directions** | Mixed up/down/horizontal steps | Lower \(R\) and higher \(\tau\) than uniform ascent |
| **parallel_ascending_parts** | Two parts, same ascent | Low conflict; aligned per-part \(D\); high pooled \(R\) |
| **contrary_motion_symmetric** | Part ascends, part descends | Opposite per-part \(D\); pooled \(D \approx 0\); lower pooled \(R\) than parallel |
| **oblique_motion** | Static layer + ascending layer | Distinct pooled profile; \(R\) between parallel and contrary patterns |
| **directional_change_by_window** | Ascend (m1–2), descend (m3–4) | Windowed \(D>0\) then \(D<0\) (measures, size=2, step=2) |
| **transposed_same_contour** | Ascending line up one octave | \(A_{\mathrm{tensor}}\), \(R\), \(\mu\), flow components ≈ uniform ascent |
| **pitch_inversion_same_rhythm** | Ascending contour inverted around E4 | Similar \(A_{\mathrm{tensor}}\), \(R\); **\(D\)** sign flips |
| **time_stretched_same_contour** | Same pitches, doubled durations | Stable \(A_{\mathrm{tensor}}\), \(R\) under current standardisation (see inspection report) |
| **dense_events_no_direction** | Long alternating C–D pattern | Many transitions; **lower** \(R\) than sparse aligned case |
| **sparse_strong_direction** | C4–G4–C5 | Few transitions; **strong** \(R\) despite low \(n\) |

---

## Qualitative-only values

The following are **not** asserted to exact tolerances in Phase 1:

- Absolute numeric targets for \(A_{\mathrm{tensor}}\) or \(R\) per fixture;
- Strict golden JSON references;
- Perceptual or acoustic ground truth.

Inspection outputs in `corpus/reports/` are **exploratory** and may change with parser tweaks. Promote to frozen references only after corpus review.

---

## Interpretive warnings

1. **Do not** treat a single scalar (\(A_{\mathrm{tensor}}\) alone, or \(R\) alone) as a complete musical description.
2. **Do not** equate high event count with high directional concentration (`dense_events_no_direction` vs `sparse_strong_direction`).
3. **Do not** read flow_V sign as melodic up/down — use **\(D\)** for registral tendency.
4. **Do not** equate **directional conflict** with harmonic dissonance, textural density, or traditional contrapuntal “contrary motion” — see [Important semantic findings from Phase 1](#important-semantic-findings-from-phase-1) (point 3).

---

## Scripts

```bash
# Regenerate MusicXML fixtures
python corpus/scripts/create_anisotropy_regression_fixtures.py

# Exploratory metric snapshot (updates corpus/reports/)
python corpus/scripts/inspect_anisotropy_regression.py

# Run regression tests
python -m pytest tests/test_anisotropy_regression_fixtures.py -q
```

---

## Related documentation

- [METRIC_SEMANTICS.md](METRIC_SEMANTICS.md) — metric meaning and limits  
- [MANUAL_TECNICO.md](../MANUAL_TECNICO.md) — formulas  
- [CORPUS_REFERENCIA.md](../CORPUS_REFERENCIA.md) — frozen benchmark (separate from this suite)
