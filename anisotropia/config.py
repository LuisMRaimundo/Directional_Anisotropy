"""Analysis configuration for the programmatic notational pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal

WindowMode = Literal["measures", "seconds", "events", "total"]
ChordRep = Literal["centroid", "top", "bottom"]
GracePolicy = Literal["exclude", "include"]
StandardizationMode = Literal["local_zscore", "none", "robust_scale", "global_zscore"]
WeightMode = Literal["dur", "min"]
TimeAxis = Literal["ql", "sec"]
PitchSpace = Literal["sounding", "written"]
UnpitchedPolicy = Literal["map_display", "exclude"]
ChordSimultaneity = Literal["coincident", "stagger"]


class GracePolicyNotImplementedError(NotImplementedError):
    """Raised when grace_policy 'include_attached' is requested."""


def validate_grace_policy(grace_policy: str) -> str:
    gp = str(grace_policy).lower()
    if gp == "include_attached":
        raise GracePolicyNotImplementedError(
            "grace_policy 'include_attached' is not implemented. "
            "Use 'exclude' or 'include'."
        )
    if gp not in ("exclude", "include"):
        raise ValueError(f"Unknown grace_policy: {grace_policy!r}")
    return gp


@dataclass
class AnalysisConfig:
    """
    Parameters for symbolic pitch-time transition analysis.

    ``global_zscore`` is documented as an alias of ``local_zscore`` per window
    (true corpus-global normalization is not implemented in this release).
    """

    chord_rep: ChordRep = "centroid"
    weight_mode: WeightMode = "dur"
    window_mode: WindowMode = "total"
    window_size: float = 4.0
    step: float = 2.0
    standardization_mode: StandardizationMode = "local_zscore"
    bootstrap_ci: bool = True
    grace_policy: GracePolicy = "exclude"
    pitch_space: PitchSpace = "sounding"
    unpitched_policy: UnpitchedPolicy = "map_display"
    chord_simultaneity: ChordSimultaneity = "coincident"
    expand_chord_pitches: bool = True
    split_voices: bool = False
    merge_tied_notes: bool = True
    merge_grand_staff: bool = True
    expand_repeats: bool = False
    legacy_mixed_mode: bool = False
    epsilon_dt: float = 1e-9
    include_vertical_auxiliary: bool = True
    compute_2a: bool = True
    compute_2b: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def effective_time_axis(self, has_seconds: bool) -> TimeAxis:
        if self.window_mode == "total":
            return "sec" if has_seconds else "ql"
        if self.window_mode == "seconds" and not has_seconds:
            return "ql"
        return "ql" if self.window_mode in ("measures", "events", "total") else "sec"


def analysis_config_from_ui(
    *,
    chord_rep: str,
    weight_mode: str,
    window_mode: str,
    window_size: float,
    step: float,
    standardization_mode: str,
    scientific_mode: bool,
    grace_policy: str,
    split_voices: bool,
    expand_chord_pitches: bool,
    chord_simultaneity: str,
    pitch_space: str,
    unpitched_policy: str,
    merge_tied_notes: bool,
    merge_grand_staff: bool,
    expand_repeats: bool,
    legacy_mixed_mode: bool,
    epsilon_dt: float,
    compute_2a: bool = True,
    compute_2b: bool = True,
) -> AnalysisConfig:
    """Build :class:`AnalysisConfig` from Streamlit sidebar values."""
    return AnalysisConfig(
        chord_rep=chord_rep,  # type: ignore[arg-type]
        weight_mode=weight_mode,  # type: ignore[arg-type]
        window_mode=window_mode,  # type: ignore[arg-type]
        window_size=float(window_size),
        step=float(step),
        standardization_mode=standardization_mode,  # type: ignore[arg-type]
        bootstrap_ci=bool(scientific_mode),
        grace_policy=validate_grace_policy(grace_policy),  # type: ignore[arg-type]
        split_voices=split_voices,
        expand_chord_pitches=expand_chord_pitches,
        chord_simultaneity=chord_simultaneity,  # type: ignore[arg-type]
        pitch_space=pitch_space,  # type: ignore[arg-type]
        unpitched_policy=unpitched_policy,  # type: ignore[arg-type]
        merge_tied_notes=merge_tied_notes,
        merge_grand_staff=merge_grand_staff,
        expand_repeats=expand_repeats,
        legacy_mixed_mode=legacy_mixed_mode,
        epsilon_dt=float(epsilon_dt),
        compute_2a=compute_2a,
        compute_2b=compute_2b,
    )
