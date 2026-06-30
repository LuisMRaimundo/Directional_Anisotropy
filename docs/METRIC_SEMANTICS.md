# Metric semantics — Directional_Anisotropy

**Version:** 2.4.0  
**Scope:** Interpretive and methodological meaning of the main notational directional-field metrics, aligned with the implementation in `anisotropia/`.

> **Implementation reference (formulas, algorithms):** [MANUAL_TECNICO.md](../MANUAL_TECNICO.md)  
> **Short metric summary (UI-oriented):** [MANUAL_METRICAS.md](../MANUAL_METRICAS.md)

---

## 1. Scope and methodological status

**Directional_Anisotropy** (package `anisotropia`) computes **symbolic / notational descriptors** of directional organisation in **score-derived musical events**. Input is **MusicXML** (or related symbolic formats parsed via music21). The system builds a field of pitch–time **transition vectors** \((\Delta t, \Delta p)\) and summarises their distribution with scalar metrics, structure-tensor quantities, circular statistics, and optional windowed aggregates.

This is **not**:

| Category | Status |
|----------|--------|
| Audio analysis | **Not implemented** — no waveform, spectrum, or recording input |
| Spectral analysis | **Not implemented** — no frequency-domain descriptors |
| Psychoacoustic / perceptual validation | **Not implemented** — metrics are formal, not listener-tested |
| Loudness, timbre, salience | **Not measured** |
| Orchestration weight / acoustic density | **Not modelled** (unless inferred informally by the analyst from score layout) |
| Listener perception | **Not measured** |

What **is** measured: **directional behaviour of parsed symbolic pitch/time events** under the implemented transition model, weighting, standardisation, and windowing assumptions documented below and in [MANUAL_TECNICO.md](../MANUAL_TECNICO.md).

---

## 2. Core vocabulary

| Term | Meaning in this codebase |
|------|---------------------------|
| **Event** | A discrete onset in a part (or part+voice) timeline: `(t, ql, dur_ql, p, meas, voice, …)` where `p` is MIDI semitones (float). Derived from MusicXML via `parse_musicxml`. |
| **Transition** | A directed link between two events in a constructed chain, with pitch displacement **Δp** and temporal displacement **Δt** (in quarter lengths and/or seconds). |
| **Horizontal transition** | A transition along a **melodic / temporal** chain within one MusicXML voice: consecutive collapsed onsets with **\|Δt\| > ε** (`epsilon_dt`). This is the **main directional field** for metrics. See `build_directional_transition_tables` in `transitions.py`. |
| **Vertical transition** | Ordered pitch pairs **within the same** `(voice, ql)` with **Δt ≈ 0** (chord-internal). Built only as an **auxiliary** table when `include_vertical_auxiliary=True`; **not** mixed into the main metric field by default. |
| **Displacement vector** | The pair \((\Delta t_i, \Delta p_i)\) for transition \(i\). **Δt** uses `dt_ql` or `dt_sec` depending on `time_axis`; **Δp** is always semitone difference. |
| **Δt** | Temporal displacement between successive events in the chain: \(\Delta t^{\mathrm{ql}} = \mathrm{ql}_{b} - \mathrm{ql}_{a}\), \(\Delta t^{\mathrm{sec}} = t_{b} - t_{a}\). |
| **Δp** | Pitch displacement in semitones: \(\Delta p = p_{b} - p_{a}\) (positive = upward in the chosen pitch space). |
| **Part-level analysis** | Metrics computed per instrument/part (and optionally per voice if `split_voices=True`) on that part's horizontal transitions within each window. |
| **Aggregate-level analysis** | **2A**: weighted mean of per-part metrics (circular mean for μ). **2B**: single metric pass on the **pooled** transition set of all parts. |
| **Analysis window** | A slice of transitions sharing a label (`total`, `m4–m7`, `t1.50–6.50`, `e25–e74`, …). All parts are cut to the **same** window labels (reference part = most transitions). |
| **Window mode** | How windows are defined: `measures`, `seconds`, `events`, or `total`. See §10. |
| **Written pitch space** | `pitch_space="written"`: pitches as notated; transposing instruments retain written transposition. |
| **Sounding pitch space** | `pitch_space="sounding"` (default): `Score.toSoundingPitch()` before event extraction; on failure, written pitch is used with a parse warning. |
| **Directional flow** | Visual/export shorthand: components **flow_U**, **flow_V** = \(A_{\mathrm{tensor}} \cos\mu\), \(A_{\mathrm{tensor}} \sin\mu\) (see §8). |
| **Anisotropy** | In this project: **concentration of transition directions** in \((\Delta t, \Delta p)\) space, quantified mainly by **\(A_{\mathrm{tensor}}\)** and related tensor/circular measures — **not** physical or acoustic anisotropy. |
| **Directional concentration** | Alignment of transition **directions** (angles \(\theta_i = \mathrm{atan2}(\Delta p_i, \Delta t_i)\)), summarised by **R** and related quantities. Distinct from total **amount** of pitch movement. |
| **Directional conflict** | Between parts in a window: **\(1 - R_{\mathrm{inst}}\)** where \(R_{\mathrm{inst}}\) is the weighted circular resultant of per-part **μ** values. See §9. |

