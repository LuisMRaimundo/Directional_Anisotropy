"""Report generation: technical and pedagogical (English)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from anisotropia import CANONICAL_TOOL_NAME, PACKAGE_NAME
from anisotropia.references import format_references_report_markdown


def _fmt(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def _fmt_ci(lo: Optional[float], hi: Optional[float]) -> str:
    if (lo is None or pd.isna(lo)) or (hi is None or pd.isna(hi)):
        return ""
    return f"[{lo:.4f}, {hi:.4f}]"


def _grace_operational_short(grace_policy: Any) -> str:
    """One-line table cell for grace operational effect."""
    g = str(grace_policy or "exclude").lower()
    if g == "exclude":
        return "Not emitted as note events (excluded at parse)."
    if g == "include":
        return "Emitted as normal note events (music21 onsets/durations)."
    return "Not implemented; programmatic use raises GracePolicyNotImplementedError."


def _grace_operational_paragraph(grace_policy: Any) -> str:
    """Longer explanation for methodology section."""
    g = str(grace_policy or "exclude").lower()
    if g == "exclude":
        return (
            "Grace notes were **excluded** when building note-event lists: they do not appear as rows in "
            "`events_by_part` and do not contribute to transition tables."
        )
    if g == "include":
        return (
            "Grace notes were **included** as ordinary `Note`/`NotRest` events with durations and onsets "
            "as returned by the parser (they contribute to events and, unless filtered elsewhere, to transitions)."
        )
    return (
        "The `include_attached` policy is **not implemented** in this release. "
        "Passing it to the parser raises `GracePolicyNotImplementedError` (use `exclude` or `include`)."
    )


def generate_report(
    filename: str,
    df_results: pd.DataFrame,
    params: Dict[str, Any],
    n_parts: int,
    n_windows: int,
    total_transitions: int,
    summary_counts: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate detailed analysis report in English.
    Two sections: technical (with formulas) and pedagogical (for non-specialists).
    """
    totals = df_results[df_results["scope"].isin(["total_2A", "total_2B"])]

    report = []
    report.append(f"# {CANONICAL_TOOL_NAME} — Notational Analysis Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Source file:** {filename}")
    report.append("")
    report.append(
        "**Scope:** This report describes **notational anisotropy** from symbolic MusicXML "
        "pitch–time transitions. It is **not** audio analysis, a perception model, harmonic analysis, "
        "Schenkerian analysis, or general texture analysis."
    )
    report.append("")

    if params.get("software_version") or params.get("metric_schema_version"):
        report.append("## 0. Reproducibility metadata")
        report.append("")
        report.append("| Field | Value |")
        report.append("|-------|-------|")
        for key in (
            "canonical_tool_name",
            "package_name",
            "software_version",
            "metric_schema_version",
            "input_sha256",
            "config_sha256",
            "corpus_id",
            "time_axis_effective",
            "bootstrap_random_seed",
            "N_BOOTSTRAP",
            "bootstrap_unit",
            "transition_ontology_main_field",
            "vertical_auxiliary_built",
            "main_field_horizontal_only",
        ):
            if key in params and params[key] is not None:
                report.append(f"| {key} | {params[key]} |")
        if params.get("global_zscore_note"):
            report.append(f"| global_zscore_note | {params['global_zscore_note']} |")
        if params.get("corpus_validation_note"):
            report.append(f"| corpus_validation_note | {params['corpus_validation_note']} |")
        if params.get("scope_disclaimer"):
            report.append(f"| scope_disclaimer | {params['scope_disclaimer']} |")
        if not params.get("grace_include_attached_implemented", True):
            report.append("| grace_include_attached_implemented | false |")
        report.append("")

    warn_list = params.get("warnings") or []
    warn_struct = params.get("warnings_structured") or []
    if warn_list or warn_struct:
        report.append("## 0b. Analysis warnings")
        report.append("")
        for msg in warn_list:
            report.append(f"- {msg}")
        if warn_struct and not warn_list:
            for w in warn_struct:
                if isinstance(w, dict) and w.get("message"):
                    report.append(f"- {w['message']}")
        report.append("")

    # --- Parameters ---
    report.append("## 1. Analysis Parameters")
    report.append("")
    report.append("| Parameter | Value |")
    report.append("|-----------|-------|")
    report.append(f"| Chord representative | {params.get('chord_rep', '—')} |")
    report.append(f"| Transition weight mode | {params.get('weight_mode', '—')} |")
    report.append(f"| Window mode | {params.get('window_mode', '—')} |")
    report.append(f"| Window size | {params.get('window_size', '—')} |")
    report.append(f"| Step | {params.get('step', '—')} |")
    report.append(f"| Scientific mode (bootstrap CI only) | {params.get('scientific_mode', False)} |")
    report.append(f"| Tensor standardization mode (`standardization_mode`) | {params.get('standardization_mode', 'local_zscore')} |")
    if str(params.get("standardization_mode", "")).lower() == "global_zscore":
        report.append(
            "| global_zscore (operational) | **Alias of local_zscore** per metric window — not corpus-global normalization |"
        )
    report.append(f"| Bootstrap CI enabled | {params.get('bootstrap_ci', params.get('scientific_mode', False))} |")
    if params.get("N_BOOTSTRAP") is not None:
        report.append(f"| N_BOOTSTRAP | {params.get('N_BOOTSTRAP')} |")
    if params.get("bootstrap_random_seed") is not None:
        report.append(f"| Bootstrap random seed | {params.get('bootstrap_random_seed')} |")
    if params.get("bootstrap_unit"):
        report.append(f"| Bootstrap resampling unit | {params.get('bootstrap_unit')} |")
    gp = params.get("grace_policy", "—")
    report.append(f"| Grace-note policy (label) | {gp} |")
    report.append(f"| Grace notes — operational effect | {_grace_operational_short(gp)} |")
    report.append("| Tie handling | Continuations merged (tie ≠ new onset / no spurious Δp at tie) |")
    report.append(f"| Pitch space (written vs sounding) | {params.get('pitch_space', 'sounding')} |")
    report.append(f"| Unpitched percussion policy | {params.get('unpitched_policy', 'map_display')} |")
    report.append(f"| Expand chord pitches (one event per note head) | {params.get('expand_chord_pitches', True)} |")
    report.append(f"| Chord simultaneity (coincident vs stagger) | {params.get('chord_simultaneity', 'coincident')} |")
    report.append(f"| ε_dt (minimum |Δt| in ql for horizontal class, non-legacy) | {params.get('epsilon_dt', '—')} |")
    report.append(f"| legacy_mixed_mode | {params.get('legacy_mixed_mode', False)} |")
    report.append(f"| Merge tied notes (strip ties) | {params.get('merge_tied_notes', True)} |")
    report.append(f"| Expand score repeats | {params.get('expand_repeats', False)} |")
    report.append(f"| Auxiliary vertical transition table built | {params.get('vertical_auxiliary_built', True)} |")
    report.append(f"| Main metrics use horizontal field only | {params.get('main_field_horizontal_only', True)} |")
    report.append("")
    report.append("### Voice / part aggregation (disambiguated)")
    report.append("")
    report.append("| Question | Value |")
    report.append("|----------|-------|")
    report.append(f"| Parser: separate event streams per MusicXML voice key (`split_voices`) | {params.get('split_voices', False)} |")
    report.append(f"| Voice-aware transition construction (events carry voice id) | {params.get('voice_aware_transition_construction', True)} |")
    report.append(f"| Per-voice melodic chains for main horizontal table (non-legacy) | {params.get('per_voice_chain_construction', True)} |")
    report.append(f"| Cross-voice consecutive pairing in main field (legacy mixed only) | {params.get('cross_voice_chaining_in_main_field', False)} |")
    report.append(f"| Split-by-voice output labels (e.g. “Part \\| v2”) | {params.get('split_by_voice_output_aggregation', False)} |")
    report.append("")
    report.append("*`split_voices` controls whether parsed events are stored under separate part/voice labels. "
                  "The default horizontal ontology still builds chains **per voice** inside each part when `legacy_mixed_mode=False`.*")
    report.append("")

    # --- Summary ---
    report.append("## 2. Summary — counts and samples")
    report.append("")
    report.append(f"- **Parts/instruments (event streams):** {n_parts}")
    report.append(f"- **Analysis windows:** {n_windows}")
    sc = summary_counts or {}
    if sc:
        report.append(f"- **n_note_events_total** (all parts, parsed): {sc.get('n_note_events_total', '—')}")
        report.append(f"- **n_horizontal_transitions_total** (sum over parts, main horizontal DataFrame rows): {sc.get('n_horizontal_transitions_total', '—')}")
        report.append(f"- **n_vertical_auxiliary_total** (sum over parts, optional simultaneity pairs): {sc.get('n_vertical_auxiliary_total', '—')}")
        report.append(f"- **n_reference_part_horizontal** (rows used to define windows; reference part): {sc.get('n_reference_part_horizontal', total_transitions)}")
        report.append(f"- **n_reference_part_vertical** (auxiliary, reference part): {sc.get('n_reference_part_vertical', '—')}")
        report.append(
            "- **Reference for windowing:** the part with the longest horizontal table; "
            "`n_reference_part_horizontal` is the number of **horizontal** transitions on that part (full excerpt before window filters)."
        )
        report.append("")
        report.append("### 2.1 Row counts in the results table (`n` column)")
        report.append("")
        report.append(
            "- **scope = instrumento:** `n` = number of **horizontal** transitions in that instrument’s window "
            "(same ontology as the main field; not vertical auxiliary rows)."
        )
        report.append(
            "- **scope = TOTAL_2A:** `n` = total number of transitions entering the weighted aggregate "
            "(sum of per-instrument `n` in that window)."
        )
        report.append(
            "- **scope = TOTAL_2B:** `n` = number of transitions in the **pooled** horizontal DataFrame "
            "(all instruments concatenated for that window)."
        )
        report.append(
            "*Therefore `n` for TOTAL_2A and TOTAL_2B generally **differs** from `n_reference_part_horizontal` "
            "(reference part only) and from per-instrument `n` unless there is a single part and one window.*"
        )
        report.append("")
    else:
        report.append(f"- **Horizontal transitions on reference part (full table before per-window filter):** {total_transitions}")
        report.append("")

    # --- TECHNICAL SECTION ---
    report.append("---")
    report.append("## 3. Technical Report (Specialists)")
    report.append("")
    report.append("### 3.1 Formal definition of the field")
    report.append("")
    report.append("For each instrument *j* and window *w*:")
    report.append("")
    report.append("**1. Local vectors:** $\\mathbf{v}_i = (\\Delta t_i, \\Delta p_i)$")
    report.append("")
    report.append("**2. Structure tensor:** $\\mathbf{J}^{(j,w)} = \\sum_i w_i \\mathbf{v}_i \\mathbf{v}_i^\\top$")
    report.append("")
    report.append("**3. Eigenvalues/eigenvectors:** $\\lambda_1 \\geq \\lambda_2$, with principal eigenvector $\\mathbf{e}_1$")
    report.append("")
    report.append("**4. Field components (tensor uses standardized increments; see §3.2):**")
    report.append("")
    report.append("$$\\mu_{\\mathrm{axis}}^{(j,w)} = \\mathrm{atan2}(e_{1,2}, e_{1,1}) \\quad \\text{(principal axis orientation; sign of } \\mathbf{e}_1 \\text{ arbitrary)}$$")
    report.append("")
    report.append("$$A^{(j,w)} = \\frac{\\lambda_1 - \\lambda_2}{\\lambda_1 + \\lambda_2} \\quad \\text{(anisotropy)}$$")
    report.append("")
    report.append("Optional scalars **not** derived from $\\mathbf{J}$: drift $D(w)$ and tortuosity $\\tau(w)$ use $\\Delta p$ only; angular coherence $R(w)$ uses **original** $\\Delta t$, $\\Delta p$ (see §3.3).")
    report.append("")
    report.append("### 3.2 Methodology")
    report.append("")
    lm = params.get("legacy_mixed_mode", False)
    if not lm:
        report.append(
            "**Transition ontology (default):** The main directional field uses **horizontal** transitions only. "
            "For each MusicXML **voice**, simultaneous noteheads at the same onset `(voice, ql)` are **collapsed** "
            "to a single representative pitch (mean) before forming consecutive **time-ordered** pairs. "
            "Chord-internal moves (vertical / zero-Δt pairs) are **not** mixed into this main field; an auxiliary "
            "vertical table may be computed for diagnostics but is **excluded** from `compute_metrics_from_transitions` "
            "unless you enable a separate analysis path."
        )
    else:
        report.append(
            "**legacy_mixed_mode = True:** Transitions follow the **legacy** global ordering (`transitions_from_events` "
            "on the parsed event list, including optional chord **stagger**). This can chain across voices in time order "
            "and is **not** the default horizontal ontology."
        )
    report.append("")
    report.append(_grace_operational_paragraph(params.get("grace_policy")))
    report.append("")
    report.append(
        "**Tensor increments:** The structure tensor $\\mathbf{J}$ is built from transformed "
        "$(\\Delta t_i, \\Delta p_i)$ according to **`standardization_mode`** "
        f"({params.get('standardization_mode', 'local_zscore')}). "
        "This is **independent** of **scientific mode**, which only toggles **bootstrap confidence intervals** when sample sizes suffice."
    )
    report.append("")
    report.append("With `local_zscore`, within each window:")
    report.append("")
    report.append("$$\\tilde{v}_1 = \\frac{\\Delta t - \\mu_{\\Delta t}}{\\sigma_{\\Delta t}}, \\quad \\tilde{v}_2 = \\frac{\\Delta p - \\mu_{\\Delta p}}{\\sigma_{\\Delta p}}$$")
    report.append("")
    report.append("(Other modes: see `MANUAL_TECNICO.md` §4 — `none`, `robust_scale`, `global_zscore` alias.)")
    report.append("")

    report.append("### 3.3 Metric Definitions")
    report.append("")
    report.append("**Drift (D)** — **not** tensor-based; signed, normalized pitch trend from raw $\\Delta p_i$:")
    report.append("")
    report.append("$$D = \\frac{\\sum_i w_i \\Delta p_i}{\\sum_i w_i |\\Delta p_i|}$$")
    report.append("")
    report.append("Range: [-1, 1]. D > 0: upward drift; D < 0: downward drift.")
    report.append("")
    report.append("**Tortuosity (τ)** — **not** tensor-based; degree of zigzagging in $\\Delta p$:")
    report.append("")
    report.append("$$\\tau = 1 - \\frac{|\\sum_i w_i \\Delta p_i|}{\\sum_i w_i |\\Delta p_i|}$$")
    report.append("")
    report.append("Range: [0, 1]. τ ≈ 0: unidirectional; τ ≈ 1: highly tortuous.")
    report.append("")
    report.append("**Tensor anisotropy (A_tensor)** — from the structure tensor $\\mathbf{J}$ built from **standardized** $(\\Delta t, \\Delta p)$ per `standardization_mode`:")
    report.append("")
    report.append("$$\\mathbf{J} = \\sum_i w_i \\mathbf{v}_i \\mathbf{v}_i^\\top, \\quad \\mathbf{v}_i = (\\tilde{v}_1, \\tilde{v}_2)$$")
    report.append("")
    report.append("$$A_{\\mathrm{tensor}} = \\frac{\\lambda_1 - \\lambda_2}{\\lambda_1 + \\lambda_2}, \\quad \\lambda_1 \\geq \\lambda_2 \\text{ (eigenvalues)}$$")
    report.append("")
    report.append("Range: [0, 1]. A_tensor ≈ 0: isotropy; A_tensor ≈ 1: strong anisotropy.")
    report.append("")
    report.append("**Principal axis orientation (μ_axis)** — direction of the eigenvector for λ₁ (line through the origin); **sign is arbitrary** (\\mathbf{e}_1 \\equiv -\\mathbf{e}_1). Use \\cos\\mu, \\sin\\mu or doubled-angle statistics for aggregation when needed.")
    report.append("")
    report.append("$$\\mu_{\\mathrm{axis}} = \\mathrm{atan2}(e_{1,2}, e_{1,1})$$")
    report.append("")
    report.append("**Angular coherence (R)** — **not** using standardized $\\Delta t$/$\\Delta p$; resultant length of **raw** step directions:")
    report.append("")
    report.append("$$\\theta_i = \\arctan2(\\Delta p_i, \\Delta t_i^\\star) \\text{ with original increments}, \\quad C = \\frac{\\sum w_i \\cos\\theta_i}{\\sum w_i}, \\quad S = \\frac{\\sum w_i \\sin\\theta_i}{\\sum w_i}$$")
    report.append("")
    report.append("$$R = \\sqrt{C^2 + S^2}$$")
    report.append("")
    report.append("Range: [0, 1]. R ≈ 1: coherent direction; R ≈ 0: scattered directions.")
    report.append("")

    report.append("### 3.4 Results (numeric)")
    report.append("")
    for _, row in totals.iterrows():
        scope = row["part"]
        win = row["window"]
        report.append(f"**{scope} — window {win}**")
        report.append("")
        report.append("| Metric | Value | 95% CI |")
        report.append("|--------|-------|--------|")
        a_lo: Optional[float] = row.get("A_tensor_ci_lo")
        a_hi: Optional[float] = row.get("A_tensor_ci_hi")
        a_ci = _fmt_ci(a_lo, a_hi) or "—"
        r_lo: Optional[float] = row.get("R_ci_lo")
        r_hi: Optional[float] = row.get("R_ci_hi")
        r_ci = _fmt_ci(r_lo, r_hi) or "—"
        report.append(f"| D | {_fmt(row['D'])} | — |")
        report.append(f"| τ | {_fmt(row['tau'])} | — |")
        report.append(f"| A_tensor | {_fmt(row['A_tensor'])} | {a_ci} |")
        mu_ax = row.get("mu_axis", row.get("mu"))
        report.append(f"| μ_axis (rad) | {_fmt(mu_ax)} | — |")
        report.append(f"| cos(μ_axis) | {_fmt(row.get('cos_mu'))} | — |")
        report.append(f"| sin(μ_axis) | {_fmt(row.get('sin_mu'))} | — |")
        m2 = row.get("mu_doubled_angle")
        if m2 is not None and not (isinstance(m2, float) and pd.isna(m2)):
            report.append(f"| 2μ_axis (rad) | {_fmt(m2)} | — |")
        report.append(f"| R | {_fmt(row['R'])} | {r_ci} |")
        report.append(f"| n (horizontal transitions in this aggregate) | {int(row['n'])} | — |")
        report.append("")
        report.append(
            "*Legacy column `mu` in machine-readable exports is identical to **μ_axis** (principal axis orientation in radians).*"
        )
        report.append("")
    report.append("")

    # Directional conflict (when available)
    conflict_rows = df_results[df_results["scope"] == "conflito"]
    if not conflict_rows.empty and "conflict" in conflict_rows.columns:
        report.append("### 3.5 Directional conflict between instruments")
        report.append("")
        report.append("$C = (\\sum_j W_j \\cos \\mu_{\\mathrm{axis}}^{(j,w)}) / \\sum_j W_j$, $S = (\\sum_j W_j \\sin \\mu_{\\mathrm{axis}}^{(j,w)}) / \\sum_j W_j$")
        report.append("")
        report.append("$R_{\\mathrm{inst}}(w) = \\sqrt{C^2 + S^2}$, $\\mathrm{Conflito}(w) = 1 - R_{\\mathrm{inst}}(w)$")
        report.append("")
        report.append("| Window | Conflict |")
        report.append("|--------|----------|")
        for _, row in conflict_rows.iterrows():
            c = row.get("conflict")
            report.append(f"| {row['window']} | {_fmt(c)} |")
        report.append("")
        report.append("*High conflict: layers in different directions. Low: coherent global orientation.*")
        report.append("")
    report.append("")

    # --- PEDAGOGICAL SECTION ---
    report.append("---")
    report.append("## 4. Plain-Language Summary (Non-Specialists)")
    report.append("")
    report.append("### What was analysed?")
    report.append("")
    if not params.get("legacy_mixed_mode", False):
        report.append(
            "The software summarises **horizontal** melodic steps (time-ordered, per music notation voice), "
            "with simultaneous chord tones at the same moment collapsed before chaining — **not** arbitrary chains through chord noteheads."
        )
        report.append("")
    report.append("This analysis examines how melody moves in your score. It looks at each step from one note to the next:")
    report.append("- Did the pitch go up or down?")
    report.append("- How much time passed between the notes?")
    report.append("")
    report.append("From these steps, the software computes several indicators that describe the overall **direction** and **shape** of the melodic movement.")
    report.append("")

    report.append("### Key findings (in simple terms)")
    report.append("")
    for _, row in totals.iterrows():
        scope = row["part"]
        D, tau, A, R = row["D"], row["tau"], row["A_tensor"], row["R"]
        report.append(f"**{scope}:**")
        report.append("")
        if pd.notna(D):
            if D > 0.3:
                report.append(f"- **Upward tendency (D = {D:.2f}):** The melody tends to rise more often than it falls.")
            elif D < -0.3:
                report.append(f"- **Downward tendency (D = {D:.2f}):** The melody tends to fall more often than it rises.")
            else:
                report.append(f"- **Balanced movement (D = {D:.2f}):** Ascents and descents are roughly balanced.")
        report.append("")
        if pd.notna(tau):
            if tau < 0.5:
                report.append(f"- **Straight path (τ = {tau:.2f}):** The melodic line follows a relatively clear direction, like a scale.")
            else:
                report.append(f"- **Winding path (τ = {tau:.2f}):** The melodic line zigzags and changes direction often.")
        report.append("")
        if pd.notna(A):
            if A > 0.7:
                report.append(f"- **Strong directionality (A = {A:.2f}):** The movement has a dominant direction.")
            elif A < 0.3:
                report.append(f"- **Diffuse movement (A = {A:.2f}):** The movement spreads in many directions.")
            else:
                report.append(f"- **Moderate directionality (A = {A:.2f}):** The movement has some preferred direction.")
        report.append("")
        if pd.notna(R):
            if R > 0.7:
                report.append(f"- **Coherent flow (R = {R:.2f}):** Steps tend to point in similar directions.")
            elif R < 0.3:
                report.append(f"- **Varied flow (R = {R:.2f}):** Steps point in many different directions.")
            else:
                report.append(f"- **Moderate coherence (R = {R:.2f}):** Some consistency in how the melody moves.")
        report.append("")
    report.append("")

    report.append("### Interpretation guide")
    report.append("")
    report.append("| Indicator | Low value | High value |")
    report.append("|-----------|-----------|------------|")
    report.append("| **Drift (D)** | Descending tendency | Ascending tendency |")
    report.append("| **Tortuosity (τ)** | Straight, unidirectional | Winding, oscillating |")
    report.append("| **Anisotropy (A)** | Movement in all directions | Strong preferred direction |")
    report.append("| **Coherence (R)** | Scattered directions | Aligned directions |")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 5. References")
    report.append("")
    report.extend(format_references_report_markdown())
    report.append("")
    report.append("---")
    report.append("")
    report.append(f"*Report generated by {CANONICAL_TOOL_NAME} (package `{PACKAGE_NAME}`)*")
    report.append("")

    return "\n".join(report)
