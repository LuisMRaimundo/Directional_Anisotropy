# Benchmark intake (official corpus)

**Directional_Anisotropy** is a systematic notational directional-field analyzer. Official benchmarks must be **licensed or owned** MusicXML — never synthetic-only fixtures.

## Required manifest fields

| Field | Description |
|-------|-------------|
| `corpus_id` | Stable identifier (e.g. `PD_BACH_BWV1001_M1`) |
| `file_path` | Path under `corpus/intake/` or `tests/fixtures/` |
| `format` | `musicxml` \| `mxl` \| `xml` |
| `corpus_status` | See allowed values below |
| `composer` | Composer name or `unknown` |
| `work_title` | Work title |
| `excerpt_label` | e.g. `mm.1-32` |
| `instrumentation` | Short description |
| `measure_range` | e.g. `1-32` |
| `source` | Provenance (edition, repository URL) |
| `license_status` | Legal status |
| `license_note` | Citation / verification note |
| `limitations` | Analytic caveats |
| `include_in_official_benchmark` | `true` only when license verified |

## Allowed `corpus_status` for official benchmark

- `owned_by_author`
- `public_domain_verified`
- `openly_licensed`

**Excluded from official benchmark:**

- `synthetic_fixture`
- `unknown_license_excluded`
- `repository_example` (unless license verified)

## Intake workflow

1. Place MusicXML in `corpus/intake/` (create subfolders as needed).
2. Add entry to `corpus/manifest.json`.
3. Run `python corpus/scripts/generate_reference_outputs.py`.
4. Commit JSON + `checksums.sha256`.
5. Update `docs/anisotropia_current_rating.md`.

Do **not** mark `minimal_score.xml` or other synthetic files as representative corpus.
