"""Hashes and reproducibility metadata for exports and reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from anisotropia import CANONICAL_TOOL_NAME, METRIC_SCHEMA_VERSION, PACKAGE_NAME, __version__
from anisotropia.analysis_warnings import AnalysisWarning, warnings_to_metadata
from anisotropia.config import AnalysisConfig
from anisotropia.metrics import N_BOOTSTRAP, N_MIN_BOOTSTRAP, N_MIN_STABLE

BOOTSTRAP_RANDOM_SEED = 42

_SCOPE_DISCLAIMER = (
    "Measures notational directionality in symbolic pitch-time transitions from MusicXML. "
    "Not audio, perception, harmony, Schenkerian analysis, or general texture analysis."
)
_CORPUS_VALIDATION_NOTE = (
    "Official representative benchmark corpus is not yet established; "
    "synthetic fixtures support behavioural regression only."
)
_GLOBAL_ZSCORE_NOTE = (
    "global_zscore is currently an alias of local_zscore within each metric call; "
    "not corpus-global normalization."
)

# Stable keys for config_sha256 (excludes volatile / input fields).
EFFECTIVE_CONFIG_HASH_KEYS = (
    "chord_rep",
    "weight_mode",
    "time_axis_effective",
    "window_mode",
    "window_size",
    "step",
    "bootstrap_ci",
    "grace_policy",
    "split_voices",
    "expand_chord_pitches",
    "chord_simultaneity",
    "pitch_space",
    "unpitched_policy",
    "merge_tied_notes",
    "merge_grand_staff",
    "expand_repeats",
    "epsilon_dt",
    "legacy_mixed_mode",
    "standardization_mode",
    "include_vertical_auxiliary",
    "compute_2a",
    "compute_2b",
    "N_BOOTSTRAP",
    "bootstrap_random_seed",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_primitive(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_primitive(v) for v in value]
    return str(value)


def effective_config_dict(
    config: AnalysisConfig,
    *,
    time_axis_effective: str,
) -> Dict[str, Any]:
    """Resolved analysis parameters for hashing and metadata."""
    base = config.to_dict()
    payload: Dict[str, Any] = {
        "chord_rep": base["chord_rep"],
        "weight_mode": base["weight_mode"],
        "time_axis_effective": time_axis_effective,
        "window_mode": base["window_mode"],
        "window_size": float(base["window_size"]),
        "step": float(base["step"]),
        "bootstrap_ci": bool(base["bootstrap_ci"]),
        "grace_policy": base["grace_policy"],
        "split_voices": base["split_voices"],
        "expand_chord_pitches": base["expand_chord_pitches"],
        "chord_simultaneity": base["chord_simultaneity"],
        "pitch_space": base["pitch_space"],
        "unpitched_policy": base["unpitched_policy"],
        "merge_tied_notes": base["merge_tied_notes"],
        "merge_grand_staff": base["merge_grand_staff"],
        "expand_repeats": base["expand_repeats"],
        "epsilon_dt": float(base["epsilon_dt"]),
        "legacy_mixed_mode": base["legacy_mixed_mode"],
        "standardization_mode": base["standardization_mode"],
        "include_vertical_auxiliary": base["include_vertical_auxiliary"],
        "compute_2a": base["compute_2a"],
        "compute_2b": base["compute_2b"],
        "N_BOOTSTRAP": N_BOOTSTRAP,
        "bootstrap_random_seed": BOOTSTRAP_RANDOM_SEED,
    }
    return {k: _json_primitive(payload[k]) for k in EFFECTIVE_CONFIG_HASH_KEYS}


def effective_config_dict_from_overrides(overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Build hash payload from UI/override dict (Streamlit path)."""
    mapping = {
        "scientific_mode": "bootstrap_ci",
    }
    raw: Dict[str, Any] = {}
    for key in EFFECTIVE_CONFIG_HASH_KEYS:
        if key in overrides:
            raw[key] = overrides[key]
        elif key == "bootstrap_ci" and "scientific_mode" in overrides:
            raw[key] = overrides["scientific_mode"]
        elif key == "N_BOOTSTRAP":
            raw[key] = N_BOOTSTRAP
        elif key == "bootstrap_random_seed":
            raw[key] = BOOTSTRAP_RANDOM_SEED
    for src, dst in mapping.items():
        if src in overrides and dst not in raw:
            raw[dst] = overrides[src]
    missing = [k for k in EFFECTIVE_CONFIG_HASH_KEYS if k not in raw]
    if missing:
        raise ValueError(f"Cannot hash incomplete config; missing keys: {missing}")
    return {k: _json_primitive(raw[k]) for k in EFFECTIVE_CONFIG_HASH_KEYS}


