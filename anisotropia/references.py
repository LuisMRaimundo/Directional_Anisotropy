"""Bibliografia alinhada com métodos implementados (ver ``MANUAL_TECNICO.md`` §14)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Reference:
    """Uma entrada bibliográfica com rótulo bilingue."""

    label_en: str
    label_pt: str
    citation: str
    usage_pt: str


# Ordem: do parsing às métricas escalares, tensor, estatística, visualização, software.
REFERENCES: tuple[Reference, ...] = (
    Reference(
        label_en="MusicXML (symbolic score format)",
        label_pt="MusicXML (formato de partitura simbólica)",
        citation=(
            "W3C MusicXML Community Group (2021). MusicXML 4.0. "
            "W3C Community Group Specification."
        ),
        usage_pt="Partes, vozes, onset e semântica do ficheiro de entrada.",
    ),
    Reference(
        label_en="music21",
        label_pt="music21",
        citation=(
            "Cuthbert, M. S., & Ariza, C. (2010). music21: A Toolkit for "
            "Computer-Aided Musicology. *ISMIR 2010*."
        ),
        usage_pt="Parsing MusicXML e extração de eventos.",
    ),
    Reference(
        label_en="Melodic contour / signed pitch motion (D, τ)",
        label_pt="Contorno melódico / movimento de altura assinado (D, τ)",
        citation=(
            "Marvin, E. W., & Friedman, L. (1991). Musical contour: "
            "A correlation approach. *Music Analysis*, 10(2), 181–204."
        ),
        usage_pt=(
            "Deriva D e tortuosidade τ como estatísticas de contorno "
            "em transições Δp."
        ),
    ),
    Reference(
        label_en="Robust scale (MAD)",
        label_pt="Escala robusta (MAD)",
        citation=(
            "Rousseeuw, P. J., & Croux, C. (1993). Alternatives to the "
            "median absolute deviation. *Journal of the American Statistical "
            "Association*, 88(424), 1273–1283."
        ),
        usage_pt="Modo ``robust_scale``: mediana ponderada e MAD × 1,4826.",
    ),
    Reference(
        label_en="Structure tensor / anisotropy",
        label_pt="Tensor de estrutura / anisotropia",
        citation=(
            "Bigün, J., & Granlund, G. H. (1987). Optimal orientation "
            "detection of linear symmetry. *First International Conference "
            "on Computer Vision*, pp. 433–438."
        ),
        usage_pt="Tensor J, eixo μ, anisotropia A_tensor.",
    ),
    Reference(
        label_en="Anisotropy ratio (eigenvalues)",
        label_pt="Razão de anisotropia (valores próprios)",
        citation=(
            "Woodcock, N. H. (1977). Specification of fabric shapes using "
            "an eigenvalue method. *GSA Bulletin*, 88(8), 1231–1236."
        ),
        usage_pt="Analogia para (λ₁−λ₂)/(λ₁+λ₂).",
    ),
    Reference(
        label_en="Directional statistics / circular resultant",
        label_pt="Estatística direccional / resultante circular",
        citation=(
            "Mardia, K. V., & Jupp, P. E. (2000). *Directional Statistics*. "
            "Wiley."
        ),
        usage_pt="R, média circular de μ (2A), conflito direccional.",
    ),
    Reference(
        label_en="Bootstrap confidence intervals",
        label_pt="Intervalos de confiança (bootstrap)",
        citation=(
            "Efron, B., & Tibshirani, R. J. (1993). "
            "*An Introduction to the Bootstrap*. Chapman & Hall."
        ),
        usage_pt="IC 95% por percentis (B=1000, semente 42).",
    ),
    Reference(
        label_en="Diffusion tensor imaging (ellipse display)",
        label_pt="DTI (visualização de elipses)",
        citation=(
            "Basser, P. J., Mattiello, J., & LeBihan, D. (1994). Estimation "
            "of the effective self-diffusion tensor from the NMR spin echo. "
            "*Journal of Magnetic Resonance*, 103(3), 247–254."
        ),
        usage_pt="Analogia visual para elipses a partir de λ₁, λ₂.",
    ),
)


def format_references_report_markdown() -> List[str]:
    """Linhas Markdown (inglês) para a secção References do relatório."""
    lines: List[str] = []
    for ref in REFERENCES:
        lines.append(f"- **{ref.label_en}:** {ref.citation}")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def format_references_manual_tecnico() -> List[str]:
    """Lista numerada para ``MANUAL_TECNICO.md`` §14 (sincronização manual de docs)."""
    return [
        f"{i}. **{ref.label_pt}** — {ref.citation}  \n   *Uso:* {ref.usage_pt}"
        for i, ref in enumerate(REFERENCES, start=1)
    ]


def format_references_manual_metricas() -> List[str]:
    """Lista com travessão para ``MANUAL_METRICAS.md`` §7."""
    return [
        f"- **{ref.label_pt}**: {ref.citation} — {ref.usage_pt}"
        for ref in REFERENCES
    ]
