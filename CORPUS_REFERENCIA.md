# Corpus de Referência — Validação notacional

**Âmbito:** validação do analisador de **campo direccional notacional** (transições simbólicas MusicXML). **Não** valida áudio, percepção, harmonia ou textura geral.

---

## Estado do benchmark oficial

| Item | Estado |
|------|--------|
| Corpus representativo oficial | **Inexistente** nesta release |
| Manifesto | `corpus/manifest.json` |
| Fixtures sintéticos | 3 entradas (`synthetic_fixture`) |
| Saídas congeladas | `corpus/reference_outputs/*.json` |
| Tabelas | `corpus/tables/benchmark_summary.csv` |

**Não** use `minimal_score.xml` como prova de validação em repertório amplo. É **smoke / referência comportamental** apenas.

---

## 1. minimal_score.xml (SYNTH_MINIMAL_ASCENDING)

**Localização:** `tests/fixtures/minimal_score.xml`  
**Manifest:** `corpus_id` = `SYNTH_MINIMAL_ASCENDING`, `corpus_status` = `synthetic_fixture`, `include_in_official_benchmark` = `false`

Partitura mínima: 4 notas ascendentes (C4–F4), 3 transições horizontais no pipeline por defeito.

**Comportamento esperado (perfil `corpus/benchmark_profile.py`, janela total):**

- \(D > 0\), \(\tau \approx 0\), \(A_{\mathrm{tensor}} \approx 1\), \(R\) alto  
- Valores congelados em `corpus/reference_outputs/SYNTH_MINIMAL_ASCENDING.json`

---

## 2. Outros fixtures sintéticos

| corpus_id | Ficheiro | Uso |
|-----------|----------|-----|
| SYNTH_MINIMAL_TWO_PARTS | `tests/fixtures/minimal_two_parts.xml` | 2A/2B, conflito |
| SYNTH_GRAND_STAFF_TWO_PARTS | `tests/fixtures/grand_staff_two_parts.xml` | parsing grand staff; **sem** métricas congeladas (poucas transições horizontais) |

---

## 3. Roadmap para corpus representativo

1. Adicionar MusicXML com licença verificada (`public_domain_verified`, `openly_licensed`, `owned_by_author`).
2. Preencher metadados no manifesto; `include_in_official_benchmark: true` só com licença documentada.
3. `python corpus/scripts/generate_reference_outputs.py` → commit JSON + `checksums.sha256`.
4. Actualizar `docs/anisotropia_current_rating.md`.

Ver `corpus/README.md` e `docs/anisotropia_90_rubric.md`.

---

## Scripts

```bash
python corpus/scripts/generate_reference_outputs.py
python corpus/scripts/compare_reference_outputs.py
python corpus/scripts/reproduce_tables.py
```