### Parsing assumptions (high level)

| Material | Handling |
|----------|----------|
| **Parts / voices** | One event list per part (default) or per `part | vN` if `split_voices=True`. Horizontal chains follow **MusicXML voice** after per-voice onset collapse. |
| **Chords** | If `expand_chord_pitches=True`, each pitch is an event; `chord_simultaneity="coincident"` shares onset time (recommended). Same-onset pitches are **collapsed** to one representative per voice for the main horizontal field (centroid pitch, max duration). |
| **Rests** | Omitted from event lists (`NotRest` elements only). |
| **Ties** | `merge_tied_notes=True` (default): `stripTies()` → one logical onset; `False` keeps each written notehead (Δp across tie may be 0). |
| **Grace notes** | `grace_policy="exclude"` (default) or `include`; `include_attached` is not implemented. |
| **Unpitched / percussion** | `map_display` (staff position as MIDI proxy) or `exclude`. |
| **Repeats** | `expand_repeats=False` by default; optional expansion duplicates passages where music21 can expand. |
| **Grand staff** | `merge_grand_staff=True` merges `Staff1`/`Staff2` into one part key when XML ids match. |

Details: [MANUAL_TECNICO.md §3](../MANUAL_TECNICO.md#3-eventos-transições-e-pesos), `parsing.py`, `transitions.py`.

---

## 3. Horizontal transition model

A **horizontal transition** is **not** performed gesture or audio motion. It is a **symbolic, notational** step from one parsed onset to the next along a **voice-specific melodic timeline** after simultaneous onsets at the same `(voice, ql)` are collapsed.

**Construction (default, `legacy_mixed_mode=False`):**

1. Group events by MusicXML **voice**.
2. Sort by `(ql, p)` within each voice.
3. Collapse events at the same `(voice, ql)` to one representative (mean `p`, max `dur_ql`).
4. Form consecutive pairs along each voice chain → candidate horizontal transitions.
5. Keep only rows with **\|Δt\| > ε** (`epsilon_dt`, compared on `dt_sec` when seconds exist and the time axis is seconds-oriented in the transition filter).

**Pitch space:** If `pitch_space="written"`, Δp reflects **written** intervals (e.g. clarinet in A reads as written). If `pitch_space="sounding"`, transposing instruments are normalised to **concert pitch** when `toSoundingPitch()` succeeds.

**Legacy mode:** `legacy_mixed_mode=True` uses global consecutive pairs from `transitions_from_events` (pre-stagger/collapse ordering as returned by the parser). Use only for backward compatibility.

Vertical (simultaneity-internal) transitions are documented separately; they do **not** feed `compute_metrics_from_transitions` in the default pipeline.

---

## 4. D, τ, and movement magnitude

These metrics use **only Δp and weights** \(w_i\). They do **not** use the structure tensor and are computed on **raw** (non-standardised) pitch displacements.

**Weight** \(w_i\): from `w_dur` (`weight_mode="dur"`) or `w_min` (`weight_mode="min"`). See [MANUAL_TECNICO.md §3.2](../MANUAL_TECNICO.md#32-transição-definição-local-no-dataframe).

Let \(\mathrm{denom} = \sum_i w_i |\Delta p_i|\).

### D — signed pitch drift

\[
D = \frac{\sum_i w_i \Delta p_i}{\mathrm{denom}}
\quad\text{if }\mathrm{denom} > 0,\text{ else }0
\]

- **Range:** typically \([-1, 1]\).
- **Meaning:** normalised **signed** sum of pitch changes — net registral tendency (up vs down), not vector magnitude in \((\Delta t, \Delta p)\).
- **Not:** total movement amount, melodic interval size distribution, or tonal function.

### τ (tau) — tortuosity

\[
\tau = 1 - \frac{\left|\sum_i w_i \Delta p_i\right|}{\mathrm{denom}}
\quad\text{if }\mathrm{denom} > 0,\text{ else }0;\quad
\tau \leftarrow \mathrm{clip}(\tau, 0, 1)
\]

- **τ ≈ 0:** net displacement uses most of the absolute pitch motion (unidirectional contour).
- **τ ≈ 1:** signed displacements **cancel** (oscillatory / tortuous contour).

**D and τ are not norms of \((\Delta t, \Delta p)\).** Neither Δt nor Δp is standardised before D or τ.

**Filtering:** Transitions with non-finite `dp` or Δt, or with **Δt ≤ 0**, are dropped before any metric (`compute_metrics_from_transitions`).

---

## 5. Direction angle μ

**μ** (`Metrics.mu`, alias of `mu_axis`) is the **principal-axis angle** of the **structure tensor** \(\mathbf{J}\) built from **standardised** \((\Delta t, \Delta p)\) (per `standardization_mode`).

**Tensor construction** (after standardisation \(\tilde{v}_{1,i}, \tilde{v}_{2,i}\)):

\[
\mathbf{J} = \sum_i w_i \tilde{\mathbf{v}}_i \tilde{\mathbf{v}}_i^\top
\]

`numpy.linalg.eigh(J)` yields eigenvalues \(\lambda_2 \leq \lambda_1\) (code assigns smaller to `lambda2`, larger to `lambda1`). The eigenvector \(\mathbf{v} = (v_1, v_2)^\top\) for \(\lambda_1\) defines:

\[
\mu = \mathrm{atan2}(v_2, v_1) \in (-\pi, \pi]
\]

**Interpretive limits:**

- μ is a **mathematical direction** in the model's (possibly standardised) Δt–Δp plane — **not** a psychological label of "melodic direction."
- μ depends on **time axis** (`ql` vs `sec`), **standardization_mode**, and the **mix of Δt and Δp** in the window.
- Eigenvector sign is arbitrary; \(\mathbf{v}\) and \(-\mathbf{v}\) denote the same axis.

**R uses a different angle:** per-transition \(\theta_i = \mathrm{atan2}(\Delta p_i, \Delta t_i^\star)\) on **non-standardised** values (§6).

---

## 6. R — circular resultant / directional concentration

For each transition, \(\theta_i = \mathrm{atan2}(\Delta p_i, \Delta t_i^\star)\) where \(\Delta t_i^\star\) is `dt_ql` or `dt_sec` per `time_axis`.

\[
C = \frac{\sum_i w_i \cos\theta_i}{\sum_i w_i}, \quad
S = \frac{\sum_i w_i \sin\theta_i}{\sum_i w_i}, \quad
R = \sqrt{C^2 + S^2}
\]

- **R ≈ 1:** transition **directions** (angles) are strongly aligned.
- **R ≈ 0:** directions are dispersed or **mutually cancelling** on the circle.
- **R is not "amount of movement."** Frequent large \|Δp\| with opposing θ can yield **low R**.
- **R is not identical to \(A_{\mathrm{tensor}}\)** — both relate to directionality but R uses raw atan2 angles; \(A_{\mathrm{tensor}}\) uses the weighted structure tensor on standardised components.

---

## 7. A_tensor

When \(\lambda_1 + \lambda_2 > 0\):

\[
A_{\mathrm{tensor}} = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2} \in [0, 1]
\]

Otherwise \(A_{\mathrm{tensor}} = \mathrm{NaN}\).

**Meaning:**

- Summarises **directional asymmetry / concentration** in the **distribution of transition vectors** (via \(\mathbf{J}\)).
- **\(A_{\mathrm{tensor}} \approx 0\):** transitions spread without a dominant axis (notational isotropy in this model).
- **\(A_{\mathrm{tensor}} \approx 1\):** transitions align along one principal axis (strong notational anisotropy).

**Not:**

- Acoustic anisotropy, radiation pattern, or physical directivity.
- Orchestral density or timbral "brightness."

Standardisation (`local_zscore`, `robust_scale`, or `none`) is applied to \((\Delta t, \Delta p)\) **before** forming \(\mathbf{J}\), so \(A_{\mathrm{tensor}}\) reflects **shape** of the cloud more than absolute semitone or beat scales (when standardisation is active).

---

## 8. flow_U and flow_V

Exported in Excel (`instrument_metrics_with_flow_components`) and used in flow-map visualisations:

\[
\text{flow\_U} = A_{\mathrm{tensor}} \cos\mu, \qquad
\text{flow\_V} = A_{\mathrm{tensor}} \sin\mu
\]

- These are **derived vector components**, not unit vectors.
- **Magnitude** \(\sqrt{\mathrm{flow\_U}^2 + \mathrm{flow\_V}^2} = |A_{\mathrm{tensor}}|\) when μ and \(A_{\mathrm{tensor}}\) are finite.
- **Direction** in the Δt–Δp plane matches **μ** (principal tensor axis).
- **Interpretation:** a compact 2D summary for plotting quiver arrows: **length ∝ \(A_{\mathrm{tensor}}\)**, **angle = μ**. They encode the same information as \((A_{\mathrm{tensor}}, \mu)\), not independent measurements.

Missing or non-finite `mu` / `A_tensor` propagate as NaN or 0 per export logic.

---

## 9. Directional conflict

`compute_directional_conflict(metrics_by_part)` compares **per-part principal directions μ** within one window.

For parts \(j\) with finite `mu` and positive `weight_sum` \(W_j\):

\[
C_{\mathrm{inst}} = \frac{\sum_j W_j \cos\mu^{(j)}}{\sum_j W_j}, \quad
S_{\mathrm{inst}} = \frac{\sum_j W_j \sin\mu^{(j)}}{\sum_j W_j}
\]

\[
R_{\mathrm{inst}} = \sqrt{C_{\mathrm{inst}}^2 + S_{\mathrm{inst}}^2}, \quad
\text{directional conflict} = 1 - R_{\mathrm{inst}}
\]

| Outcome | Meaning |
|---------|---------|
| **Low conflict** (→ 0) | Part-level μ values are **aligned** (similar directional tendency in the tensor sense). |
| **High conflict** (→ 1) | μ values **oppose or cancel** (stratified motion in different directions). |
| **NaN** | No valid parts, or \(\sum W_j \leq 0\). |

**Not:** contrapuntal dissonance, harmonic tension, textural density, or perceptual "conflict." Requires **≥ 2 parts** with valid metrics for meaningful comparison (single-part windows yield NaN in the pipeline).

---

## 10. Windowing semantics

Implemented in `window_slices_for_part` (`windowing.py`).

| `window_mode` | Parameters | Window contents |
|---------------|------------|-----------------|
| **`total`** | — | All horizontal transitions of the part |
| **`measures`** | `window_size`, `step` (integers) | Transitions with `meas ∈ [m_0, m_0 + size)` |
| **`seconds`** | `window_size`, `step` (floats) | Transitions with `t ∈ [t_cur, t_cur + size)` |
| **`events`** | `window_size`, `step` (integers) | Consecutive slices `iloc[i_0 : i_0 + size)` of the transition table |

**Fallback:** If `window_mode="measures"` but **all** `meas == 0`, the code **falls back to `seconds`** on column `t`.

**Seconds availability:** Real-second windows and `time_axis="sec"` depend on music21 `secondsMap`. If seconds are unavailable, the pipeline uses **quarterLength / symbolic time** (`ql`) per `effective_time_axis` in `config.py`.

**Legitimate differences:** The same score analysed with `measures` vs `events` vs `seconds` can produce **different metric profiles** — windows partition different units of musical structure.

---

## 11. Confidence intervals and sensitivity

### Bootstrap CIs (`bootstrap_ci=True`, default in scientific mode)

| Level | Condition | Resampled unit | Metrics with CI |
|-------|-----------|----------------|-----------------|
| Per-window | \(n \geq 8\) transitions | **Transitions** (with replacement, B=1000, seed 42) | **\(A_{\mathrm{tensor}}\)**, **R** |
| Aggregation 2A | ≥ 2 valid instruments | **Instruments** (with replacement) | **\(A_{\mathrm{tensor}}\)**, **R** |

CI bounds are **2.5% and 97.5% percentiles** of the bootstrap distribution.

**Meaning:** computational **uncertainty / stability** of the estimator under resampling — **not** perceptual confidence, not population inference for listeners.

**Stability heuristic:** `N_MIN_STABLE = 15` transitions is documented as a practical threshold for stabler estimates (see `MANUAL_METRICAS.md`).

### Sensitivity analysis (`sensitivity.py`)

`run_parameter_sensitivity` varies parameters (`chord_rep`, `standardization_mode`, `weight_mode`, `window_mode`, etc.) and reports deltas vs baseline (typically **2B** metrics). Disclaimer in code: **robustness analysis, not validation** against an external gold standard.

---

## 12. Metric interpretation table

| Metric | Measures | Does not measure | Main interpretive risk |
|--------|----------|------------------|------------------------|
| **Δt** | Symbolic time step between chained onsets | Real performance timing, rubato | Confusing ql with seconds when `has_seconds` is false |
| **Δp** | Semitone pitch step in chosen pitch space | Spelling, harmonic function, interval class | Written vs sounding changes transposing-instrument Δp |
| **D** | Weighted signed pitch drift | Total movement, Δt coupling, harmony | Treating D as "anisotropy" |
| **τ** | Pitch contour tortuosity (cancellation) | Rhythmic complexity | Equating τ with "ornamentation" without context |
| **μ** | Principal axis of standardised transition tensor | Perceptual melodic direction | Ignoring standardisation and time-axis choice |
| **R** | Alignment of raw transition angles θ | Movement magnitude | Assuming high \|Δp\| implies high R |
| **A_tensor** | Tensor anisotropy of standardised transitions | Acoustic directivity, loudness | Calling it "physical anisotropy" |
| **flow_U / flow_V** | Plot/export components of \((A_{\mathrm{tensor}}, \mu)\) | Independent physical flows | Reading U,V as velocities in performance |
| **Directional conflict** | Misalignment of per-part μ | Harmonic or textural dissonance | Single-part scores (NaN conflict) |
| **Windowed A_tensor** | Anisotropy within segment | Global work identity alone | Comparing windows with different \(n\) |
| **Confidence intervals** | Bootstrap spread of \(A_{\mathrm{tensor}}\), R | Listener certainty | Over-interpreting narrow CI as "truth" |
| **written / sounding** | Pitch-space convention for Δp | Automatic correctness of transposition | Silent fallback to written on `toSoundingPitch` failure |

---

## 13. Examples of interpretive distinctions

1. **Consistent upward melody** (many positive Δp, similar θ): **high R**, often **high \(A_{\mathrm{tensor}}\)**, **D > 0**, **τ ≈ 0**.
2. **Alternating up and down** with similar step sizes: **τ high**, **D ≈ 0**; **R** may be **low** even if transitions are frequent.
3. **Two parts, same μ**: **low directional conflict**; does not require identical melodic contours.
4. **Two parts, μ differing by ~π**: **high directional conflict** (opposed directional tendencies in the model).
5. **Many events, opposing directions**: not necessarily anisotropic — **\(A_{\mathrm{tensor}}\)** and **R** can stay low if vectors cancel.
6. **Few but parallel transitions** (e.g. steady ascent): can show **high R** and **high \(A_{\mathrm{tensor}}\)** with small \(n\) — check bootstrap CI / \(n\).
7. **Clarinet part in written pitch vs sounding**: same score can change **Δp**, **μ**, and conflict when transposition is normalised.

---

## 14. Relation to musicological use

These metrics may **support** (not replace) analysis of:

| Topic | Relevant metrics |
|-------|------------------|
| Directional tendency | D, μ, R, flow components |
| Registral ascent / descent | D (pitch-only drift) |
| Melodic / textural vectorisation | \(A_{\mathrm{tensor}}\), μ, θ distribution (rose plots) |
| Directional stabilisation vs dispersion | R, \(A_{\mathrm{tensor}}\) over windows |
| Opposed stratified motion | Directional conflict, per-part μ |
| Convergence / divergence between parts | Conflict + per-part μ comparison |
| Temporal evolution | Windowed series of \(A_{\mathrm{tensor}}\), R, D, τ |

**Use together:** D/τ describe **pitch contour** statistics; \(A_{\mathrm{tensor}}\)/μ describe **2D transition geometry**; R describes **angular alignment**; conflict describes **cross-part axis alignment**. No single scalar is a complete musical characterisation.

---

## 15. Limitations

- **No audio signal analysis**
- **No spectral density or timbral modelling**
- **No loudness modelling**
- **No perceptual validation** or listening experiments
- **No direct orchestration-weighting model** unless the analyst supplies external context
- **Dependent on MusicXML / music21 parsing** quality and export conventions
- **Sensitive to:** tie merging, grace-note policy, repeat expansion, transposition / pitch_space, chord expansion, voice splitting, `epsilon_dt`, window mode, standardisation mode, weight mode
- **Formal descriptors** supporting musicological argument — **not** a substitute for score reading, context, or aesthetic judgment

---

## 16. Related documentation

| Document | Role |
|----------|------|
| [MANUAL_TECNICO.md](../MANUAL_TECNICO.md) | Exact formulas, pipeline, pseudocode |
| [MANUAL_METRICAS.md](../MANUAL_METRICAS.md) | Streamlit-oriented metric summary |
| [README.md](../README.md) | Project overview and limitations |
| [CORPUS_REFERENCIA.md](../CORPUS_REFERENCIA.md) | Synthetic fixtures and benchmark status |
| [docs/anisotropia_90_rubric.md](anisotropia_90_rubric.md) | Quality rubric (notational scope) |

---

*This document describes semantics and interpretation only. It does not alter the implemented formulas in `anisotropia/metrics.py`.*
