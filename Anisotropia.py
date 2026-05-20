# Anisotropia.py — Streamlit app: anisotropia notacional a partir de MusicXML

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from anisotropia import run_analysis
from anisotropia.config import GracePolicyNotImplementedError, analysis_config_from_ui
from anisotropia.metrics import N_MIN_STABLE
from anisotropia.windowing import window_sort_key
from anisotropia.report import generate_report
from anisotropia.excel_export import build_anisotropia_excel_bytes
from anisotropia.visualizations import (
    PROFESSIONAL_COLORS,
    flow_map_quiver,
    plot_tensor_ellipses,
    plot_tensor_ellipses_per_instrument,
    plot_rose_diagram,
    plot_time_curves,
    plot_pitch_over_time,
    professional_rc,
)

def _show_matplotlib(fig) -> None:
    """Display matplotlib figures at intrinsic size (avoid full-width stretch in wide layout)."""
    st.pyplot(fig, use_container_width=False)

# --- UI ---
st.set_page_config(page_title="Anisotropia Direcional (MusicXML)", layout="wide")
st.title("Anisotropia direcional em partitura (MusicXML): direção + desvio + tensor")

with st.sidebar:
    st.header("Entrada")
    uploaded = st.file_uploader("Upload MusicXML (.xml/.musicxml/.mxl)", type=["xml", "musicxml", "mxl"])

    st.header("Definições")
    chord_rep = st.selectbox("Representante de altura do acorde", ["centroid", "top", "bottom"], index=0)
    with st.expander("Precisão do parsing MusicXML", expanded=True):
        st.caption(
            "Para **mais eventos**: ligue **Expandir repetições** (se a peça tiver voltas), "
            "desligue **Fundir notas ligadas** (cada cabeça escrita conta), e mantenha "
            "**Todas as alturas dos acordes** ligado."
        )
        st.caption(
            "**Percussão sem altura definida (unpitched):** passa a ser extraída. O valor numérico "
            "usa a **posição na pauta** (display step/octave) como MIDI de referência — não é "
            "necessariamente o mesmo que um mapa GM de bateria."
        )
        st.caption(
            "**Pauta dupla (piano, arpa, etc.):** com **Fundir pautas do mesmo instrumento** "
            "ligado, partes ``…-Staff1`` / ``…-Staff2`` no MusicXML contam como **um** instrumento "
            "(eventos numa só linha temporal). Desligue para tratar cada pauta como série separada."
        )
        grace_policy = st.selectbox(
            "Política de notas de adorno (grace)",
            ["exclude", "include"],
            index=0,
            help="**exclude** (predefinição): não entram no modelo de eventos. **include**: como no XML. "
            "A opção *include_attached* não está implementada nesta versão.",
        )
        split_voices = st.checkbox(
            "Uma linha melódica por voz (MusicXML)",
            value=False,
            help="Separa cada voz da parte em séries distintas (ex.: «Arpa | v1»), em vez de misturar todas numa só linha temporal.",
        )
        expand_chord_pitches = st.checkbox(
            "Todas as alturas dos acordes (nota a nota)",
            value=True,
            help="Cada cabeça de acorde é um evento; **coincident** partilha o mesmo tempo (recomendado). "
            "**stagger** = micro-desfasamento legado (mistura vertical na série temporal).",
        )
        chord_simultaneity = st.selectbox(
            "Simultaneidade no acorde (expandir alturas)",
            ["coincident", "stagger"],
            index=0,
            help="**coincident**: mesmos ql/t para todas as cabeças; o campo direccional principal não usa cadeias falsas no acorde.",
        )
        pitch_space = st.selectbox(
            "Espaço de alturas",
            ["sounding", "written"],
            index=0,
            help="**sounding** (predefinição): altura **real** (transposição de instrumento). **written**: como escrito.",
        )
        unpitched_policy = st.selectbox(
            "Percussão unpitched",
            ["map_display", "exclude"],
            index=0,
            help="**map_display**: MIDI proxy pela posição na pauta. **exclude**: não extrair.",
        )
        merge_tied_notes = st.checkbox(
            "Fundir notas ligadas (tie = uma nota sustida)",
            value=True,
            help="Ligado: uma nota longa ligada conta como **um** evento (recomendado para métricas melódicas). "
            "Desligado: **mais eventos** — cada cabeça de nota no XML, incluindo continuações de ligadura.",
        )
        expand_repeats = st.checkbox(
            "Expandir repetições (voltas, estrutura de repeats)",
            value=False,
            help="Se a peça tiver sinais de repetição que o music21 consiga expandir, duplica essas passagens — "
            "**mais notas** (comprimento tipo audição). Pode não ter efeito em excertos sem repeats.",
        )
        merge_grand_staff = st.checkbox(
            "Fundir pautas do mesmo instrumento (grand staff)",
            value=True,
            help="Junta ``P1-Staff1`` + ``P1-Staff2`` num único instrumento «Nome (P1)». "
            "Desligue se quiser uma série por pauta (comportamento antigo).",
        )
    weight_mode = st.selectbox("Peso por transição", ["dur", "min"], index=0,
                               help="dur = duração do evento de origem; min = min(duração, dt) para não sobrepesar sustains.")
    window_mode = st.selectbox(
        "Janela (w)",
        ["measures", "seconds", "events", "total"],
        format_func=lambda x: {"measures": "compassos", "seconds": "segundos", "events": "transições", "total": "excerto total"}[x],
        index=0
    )

    if window_mode == "total":
        window_size = step = 1
        time_axis = "ql"
    elif window_mode == "measures":
        window_size = st.number_input("Tamanho da janela (nº de compassos)", min_value=1, value=4, step=1)
        step = st.number_input("Passo (nº de compassos)", min_value=1, value=2, step=1)
        time_axis = "ql"
    elif window_mode == "seconds":
        window_size = st.number_input("Tamanho da janela (segundos)", min_value=0.1, value=5.0, step=0.5)
        step = st.number_input("Passo (segundos)", min_value=0.1, value=2.5, step=0.5)
        time_axis = "sec"
    elif window_mode == "events":
        window_size = st.number_input("Tamanho da janela (nº transições)", min_value=1, value=50, step=1)
        step = st.number_input("Passo (nº transições)", min_value=1, value=25, step=1)
        time_axis = "ql"

    st.header("Ontologia das transições (campo direccional principal)")
    epsilon_dt = st.number_input(
        "ε_dt (quarterLength): mínimo |Δt| para transição horizontal",
        min_value=1e-12,
        value=1e-9,
        format="%.2e",
        help="Transições com |Δt| ≤ ε são tratadas como verticais / não entram no campo principal (modo não legado).",
    )
    legacy_mixed_mode = st.checkbox(
        "legacy_mixed_mode (série temporal misturada)",
        value=False,
        help="Comportamento antigo: ordenação global + stagger de acordes. **Desligado** (predefinição): "
        "sucessão melódica por **voz**, acordes coincidentes, campo principal só com Δt>ε.",
    )
    st.header("Robustez científica (anisotropia notacional)")
    standardization_mode = st.selectbox(
        "Padronização do tensor (Δt, Δp)",
        ["local_zscore", "none", "robust_scale", "global_zscore"],
        index=0,
        help="**local_zscore**: média/peso e σ por janela (predefinição). **none**: bruto. **robust_scale**: mediana/MAD. "
        "**global_zscore**: actualmente alias de local (pool global reservado).",
    )
    scientific_mode = st.checkbox(
        "Modo científico robusto (bootstrap IC)",
        value=True,
        help="IC 95% por bootstrap (n≥8 transições; ≥2 instrumentos para 2A). Independente da padronização.",
    )

    st.header("Saídas")
    compute_A = st.checkbox("Calcular agregado 2A (média ponderada por instrumento)", value=True)
    compute_B = st.checkbox("Calcular agregado 2B (pool global de transições)", value=True)

    st.caption("Métricas: D (drift), τ (tortuosidade), A_tensor ((λ1-λ2)/(λ1+λ2)), μ (orientação principal), R (coerência angular).")
    with st.expander("📖 Manual de métricas (ler primeiro)"):
        _manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MANUAL_METRICAS.md")
        try:
            with open(_manual_path, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        except FileNotFoundError:
            st.markdown("Consulte o ficheiro **MANUAL_METRICAS.md** na pasta do projecto.")

if not uploaded:
    st.info("Faça upload de um ficheiro MusicXML para começar.")
    st.stop()

_analysis_cfg = analysis_config_from_ui(
    chord_rep=chord_rep,
    weight_mode=weight_mode,
    window_mode=window_mode,
    window_size=float(window_size),
    step=float(step),
    standardization_mode=standardization_mode,
    scientific_mode=scientific_mode,
    grace_policy=grace_policy,
    split_voices=split_voices,
    expand_chord_pitches=expand_chord_pitches,
    chord_simultaneity=chord_simultaneity,
    pitch_space=pitch_space,
    unpitched_policy=unpitched_policy,
    merge_tied_notes=merge_tied_notes,
    merge_grand_staff=merge_grand_staff,
    expand_repeats=expand_repeats,
    legacy_mixed_mode=legacy_mixed_mode,
    epsilon_dt=float(epsilon_dt),
    compute_2a=compute_A,
    compute_2b=compute_B,
)

try:
    _analysis_result = run_analysis(
        uploaded.getvalue(),
        uploaded.name,
        _analysis_cfg,
    )
except GracePolicyNotImplementedError as e:
    st.error(str(e))
    st.stop()
except ValueError as e:
    st.warning(str(e))
    st.stop()
except Exception as e:
    st.error(f"Falha na análise: {e}")
    st.stop()

df_out = _analysis_result.df_results
events_by_part = _analysis_result.events_by_part
trans_by_part = _analysis_result.trans_by_part
trans_vertical_by_part = _analysis_result.trans_vertical_by_part
trans_by_window = _analysis_result.trans_by_window
has_seconds = _analysis_result.has_seconds
time_axis = _analysis_result.time_axis
ref_part = _analysis_result.ref_part
ontology_meta = _analysis_result.ontology_meta
_summary_counts = dict(_analysis_result.summary_counts)
_repro_meta = dict(_analysis_result.reproducibility)

_n_events_extracted = int(_summary_counts.get("n_note_events_total", 0))
st.sidebar.metric("Eventos extraídos", _n_events_extracted)

for _wmsg in _analysis_result.warnings:
    st.warning(_wmsg)

_flat_export_meta: Dict[str, Any] = {
    "pitch_space": pitch_space,
    "split_by_voice": split_voices,
    "expand_chord_pitches": expand_chord_pitches,
    "grace_policy": grace_policy,
    "unpitched_policy": unpitched_policy,
    "chord_simultaneity": chord_simultaneity,
    "epsilon_dt": float(epsilon_dt),
    "legacy_mixed_mode": legacy_mixed_mode,
    "standardization_mode": standardization_mode,
}
for _pk, _st in ontology_meta.get("parts", {}).items():
    _flat_export_meta[f"n_horizontal_{_pk}"] = _st.get("n_horizontal_main", 0)
    _flat_export_meta[f"n_candidate_{_pk}"] = _st.get("n_horizontal_raw", 0)
    _flat_export_meta[f"n_vertical_{_pk}"] = _st.get("n_vertical", 0)

_t2a = df_out[(df_out["scope"] == "total_2A") & (df_out["part"] == "TOTAL_2A")]
_t2b = df_out[(df_out["scope"] == "total_2B") & (df_out["part"] == "TOTAL_2B")]
_summary_counts["n_TOTAL_2A_by_window"] = _t2a["n"].astype(int).tolist() if not _t2a.empty else []
_summary_counts["n_TOTAL_2B_by_window"] = _t2b["n"].astype(int).tolist() if not _t2b.empty else []

# Generate report (English: technical + pedagogical)
_report_window_mode = {"measures": "measures", "seconds": "seconds", "events": "events", "total": "total excerpt"}
report_params = {
    "chord_rep": chord_rep,
    "weight_mode": weight_mode,
    "window_mode": _report_window_mode.get(window_mode, window_mode),
    "window_size": window_size,
    "step": step,
    "scientific_mode": scientific_mode,
    "grace_policy": grace_policy,
    "split_voices": split_voices,
    "expand_chord_pitches": expand_chord_pitches,
    "chord_simultaneity": chord_simultaneity,
    "pitch_space": pitch_space,
    "unpitched_policy": unpitched_policy,
    "merge_tied_notes": merge_tied_notes,
    "expand_repeats": expand_repeats,
    "epsilon_dt": epsilon_dt,
    "legacy_mixed_mode": legacy_mixed_mode,
    "standardization_mode": standardization_mode,
    "ontology_summary": ontology_meta,
    "voice_aware_transition_construction": True,
    "per_voice_chain_construction": not legacy_mixed_mode,
    "cross_voice_chaining_in_main_field": bool(legacy_mixed_mode),
    "split_by_voice_output_aggregation": split_voices,
    "vertical_auxiliary_built": True,
    "main_field_horizontal_only": not legacy_mixed_mode,
    "summary_counts": _summary_counts,
    **_repro_meta,
}
_flat_export_meta.update(_summary_counts)
_flat_export_meta.update(_repro_meta)
report_text = generate_report(
    filename=uploaded.name,
    df_results=df_out,
    params=report_params,
    n_parts=len(events_by_part),
    n_windows=len(_analysis_result.windows),
    total_transitions=len(trans_by_part[ref_part]) if ref_part else 0,
    summary_counts=_summary_counts,
)

st.subheader("Resultados (tabela)")
st.dataframe(df_out, width="stretch")
if (df_out["n"] < N_MIN_STABLE).any() and (df_out["n"] > 0).any():
    st.caption(f"⚠️ Janelas com n < {N_MIN_STABLE} transições podem ter métricas instáveis. Recomenda-se maior tamanho de janela.")

# =============================================================================
# Secção de análise dos dados — robusta e explicativa
# =============================================================================
st.subheader("📊 Análise dos dados (interpretação detalhada)")
with st.expander("**Validade e robustez dos dados**", expanded=True):
    df_instr_check = df_out[df_out["scope"] == "instrumento"]
    n_unstable = (df_instr_check["n"] > 0) & (df_instr_check["n"] < N_MIN_STABLE)
    n_unstable_count = n_unstable.sum()
    if n_unstable_count > 0:
        st.warning(
            f"**{n_unstable_count} janela(s)/instrumento(s)** têm n < {N_MIN_STABLE} transições. "
            "As métricas podem ser instáveis (sensíveis a outliers). "
            "**Recomendação:** aumente o tamanho da janela ou use o excerto total."
        )
    else:
        st.success(f"Todas as janelas têm n ≥ {N_MIN_STABLE} transições — estimativas consideradas estáveis.")
    total_trans = int(df_out["n"].sum()) if "n" in df_out.columns else 0
    st.markdown(f"- **Total de transições analisadas:** {total_trans}")
    st.markdown(f"- **Instrumentos:** {df_instr_check['part'].nunique() if not df_instr_check.empty else 0}")
    st.markdown(f"- **Janelas de análise:** {df_out['window'].nunique()}")
    if scientific_mode:
        st.markdown("- **Modo científico:** ativo (padronização + IC 95% por bootstrap)")

with st.expander("**Interpretação das métricas (em termos musicais)**", expanded=True):
    st.markdown("""
    | Métrica | Significado musical | Valores típicos |
    |---------|---------------------|-----------------|
    | **D (Drift)** | Tendência média da melodia a subir ou descer. D > 0 = predominância de subidas; D < 0 = descidas. | Escala ascendente: D ≈ 1. Bordão oscilante: D ≈ 0. |
    | **τ (tau)** | Tortuosidade: até que ponto a linha «zigzagueia». τ ≈ 0 = trajectória rectilínea (ex.: escala); τ ≈ 1 = oscilações que se compensam. | Glissando: τ ≈ 0. Ornamentos: τ ≈ 1. |
    | **A_tensor** | **Anisotropia notacional:** concentração do movimento numa direcção. 0 = isotropia (movimento difuso); 1 = anisotropia (direcção dominante). | Textura densa aleatória: A ≈ 0. Melodia clara: A ≈ 0,7–1. |
    | **R** | Coerência angular: as transições apontam na mesma direcção? R ≈ 1 = fluxo orientado; R ≈ 0 = direcções dispersas. | Arpejo ascendente: R alto. Clusters: R baixo. |
    | **μ (mu)** | Orientação principal (radianos): eixo do movimento no plano (tempo, altura). μ ≈ π/2: variação sobretudo em altura. | — |
    """)
    st.caption("Padronização (modo científico) torna A_tensor invariante à escala do excerto — comparável entre obras diferentes.")

with st.expander("**Interpretação por instrumento**", expanded=True):
    df_instr_interp = df_out[df_out["scope"] == "instrumento"]
    if df_instr_interp.empty:
        st.info("Sem dados por instrumento.")
    else:
        win_order_interp = {w: i for i, w in enumerate(sorted(df_out["window"].drop_duplicates().tolist(), key=window_sort_key))}
        for part in df_instr_interp["part"].unique():
            pdf = df_instr_interp[df_instr_interp["part"] == part]
            if pdf.empty:
                continue
            pdf = pdf.sort_values("window", key=lambda x: x.map(win_order_interp))
            row0 = pdf.iloc[0]
            D, tau, A, R = row0.get("D"), row0.get("tau"), row0.get("A_tensor"), row0.get("R")
            n_val = int(row0.get("n", 0))
            text_parts = [f"**{part}** (n={n_val} transições):"]
            if np.isfinite(D):
                if D > 0.3:
                    text_parts.append(f" Tendência **ascendente** (D={D:.2f}).")
                elif D < -0.3:
                    text_parts.append(f" Tendência **descendente** (D={D:.2f}).")
                else:
                    text_parts.append(f" Subidas e descidas **equilibradas** (D={D:.2f}).")
            if np.isfinite(tau):
                if tau < 0.4:
                    text_parts.append(f" Trajectória **relativamente recta** (τ={tau:.2f}).")
                elif tau > 0.6:
                    text_parts.append(f" Trajectória **tortuosa/oscillante** (τ={tau:.2f}).")
                else:
                    text_parts.append(f" Tortuosidade **moderada** (τ={tau:.2f}).")
            if np.isfinite(A):
                if A > 0.6:
                    text_parts.append(f" **Anisotropia forte** (A={A:.2f}) — direcção bem definida.")
                elif A < 0.3:
                    text_parts.append(f" **Isotropia** (A={A:.2f}) — movimento difuso.")
                else:
                    text_parts.append(f" Anisotropia **moderada** (A={A:.2f}).")
            if np.isfinite(R):
                if R > 0.6:
                    text_parts.append(f" Fluxo **coerente** (R={R:.2f}).")
                elif R < 0.4:
                    text_parts.append(f" Fluxo **disperso** (R={R:.2f}).")
                else:
                    text_parts.append(f" Coerência **média** (R={R:.2f}).")
            st.markdown("".join(text_parts))
            if len(pdf) > 1:
                A_range = (pdf["A_tensor"].min(), pdf["A_tensor"].max())
                st.caption(f"Variação de A ao longo do tempo: [{A_range[0]:.2f}, {A_range[1]:.2f}]")

with st.expander("**Comparação 2A vs 2B**", expanded=False):
    totals_ab = df_out[df_out["scope"].isin(["total_2A", "total_2B"])]
    if len(totals_ab["scope"].unique()) < 2:
        st.info("Ative 2A e 2B para comparar.")
    else:
        for win in totals_ab["window"].unique()[:3]:
            wdf = totals_ab[totals_ab["window"] == win]
            a2A = wdf[wdf["scope"] == "total_2A"]["A_tensor"].values
            a2B = wdf[wdf["scope"] == "total_2B"]["A_tensor"].values
            if len(a2A) and len(a2B):
                diff = float(a2A[0] - a2B[0]) if np.isfinite(a2A[0]) and np.isfinite(a2B[0]) else np.nan
                st.markdown(f"**Janela {win}:** 2A = {a2A[0]:.3f}, 2B = {a2B[0]:.3f}")
                if np.isfinite(diff) and abs(diff) > 0.05:
                    st.caption("2A pondera por instrumento; 2B faz pool global. Diferença indica heterogeneidade entre instrumentos.")

with st.expander("**Conflito direccional entre instrumentos**", expanded=False):
    df_cf = df_out[df_out["scope"] == "conflito"]
    if df_cf.empty:
        st.info("Requer ≥2 instrumentos. Conflito = 1 − R_inst (resultante circular das orientações μ).")
    else:
        for _, row in df_cf.head(5).iterrows():
            c = row.get("conflict")
            if np.isfinite(c):
                if c > 0.5:
                    interp = "Camadas em **direcções distintas** — potencial cisalhamento textural."
                elif c < 0.2:
                    interp = "Orientação **global coerente** entre instrumentos."
                else:
                    interp = "Coerência **moderada**."
                st.markdown(f"**{row['window']}:** Conflito = {c:.3f}. {interp}")

with st.expander("**Síntese interpretativa**", expanded=True):
    totals_syn = df_out[df_out["scope"].isin(["total_2A", "total_2B"])]
    if totals_syn.empty:
        st.info("Ative 2A ou 2B para ver a síntese.")
    else:
        row_syn = totals_syn.iloc[0]
        A_syn = float(row_syn.get("A_tensor", np.nan))
        D_syn = float(row_syn.get("D", np.nan))
        R_syn = float(row_syn.get("R", np.nan))
        if np.isfinite(A_syn):
            if A_syn > 0.65:
                st.success(
                    f"**Conclusão:** O excerto apresenta **anisotropia notacional forte** (A_tensor = {A_syn:.2f}). "
                    "O movimento melódico segue uma direcção privilegiada, com estrutura direccional bem definida."
                )
            elif A_syn < 0.35:
                st.info(
                    f"**Conclusão:** O excerto tende para **isotropia** (A_tensor = {A_syn:.2f}). "
                    "O movimento distribui-se em várias direcções sem eixo dominante claro."
                )
            else:
                st.warning(
                    f"**Conclusão:** O excerto mostra **anisotropia moderada** (A_tensor = {A_syn:.2f}). "
                    "Há alguma direcção preferencial, mas não dominante."
                )
        if np.isfinite(D_syn):
            dir_text = "ascendente" if D_syn > 0.2 else "descendente" if D_syn < -0.2 else "equilibrada"
            st.markdown(f"**Deriva (D = {D_syn:.2f}):** Tendência geral **{dir_text}**.")
        if np.isfinite(R_syn):
            st.markdown(f"**Coerência (R = {R_syn:.2f}):** {'Fluxo orientado e consistente.' if R_syn > 0.6 else 'Fluxo variado.' if R_syn < 0.4 else 'Coerência intermédia.'}")

st.subheader("Nível de anisotropia notacional / isotropia")
st.caption("A_tensor (padronizado): 0 = isotrópico, 1 = anisotrópico. IC 95% quando modo científico ativo.")
_totals = df_out[df_out["scope"].isin(["total_2A", "total_2B"])]
if not _totals.empty:
    for _, row in _totals.iterrows():
        a_val = row.get("A_tensor")
        if np.isfinite(a_val):
            a_val = float(np.clip(a_val, 0.0, 1.0))
            a_lo = row.get("A_tensor_ci_lo", np.nan)
            a_hi = row.get("A_tensor_ci_hi", np.nan)
            has_ci = np.isfinite(a_lo) and np.isfinite(a_hi)
            scope_name, win_label = row["part"], row["window"]
            n_val = row.get("n", 0)
            with professional_rc():
                fig_bar = plt.figure(figsize=(7.2, 1.55))
                fig_bar.patch.set_facecolor("#FAFBFC")
                ax_bar = fig_bar.add_subplot(111)
                ax_bar.set_facecolor("#FAFBFC")
                ax_bar.set_xlim(0, 1)
                ax_bar.set_ylim(-0.16, 1.16)
                ax_bar.axis("off")
                ax_bar.add_patch(plt.Rectangle(
                    (0.05, 0.35), 0.9, 0.3,
                    facecolor=PROFESSIONAL_COLORS["track"],
                    edgecolor=PROFESSIONAL_COLORS["border"], linewidth=1.0,
                ))
                if has_ci:
                    a_lo_c, a_hi_c = np.clip(a_lo, 0.0, 1.0), np.clip(a_hi, 0.0, 1.0)
                    ax_bar.add_patch(plt.Rectangle(
                        (0.05 + 0.9 * a_lo_c, 0.31), 0.9 * (a_hi_c - a_lo_c), 0.38,
                        facecolor=PROFESSIONAL_COLORS["fill_ci"], alpha=0.55, edgecolor="none",
                    ))
                ax_bar.add_patch(plt.Rectangle(
                    (0.05, 0.35), 0.9 * a_val, 0.3,
                    facecolor=PROFESSIONAL_COLORS["fill_strong"],
                    edgecolor="#1D4ED8", linewidth=1.15,
                ))
                ax_bar.text(0.02, 0.5, "Isotropia", va="center", ha="left", fontsize=10, fontweight="600", color=PROFESSIONAL_COLORS["ink"])
                ax_bar.text(0.98, 0.5, "Anisotropia", va="center", ha="right", fontsize=10, fontweight="600", color=PROFESSIONAL_COLORS["ink"])
                lbl = f"{scope_name} — {win_label} — A_tensor = {a_val:.3f} (n={n_val})"
                if has_ci:
                    lbl += f" • IC 95%: [{a_lo:.3f}, {a_hi:.3f}]"
                if n_val < N_MIN_STABLE:
                    lbl += " ⚠️ n baixo"
                ax_bar.text(0.5, -0.08, lbl, va="top", ha="center", fontsize=9, color=PROFESSIONAL_COLORS["slate"])
                _show_matplotlib(fig_bar)
                plt.close(fig_bar)
else:
    st.info("Ative 2A e/ou 2B para ver o indicador de anisotropia.")

st.subheader("Curvas (totais)")
totals = df_out[df_out["scope"].isin(["total_2A", "total_2B"])].copy()
if totals.empty:
    st.info("Ative 2A e/ou 2B para ver curvas totais.")
else:
    win_order = {w: i for i, w in enumerate(sorted(df_out["window"].drop_duplicates().tolist(), key=window_sort_key))}
    totals["win_idx"] = totals["window"].map(win_order)
    n_windows = len(win_order)
    _scope_palette = [
        PROFESSIONAL_COLORS["accent_1"],
        PROFESSIONAL_COLORS["accent_2"],
        PROFESSIONAL_COLORS["accent_3"],
        PROFESSIONAL_COLORS["accent_4"],
    ]
    _scopes_order = list(totals["scope"].unique())
    _scope_color = {s: _scope_palette[i % len(_scope_palette)] for i, s in enumerate(_scopes_order)}
    _metric_title = {
        "D": "D (deriva)",
        "tau": "τ (tortuosidade)",
        "A_tensor": "A_tensor",
        "R": "R (coerência angular)",
    }
    for metric in ["D", "tau", "A_tensor", "R"]:
        with professional_rc():
            fig = plt.figure(figsize=(6.5, 3.15))
            fig.patch.set_facecolor("#FAFBFC")
            ax = fig.add_subplot(111)
            ax.set_facecolor("#FFFFFF")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for s in ("left", "bottom"):
                ax.spines[s].set_color(PROFESSIONAL_COLORS["border"])
            ax.tick_params(colors=PROFESSIONAL_COLORS["slate"])
            for scope in _scopes_order:
                col = _scope_color[scope]
                tdf = totals[totals["scope"] == scope].sort_values("win_idx")
                x = tdf["win_idx"].to_numpy()
                y = np.where(np.isfinite(tdf[metric].to_numpy()), tdf[metric].to_numpy(), np.nan)
                if n_windows == 1:
                    if np.isfinite(y[0]):
                        scope_idx = _scopes_order.index(scope)
                        ax.bar(
                            0 + (scope_idx - 0.5) * 0.35, y[0], width=0.34, label=scope,
                            color=col, edgecolor="white", linewidth=0.6,
                        )
                else:
                    ax.plot(x, y, marker="o", label=scope, color=col, linewidth=2.0, markersize=5)
            ax.set_title(_metric_title.get(metric, metric), fontsize=12, fontweight="semibold", color=PROFESSIONAL_COLORS["ink"])
            ax.set_xlabel("Janela (índice)")
            ax.set_ylabel(metric)
            if n_windows == 1:
                ax.set_xticks([0])
                ax.set_xticklabels([list(win_order.keys())[0]])
            leg = ax.legend(loc="best", framealpha=0.96, fontsize=9)
            leg.get_frame().set_edgecolor(PROFESSIONAL_COLORS["border"])
            ax.grid(True, color="#EEF2F7", linestyle="-", linewidth=0.7)
            _show_matplotlib(fig)
            plt.close(fig)
    if n_windows == 1:
        st.caption("⚠️ Apenas uma janela de análise. Para curvas ao longo do tempo, use **passo** menor.")

st.subheader("Pitch ao longo do tempo (por instrumento)")
fig_pitch = plot_pitch_over_time(events_by_part, has_seconds=has_seconds)
_show_matplotlib(fig_pitch)
plt.close(fig_pitch)
st.caption("Uma linha por instrumento. Eixo X: tempo (s ou quarterLength). Eixo Y: nomes de notas (com oitava); posicionamento continua em MIDI. Mostra direcções e oscilações de cada parte.")

st.subheader("Visualizações fortes (estrutura direccional)")
win_order = {w: i for i, w in enumerate(sorted(df_out["window"].drop_duplicates().tolist(), key=window_sort_key))}
df_instr = df_out[df_out["scope"] == "instrumento"]
df_conflict = df_out[df_out["scope"] == "conflito"]
all_win_labels = sorted(win_order.keys(), key=lambda w: win_order[w])
all_part_labels = df_instr["part"].unique().tolist()

with st.expander("⚙️ Controlo: escala e subconjuntos", expanded=False):
    viz_arrow_scale = st.slider("Escala das setas (flow map)", 0.2, 1.2, 0.6, 0.1,
                                help="Comprimento máximo das setas em unidades de célula.")
    viz_max_ellipses = st.slider("Máx. elipses por instrumento", 6, 24, 12, 6)
    viz_max_rose_windows = st.slider("Máx. janelas no Rose", 4, 16, 9, 1)
    viz_windows = st.multiselect("Subconjunto de janelas (vazio = todas)", all_win_labels, default=[],
                                 help="Ordenadas por tempo. Vazio mostra todas.")
    viz_parts = st.multiselect("Subconjunto de instrumentos (vazio = todos)", all_part_labels, default=[],
                               help="Vazio mostra todos.")
    use_viz_windows = sorted(viz_windows, key=lambda w: win_order.get(w, -1)) if viz_windows else None
    use_viz_parts = [p for p in all_part_labels if p in viz_parts] if viz_parts else None

with st.expander("Flow map (quiver), elipses do tensor, Rose, curvas temporais", expanded=True):
    if not df_instr.empty:
        fig_q = flow_map_quiver(df_instr, win_order, arrow_scale=viz_arrow_scale,
                                windows=use_viz_windows, parts=use_viz_parts)
        _show_matplotlib(fig_q)
        plt.close(fig_q)
        st.caption("Interpretação: setas alinhadas → fluxo global; direcções opostas entre instrumentos → cisalhamento textural; setas curtas (A≈0) → regime isotrópico.")
    else:
        st.info("Necessários dados por instrumento para o flow map.")
    if not totals.empty:
        fig_ell = plot_tensor_ellipses(totals, win_order, windows=use_viz_windows)
        _show_matplotlib(fig_ell)
        plt.close(fig_ell)
        st.caption("Elipses do tensor (agregado): eixo maior ∝ √λ₁, menor ∝ √λ₂, rotação = μ. Usa λ reais quando disponíveis.")
    if len(df_instr["part"].unique()) >= 2 and len(win_order) > 1:
        fig_ell_pi = plot_tensor_ellipses_per_instrument(
            df_instr, win_order, max_plots=viz_max_ellipses,
            windows=use_viz_windows, parts=use_viz_parts,
        )
        _show_matplotlib(fig_ell_pi)
        plt.close(fig_ell_pi)
        st.caption("Elipses por instrumento e janela (λ reais de J).")
    rose_per_window = len(trans_by_window) > 1
    if ref_part and (trans_by_part.get(ref_part) is not None or trans_by_window):
        fig_rose = plot_rose_diagram(
            trans_by_part.get(ref_part, pd.DataFrame()),
            time_axis=time_axis,
            per_window=rose_per_window,
            trans_by_window=trans_by_window if rose_per_window else None,
            win_order=win_order,
            max_windows=viz_max_rose_windows,
            windows=use_viz_windows,
        )
        _show_matplotlib(fig_rose)
        plt.close(fig_rose)
        st.caption("Rose: θ = arctan2(Δp, Δt). Picos estreitos → anisotropia forte; circular → isotropia. Por janela quando múltiplas.")
    if not totals.empty and len(win_order) > 1:
        fig_tc = plot_time_curves(totals, win_order, windows=use_viz_windows)
        _show_matplotlib(fig_tc)
        plt.close(fig_tc)
        st.caption("Curvas temporais: A(w), sin μ, cos μ (evita saltos por periodicidade), D(w).")
    if not df_conflict.empty:
        with professional_rc():
            fig_cf = plt.figure(figsize=(6.5, 2.75))
            fig_cf.patch.set_facecolor("#FAFBFC")
            ax = fig_cf.add_subplot(111)
            ax.set_facecolor("#FFFFFF")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for s in ("left", "bottom"):
                ax.spines[s].set_color(PROFESSIONAL_COLORS["border"])
            ax.tick_params(colors=PROFESSIONAL_COLORS["slate"])
            cf_sort = df_conflict.sort_values("window", key=lambda x: x.map(win_order))
            x = np.arange(len(cf_sort))
            ax.plot(
                x, cf_sort["conflict"], "o-",
                color=PROFESSIONAL_COLORS["conflict"], markersize=6.5, linewidth=2.1,
                markeredgecolor="white", markeredgewidth=1.2,
            )
            ax.set_xticks(x)
            ax.set_xticklabels(cf_sort["window"].tolist(), rotation=42, ha="right", fontsize=8)
            ax.set_ylabel("Conflito direccional", fontsize=10)
            ax.set_title(
                "Conflito(w) = 1 − R_inst(w)  ·  alto: camadas em direcções distintas",
                fontsize=11, fontweight="semibold", color=PROFESSIONAL_COLORS["ink"],
            )
            ax.grid(True, color="#EEF2F7", linestyle="-", linewidth=0.7)
            _show_matplotlib(fig_cf)
            plt.close(fig_cf)

st.subheader("Gerar graficos e imagem animada")
OUTPUT_DIR = Path(__file__).resolve().parent / "graficos_gerados"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if st.button("Gerar graficos e animacao (guardar na pasta graficos_gerados)"):
    with st.spinner("A gerar graficos e animacao..."):
        try:
            win_order = {w: i for i, w in enumerate(sorted(df_out["window"].drop_duplicates().tolist(), key=window_sort_key))}
            df_instr_btn = df_out[df_out["scope"] == "instrumento"]
            totals_btn = df_out[df_out["scope"].isin(["total_2A", "total_2B"])]
            dfs_to_concat = [df for df in trans_by_part.values() if df is not None and not df.empty]
            pooled = pd.concat(dfs_to_concat, ignore_index=True) if dfs_to_concat else pd.DataFrame()

            fig_pitch_btn = plot_pitch_over_time(events_by_part, has_seconds=has_seconds)
            fig_pitch_btn.savefig(OUTPUT_DIR / "grafico_pitch_por_tempo.png", dpi=150, bbox_inches="tight")
            plt.close(fig_pitch_btn)
            if not totals_btn.empty:
                fig1 = plot_time_curves(totals_btn, win_order)
                fig1.savefig(OUTPUT_DIR / "grafico_curvas_anisotropia.png", dpi=150, bbox_inches="tight")
                plt.close(fig1)
            if not totals_btn.empty:
                fig2 = plot_tensor_ellipses(totals_btn, win_order)
                fig2.savefig(OUTPUT_DIR / "grafico_elipses_tensor.png", dpi=150, bbox_inches="tight")
                plt.close(fig2)
            if not pooled.empty:
                fig3 = plot_rose_diagram(pooled, time_axis=time_axis)
                fig3.savefig(OUTPUT_DIR / "grafico_rose_isotropia.png", dpi=150, bbox_inches="tight")
                plt.close(fig3)
            if len(df_instr_btn["part"].unique()) >= 2:
                fig4 = plot_tensor_ellipses_per_instrument(df_instr_btn, win_order)
                fig4.savefig(OUTPUT_DIR / "grafico_elipses_por_instrumento.png", dpi=150, bbox_inches="tight")
                plt.close(fig4)
            insts = df_instr_btn["part"].unique().tolist()
            if insts:
                A_by_part = df_instr_btn.groupby("part")["A_tensor"].mean()
                A_vals = [float(A_by_part.get(i, np.nan)) for i in insts]
                A_vals = [0.0 if not np.isfinite(v) else v for v in A_vals]
                with professional_rc():
                    fig5, ax = plt.subplots(figsize=(6.2, 3.0))
                    fig5.patch.set_facecolor("#FAFBFC")
                    ax.set_facecolor("#FFFFFF")
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    for s in ("left", "bottom"):
                        ax.spines[s].set_color(PROFESSIONAL_COLORS["border"])
                    bar_colors = [
                        PROFESSIONAL_COLORS["accent_3"] if a > 0.5 else PROFESSIONAL_COLORS["conflict"] if a < 0.3 else PROFESSIONAL_COLORS["accent_2"]
                        for a in A_vals
                    ]
                    n_by = df_instr_btn.groupby("part")["n"].mean()
                    x_pos = np.arange(len(insts))
                    bars = ax.bar(x_pos, A_vals, color=bar_colors, edgecolor=PROFESSIONAL_COLORS["border"], linewidth=0.8)
                    ax.set_xticks(x_pos)
                    ax.set_xticklabels([f"{p}\n(n≈{int(n_by.get(p, 0))})" for p in insts], fontsize=7.5)
                    for rect, p in zip(bars, insts):
                        h = rect.get_height()
                        ax.annotate(
                            f"{h:.2f}",
                            xy=(rect.get_x() + rect.get_width() / 2, h),
                            xytext=(0, 2),
                            textcoords="offset points",
                            ha="center",
                            va="bottom",
                            fontsize=7,
                            color=PROFESSIONAL_COLORS["slate"],
                        )
                    ax.axhline(0.5, color=PROFESSIONAL_COLORS["muted"], linestyle="--", alpha=0.75, linewidth=1)
                    ax.set_ylabel("A_tensor", fontsize=10)
                    ax.set_title("Anisotropia média por instrumento (campo horizontal)", fontsize=12, fontweight="semibold")
                    ax.set_ylim(0, 1)
                    ax.tick_params(colors=PROFESSIONAL_COLORS["slate"])
                    ax.grid(True, axis="y", color="#EEF2F7", linestyle="-", linewidth=0.7)
                    fig5.savefig(OUTPUT_DIR / "grafico_anisotropia_por_instrumento.png", dpi=150, bbox_inches="tight")
                    plt.close(fig5)
                    fig6, ax6 = plt.subplots(figsize=(6.2, 3.0))
                    fig6.patch.set_facecolor("#FAFBFC")
                    ax6.set_facecolor("#FFFFFF")
                    ax6.spines["top"].set_visible(False)
                    ax6.spines["right"].set_visible(False)
                    for s in ("left", "bottom"):
                        ax6.spines[s].set_color(PROFESSIONAL_COLORS["border"])

                    def anim_fn(i):
                        ax6.clear()
                        ax6.set_facecolor("#FFFFFF")
                        ax6.spines["top"].set_visible(False)
                        ax6.spines["right"].set_visible(False)
                        for s in ("left", "bottom"):
                            ax6.spines[s].set_color(PROFESSIONAL_COLORS["border"])
                        idx = min(i, len(insts))
                        insts_show = insts[:idx] if idx > 0 else []
                        A_show = [A_by_part.get(x, 0) for x in insts_show]
                        A_show = [0.0 if not np.isfinite(v) else v for v in A_show]
                        if insts_show:
                            ax6.bar(insts_show, A_show, color=PROFESSIONAL_COLORS["fill_strong"], alpha=0.88, edgecolor=PROFESSIONAL_COLORS["border"])
                        ax6.set_ylim(0, 1)
                        ax6.set_ylabel("A_tensor")
                        ax6.set_title("Anisotropia por instrumento (animação)", fontsize=11, fontweight="semibold")
                        ax6.grid(True, axis="y", color="#EEF2F7", linestyle="-", linewidth=0.7)
                        ax6.tick_params(colors=PROFESSIONAL_COLORS["slate"])

                    n_win_btn = df_instr_btn["window"].nunique() if "window" in df_instr_btn.columns else 1
                    if n_win_btn > 1 and len(insts) > 1:
                        anim = animation.FuncAnimation(fig6, anim_fn, frames=len(insts) + 1, interval=500, repeat=True)
                        anim.save(OUTPUT_DIR / "animacao_anisotropia.gif", writer="pillow", fps=2)
                    plt.close(fig6)
            xlsx_bytes = build_anisotropia_excel_bytes(
                df_out,
                events_by_part,
                trans_by_part,
                has_seconds=has_seconds,
                analysis_metadata=_flat_export_meta,
            )
            (OUTPUT_DIR / "resultados_anisotropia_direcional.xlsx").write_bytes(xlsx_bytes)
            st.success("Graficos e animacao guardados em: " + str(OUTPUT_DIR))
        except Exception as e:
            st.error(f"Erro ao gerar: {e}")

st.subheader("Exportar")
_excel_bytes = build_anisotropia_excel_bytes(
    df_out,
    events_by_part,
    trans_by_part,
    has_seconds=has_seconds,
    analysis_metadata=_flat_export_meta,
)
col_csv, col_xlsx, col_json, col_report = st.columns(4)
with col_csv:
    st.download_button("Download CSV", data=df_out.to_csv(index=False).encode("utf-8"),
                       file_name="resultados_anisotropia_direcional.csv", mime="text/csv")
with col_xlsx:
    st.download_button(
        "Download Excel (.xlsx)",
        data=_excel_bytes,
        file_name="resultados_anisotropia_direcional.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Inclui tabela completa, métricas por instrumento (mapa de fluxo), totais/conflito, trajetórias (pitch_midi + pitch_note) e transições (note_from / note_to).",
    )
with col_json:
    st.download_button(
        "Download JSON (metadata)",
        data=json.dumps(
            {"parameters": report_params, "flat_counts": _flat_export_meta, "ontology": ontology_meta},
            indent=2,
            default=str,
        ).encode("utf-8"),
        file_name="anisotropia_analysis_metadata.json",
        mime="application/json",
        help="Parâmetros e contagens para fusão downstream.",
    )
with col_report:
    st.download_button("Download Report (English)", data=report_text.encode("utf-8"),
                       file_name="anisotropia_report.md", mime="text/markdown")

st.subheader("Detailed Report (English)")
_report_split = report_text.split("## 4. Plain-Language Summary")
_report_technical = _report_split[0].strip()
_report_pedagogical = ("## 4. Plain-Language Summary" + _report_split[1]).strip() if len(_report_split) > 1 else ""
with st.expander("Technical report (specialists)", expanded=False):
    st.markdown(_report_technical)
with st.expander("Plain-language summary (non-specialists)", expanded=True):
    st.markdown(_report_pedagogical if _report_pedagogical else _report_technical)