def config_hash_from_dict(payload: Dict[str, Any]) -> str:
    ordered = {k: _json_primitive(payload[k]) for k in sorted(payload.keys())}
    canonical = json.dumps(ordered, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def config_hash(config: AnalysisConfig, *, time_axis_effective: str) -> str:
    return config_hash_from_dict(effective_config_dict(config, time_axis_effective=time_axis_effective))


def _base_metadata(
    *,
    filename: str,
    xml_bytes: bytes,
    config_sha256: str,
    corpus_id: Optional[str],
) -> Dict[str, Any]:
    return {
        "canonical_tool_name": CANONICAL_TOOL_NAME,
        "package_name": PACKAGE_NAME,
        "software_version": __version__,
        "metric_schema_version": METRIC_SCHEMA_VERSION,
        "analyzer_identity": "Directional_Anisotropy — systematic notational directional-field analyzer",
        "input_filename": filename,
        "input_sha256": sha256_bytes(xml_bytes),
        "config_sha256": config_sha256,
        "corpus_id": corpus_id,
        "global_zscore_note": _GLOBAL_ZSCORE_NOTE,
        "grace_include_attached_implemented": False,
        "N_BOOTSTRAP": N_BOOTSTRAP,
        "N_MIN_BOOTSTRAP": N_MIN_BOOTSTRAP,
        "N_MIN_STABLE": N_MIN_STABLE,
        "bootstrap_random_seed": BOOTSTRAP_RANDOM_SEED,
        "bootstrap_unit": "transition (not hierarchical score unit)",
        "transition_ontology_main_field": "horizontal",
        "scope_disclaimer": _SCOPE_DISCLAIMER,
        "corpus_validation_note": _CORPUS_VALIDATION_NOTE,
    }


def _metadata_from_config(config: AnalysisConfig, *, time_axis_effective: str) -> Dict[str, Any]:
    eff = effective_config_dict(config, time_axis_effective=time_axis_effective)
    return {
        **eff,
        "standardization_mode": config.standardization_mode,
        "vertical_auxiliary_built": config.include_vertical_auxiliary,
        "main_field_horizontal_only": not config.legacy_mixed_mode,
        "voice_aware_transition_construction": True,
        "per_voice_chain_construction": not config.legacy_mixed_mode,
        "cross_voice_chaining_in_main_field": bool(config.legacy_mixed_mode),
    }


def build_reproducibility_metadata(
    *,
    filename: str,
    xml_bytes: bytes,
    config: AnalysisConfig | None = None,
    corpus_id: Optional[str] = None,
    ontology_summary: Optional[Dict[str, Any]] = None,
    parameter_overrides: Optional[Dict[str, Any]] = None,
    time_axis_effective: Optional[str] = None,
    analysis_warnings: Optional[List[AnalysisWarning]] = None,
) -> Dict[str, Any]:
    """
    Flat metadata dict for reports, JSON, and Excel metadata sheet.

    ``config_sha256`` is always computed from the effective analysis configuration.
    """
    if config is not None:
        axis = time_axis_effective or config.effective_time_axis(True)
        cfg_hash = config_hash(config, time_axis_effective=axis)
    elif parameter_overrides and time_axis_effective is not None:
        overrides = {**parameter_overrides, "time_axis_effective": time_axis_effective}
        if "bootstrap_ci" not in overrides and "scientific_mode" in overrides:
            overrides["bootstrap_ci"] = overrides["scientific_mode"]
        cfg_hash = config_hash_from_dict(effective_config_dict_from_overrides(overrides))
        axis = time_axis_effective
    else:
        raise ValueError("build_reproducibility_metadata requires config or parameter_overrides+time_axis_effective")

    meta = _base_metadata(filename=filename, xml_bytes=xml_bytes, config_sha256=cfg_hash, corpus_id=corpus_id)
    if config is not None:
        meta.update(_metadata_from_config(config, time_axis_effective=axis))
    elif parameter_overrides:
        meta.update(parameter_overrides)
        meta["time_axis_effective"] = axis
    if analysis_warnings:
        meta.update(warnings_to_metadata(analysis_warnings))
    else:
        meta.setdefault("warnings", [])
        meta.setdefault("warnings_structured", [])
    if ontology_summary:
        meta["ontology_summary"] = ontology_summary
    return meta
