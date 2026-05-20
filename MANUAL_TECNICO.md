# Manual Técnico — Anisotropia Notacional

**Versão:** 2.4.0  
**Data:** Maio 2026  
**Âmbito:** Fórmulas, algoritmos e convenções **exactamente** como implementados em `anisotropia/` (Python 3.10+), mais tutorial operacional. **Este é o único manual técnico do projecto.**

**Ficheiros de referência:** `anisotropia/pipeline.py`, `metrics.py`, `parsing.py`, `transitions.py`, `windowing.py`, `config.py`, `reproducibility.py`, `analysis_warnings.py`, `visualizations.py`, `report.py`, `excel_export.py`, `Anisotropia.py`.

> **MathJax em sites tipo Stack Exchange:** blocos de equação usam **`$$`** em linha própria (não o delimitador LaTeX com parêntesis recto de abertura: o caracter **`[`** é interpretado como início de hiperligação Markdown). *Inline:* preferir **`$`**…**`$`** em cópias para esses sites.

---

## Índice

1. [Resumo e notação](#1-resumo-e-notação)  
2. [Pipeline de dados](#2-pipeline-de-dados)  
   - [2.1 Relatório e metadados de exportação](#21-relatório-e-metadados-de-exportação)  
3. [Eventos, transições e pesos](#3-eventos-transições-e-pesos)  
3b. [Ontologia de transições (horizontal vs vertical)](#3b-ontologia-de-transições-horizontal-vs-vertical)  
4. [Padronização e tensor de estrutura](#4-padronização-e-tensor-de-estrutura)  
5. [Métricas escalares](#5-métricas-escalares-d-τ-a_tensor-μ-r)  
6. [Intervalos de confiança (bootstrap)](#6-intervalos-de-confiança-bootstrap)  
7. [Agregações 2A e 2B](#7-agregações-2a-e-2b)  
8. [Conflito direccional](#8-conflito-direccional)  
9. [Janelamento temporal](#9-janelamento-temporal)  
10. [Visualizações (geometria)](#10-visualizações-geometria)  
11. [Algoritmos (pseudocódigo)](#11-algoritmos-pseudocódigo)  
12. [Tutorial](#12-tutorial)  
13. [Apêndices](#13-apêndices)  
14. [Bibliografia](#14-bibliografia)  

---

## 1. Resumo e notação

### 1.1 Objectivo

O sistema mede **anisotropia notacional** (campo direccional notacional sistemático) em dados **simbólicos MusicXML**: até que ponto as transições \((\Delta t, \Delta p)\) concentram uma **direcção preferencial** no plano tempo–altura, usando um **tensor de estrutura** 2×2 (analogia pedagógica adaptada a dados notacionais discretos) e **estatística circular** para coerência angular.

**Não mede:** áudio, timbre, percepção, função tonal, direcção schenkeriana, progressão harmónica, gramática completa de condução de vozes, densidade orquestral, nem textura geral.

### 1.2 Tabela de símbolos

| Símbolo | Significado |
|--------|-------------|
| \(i\) | Índice de transição dentro de uma janela |
| \(j\) | Índice de instrumento / parte |
| \(w\) | Índice de janela (segmento temporal) |
| \(p\) | Altura em **semitons** (MIDI float) |
| \(\mathrm{ql}\) | Offset em **quarter lengths** (music21) |
| \(t\) | Tempo em **segundos** (quando `secondsMap` existe) |
| \(\Delta p_i\) | \(p_{i+1} - p_i\) na cadeia de eventos colapsados |
| \(\Delta t_i^{\mathrm{ql}}\) | \(\mathrm{ql}_{i+1} - \mathrm{ql}_i\) |
| \(\Delta t_i^{\mathrm{sec}}\) | \(t_{i+1} - t_i\) |
| \(w_i\) | Peso não-negativo da transição \(i\) |
| \(\varepsilon\) | \(10^{-9}\) — constante `EPSILON` no código |
| \(\mathbf{J}\) | Matriz 2×2 simétrica (tensor de estrutura ponderado) |
| \(\lambda_1 \geq \lambda_2\) | Autovalores de \(\mathbf{J}\) |
| \(\mu_{\mathrm{axis}}\) | **Orientação do eixo principal** (radianos), `Metrics.mu_axis`; alias legado `Metrics.mu` |

### 1.3 Distinção crítica (implementação)

- **\(D\)** e **\(\tau\)** usam apenas \(\Delta p_i\) e pesos \(w_i\) (não usam o tensor).  
- **\(\mathbf{J}\)**, **\(A_{\mathrm{tensor}}\)** e **\(\mu_{\mathrm{axis}}\)** usam o par \((v_{1,i}, v_{2,i})\) onde, conforme `standardization_mode` (ver §4), \(v_1, v_2\) são **\(\Delta t\)** e **\(\Delta p\)** *transformados* (z-score local, robusto, ou nenhum).  
- **\(R\)** e os ângulos \(\theta_i\) usam **sempre** os valores **originais** (não padronizados):
  $$
  \theta_i = \operatorname{atan2}(\Delta p_i,\, \Delta t_i^{\star})
  $$
  com \(\Delta t_i^{\star}\) = \(\Delta t_i^{\mathrm{ql}}\) se `time_axis="ql"` e \(\Delta t_i^{\mathrm{sec}}\) se `time_axis="sec"`.  
- O modo **`w_min`** calcula o peso a partir de **duração em ql** e **\(\Delta t^{\mathrm{ql}}\)** apenas (não usa segundos); ver §3.3.

---

## 2. Pipeline de dados

```
MusicXML (bytes)
    → parse_musicxml  →  Dict[parte, List[Event]]
         • opcional: toSoundingPitch() se pitch_space="sounding"
         • ids de <score-part> lidos do XML bruto para fundir grand staff (merge_grand_staff)
    → build_directional_transition_tables (transitions.py)  →  DataFrame horizontal (+ opcional vertical) por parte
         • modo predefinido: sucessão melódica por **voz** MusicXML, com colapso de simultaneidades no mesmo (voz, ql)
         • legacy_mixed_mode=True: recupera o fluxo antigo via transitions_from_events sobre a lista de eventos
    → window_slices_for_part (parte referência)  →  etiquetas de janela
    → por janela: filtrar transições horizontais, compute_metrics_from_transitions
    → opcional: aggregate_2A, aggregate_2B, compute_directional_conflict
    → relatório (generate_report), export Excel/JSON (excel_export), figuras (visualizations)
```

**Caminho programático unificado:** `run_analysis(xml_bytes, filename, AnalysisConfig)` em `anisotropia/pipeline.py` executa o pipeline acima e devolve `AnalysisResult` (tabela, metadados, `config_sha256`, avisos). A app Streamlit chama `run_analysis` para as métricas principais.

A **parte referência** para construir a lista de janelas é a parte com **mais transições** (no conjunto **horizontal**); as outras partes são cortadas às **mesmas** janelas (por medida, tempo ou índice de transição conforme o modo).

**Parsing (`parse_musicxml`):** parâmetros relevantes incluem `grace_policy` (`exclude` predefinido se não se passar outro), `pitch_space` (`sounding` \| `written`), `unpitched_policy` (`map_display` \| `exclude`), `chord_simultaneity` (`coincident` \| `stagger`), `expand_chord_pitches`, `split_voices`, `merge_tied_notes`, `merge_grand_staff`. O campo `exclude_grace` (bool) continua aceite e sobrepõe a política de grace quando fornecido (compatibilidade).

### 2.1 Relatório e metadados de exportação

O relatório Markdown **`generate_report`** (`anisotropia/report.py`) e os metadados planos usados na app (**JSON** / folha **metadata** no Excel, vía `analysis_metadata` em `excel_export`) reflectem a mesma ontologia e parâmetros que o pipeline:

- **Parâmetros explícitos** (entre outros): `legacy_mixed_mode`, `standardization_mode`, `epsilon_dt`, `grace_policy`, `pitch_space`, `unpitched_policy`, `chord_simultaneity`, `expand_chord_pitches`, `merge_tied_notes`, `split_voices`. O texto do relatório separa **intervalos de confiança bootstrap** (`scientific_mode` / bootstrap na métrica) da **padronização do tensor** (`standardization_mode`).
- **Eixo principal:** nas tabelas do relatório a métrica aparece como **μ_axis (rad)**; exportam-se `mu_axis`, `cos_mu`, `sin_mu`, `mu_doubled_angle`. A coluna **`mu`** nos DataFrames de resultados mantém-se como **alias** numérico de \(\mu_{\mathrm{axis}}\) para compatibilidade com código antigo.
- **Voz:** a construção de transições no modo predefinido é **por voz** MusicXML dentro da lista de eventos (§3b). O parâmetro `split_voices` em `parse_musicxml` define se as vozes ficam **fundidas numa única série temporal por parte** (`False`, predefinição) ou se se criam **chaves separadas** por parte e voz (`True`, rótulos `… | v1`, `… | v2`, …). Em ambos os casos o campo `voice` de cada `Event` alimenta as cadeias horizontais. O relatório inclui campos explícitos para evitar ambiguidade, por exemplo: `voice_aware_transition_construction`, `per_voice_chain_construction`, `cross_voice_chaining_in_main_field`, `split_by_voice_output_aggregation` (este último espelha `split_voices` na app).
- **Contagens (`summary_counts`):** distingue-se o número de **eventos-nota** (`n_note_events_total`), totais de transições **horizontais** e **verticais** (esta última, tabela auxiliar quando construída), contagens na **parte referência**, e o **`n`** efectivo nas linhas agregadas **TOTAL_2A** / **TOTAL_2B** (lista por janela quando aplicável). Indica-se também se o **campo principal** da análise é só horizontal (`main_field_horizontal_only`) e se foram construídas transições verticais auxiliares (`vertical_auxiliary_built`).

Estes campos são passados a `generate_report(..., summary_counts=...)` na app e fundidos no dicionário de metadados planos para exportação, de modo que **relatório e ficheiros exportados não contradizem** os rótulos de contagens.

---

## 3. Eventos, transições e pesos

### 3.1 Evento (`Event`)

Cada evento tem, no mínimo, `(t, \mathrm{ql}, \mathrm{dur\_ql}, p, \mathrm{meas})` e adicionalmente:

| Campo | Significado |
|--------|-------------|
| `voice` | Voz MusicXML (inteiro; predefinição 1 se ausente) |
| `is_chord_tone` | `True` se a cabeça provém de acorde expandido com >1 altura |
| `is_unpitched` | `True` para unpitched / percussão tratada como tal |

**Acordes expandidos:** se `expand_chord_pitches=True` e `chord_simultaneity="coincident"` (predefinição), todas as cabeças partilham o **mesmo** \(\mathrm{ql}\) e \(t\) (sem micro-stagger). Se `chord_simultaneity="stagger"`, aplica-se `STAGGER_QL` / `STAGGER_T_SEC` entre cabeças (comportamento legado para métricas que precisam de \(\Delta t > 0\) artificial).

**Colapso na exportação de eventos:** se `expand_chord_pitches=False`, o código colapsa ainda eventos no mesmo \(\mathrm{ql}\) (tolerância `EPSILON`) num único \(p\) médio — ver `_collapse_same_ql` em `parsing.py`.

### 3.2 Transição (definição local no DataFrame)

Para cada par consecutivo \(a \to b\) **na cadeia em que for construída** (ver §3b):

$$
\Delta p = p_b - p_a, \quad
\Delta t^{\mathrm{ql}} = \mathrm{ql}_b - \mathrm{ql}_a, \quad
\Delta t^{\mathrm{sec}} = t_b - t_a
$$

$$
w_i^{\mathrm{dur}} = \max(\mathrm{dur\_ql}(a),\, 0)
$$

$$
w_i^{\mathrm{min}} = \max\Bigl(\min\bigl(\mathrm{dur\_ql}(a),\, \Delta t^{\mathrm{ql}} \text{ se } \Delta t^{\mathrm{ql}}>0 \text{ senão } \mathrm{dur\_ql}(a)\bigr),\, 0\Bigr)
$$

**Nota:** \(w^{\mathrm{min}}\) está definido em **quarter lengths**, independentemente de o eixo temporal da métrica ser `ql` ou `sec`.

### 3.3 Selecção de colunas

- `weight_mode="dur"` → coluna `w_dur`  
- `weight_mode="min"` → coluna `w_min`  
- `time_axis="ql"` → \(\Delta t_i = \Delta t_i^{\mathrm{ql}}\) nas fórmulas do tensor e de \(\theta\)  
- `time_axis="sec"` → \(\Delta t_i = \Delta t_i^{\mathrm{sec}}\)

### 3.4 Filtragem (`compute_metrics_from_transitions`)

1. Remover linhas com `dp` ou \(\Delta t\) não finitos.  
2. Remover linhas com \(\Delta t \leq 0\) (o denominador temporal deve ser estritamente positivo).  
3. Se \(\sum_i w_i \leq 0\), substituir **todos** os pesos por \(1\).

---

## 3b. Ontologia de transições (horizontal vs vertical)

Implementação: `anisotropia/transitions.py` — `build_directional_transition_tables`.

**Modo predefinido (`legacy_mixed_mode=False`):**

1. Agrupar eventos por **voz** MusicXML.  
2. Dentro de cada voz, ordenar por \((\mathrm{ql}, p)\).  
3. **Colapsar** todos os eventos com o **mesmo** \((\mathrm{voice}, \mathrm{ql})\) num único representante: \(p\) = média das alturas, \(\mathrm{dur\_ql}\) = máximo — isto evita cadeias falsas *dentro* do acorde para o campo direccional principal.  
4. Entre representantes consecutivos **no tempo** na mesma voz, formar transições; marcam-se como `transition_kind="horizontal"` quando \(|\Delta t^{\mathrm{ql}}| > \varepsilon_{\mathrm{dt}}\) (parâmetro `epsilon_dt`; por defeito da UI \(10^{-9}\) em ql).  
5. Opcionalmente (`include_vertical_auxiliary=True`): pares ordenados de alturas **no mesmo** \((\mathrm{voice}, \mathrm{ql})\) com \(\Delta t = 0\) — tabela auxiliar para análise de simultaneidade (não misturada no campo principal por defeito).

**Modo legado (`legacy_mixed_mode=True`):**

- Usa `transitions_from_events` sobre a lista de eventos **tal como** devolvida por `parse_musicxml` (inclui ordenação global e, se aplicável, stagger de acordes).  
- As linhas são etiquetadas `legacy_mixed`; a separação horizontal/vertical usa \(\varepsilon_{\mathrm{dt}}\) sobre as colunas `dt_ql` ou `dt_sec` conforme o caso.

**Nota:** `transitions_from_events` permanece em `parsing.py` para compatibilidade e para o modo legado. O fluxo predefinido (Streamlit via `run_analysis` e `legacy_mixed_mode=False`) usa `build_directional_transition_tables`.

---

## 4. Padronização e tensor de estrutura

O parâmetro **`standardization_mode`** (string ou bool legacy) controla a transformação aplicada a \((\Delta t_i, \Delta p_i)\) **antes** de formar \(\mathbf{J}\):

| Modo | Comportamento |
|------|----------------|
| `local_zscore` | Centragem e divisão por \(\sigma\) **ponderados** na janela (equivalente ao antigo `standardize=True`). |
| `none` | Sem transformação: \(\tilde{v}_{k,i} = v_{k,i}\). |
| `robust_scale` | Centragem por **mediana ponderada** e escala tipo MAD (\(\times 1.4826\)) por eixo (Rousseeuw & Croux, 1993; ver §14). |
| `global_zscore` | Actualmente **alias** de `local_zscore` dentro de cada chamada (pool global reservado). **Não** é normalização ao nível do corpus. |

**TODO (futuro):** implementar `global_zscore` verdadeiro com estatísticas fixas por corpus/perfil de benchmark, versionadas em `metric_schema_version`.

Se for passado um **bool**: `True` → `local_zscore`; `False` → `none`.

### 4.1 Médias e variâncias ponderadas (modo `local_zscore`)

Sejam \(v_{1,i} = \Delta t_i\) e \(v_{2,i} = \Delta p_i\) **antes** de padronizar. Com pesos \(w_i\):

$$
\bar{v}_1 = \frac{\sum_i w_i v_{1,i}}{\sum_i w_i}, \qquad
\bar{v}_2 = \frac{\sum_i w_i v_{2,i}}{\sum_i w_i}
$$

$$
\sigma_1 = \sqrt{\frac{\sum_i w_i (v_{1,i} - \bar{v}_1)^2}{\sum_i w_i}}, \qquad
\sigma_2 = \sqrt{\frac{\sum_i w_i (v_{2,i} - \bar{v}_2)^2}{\sum_i w_i}}
$$

$$
\tilde{v}_{1,i} = \frac{v_{1,i} - \bar{v}_1}{\max(\sigma_1,\varepsilon)}, \qquad
\tilde{v}_{2,i} = \frac{v_{2,i} - \bar{v}_2}{\max(\sigma_2,\varepsilon)}
$$

### 4.2 Tensor

$$
\mathbf{J} = \sum_i w_i \begin{bmatrix} \tilde{v}_{1,i}^2 & \tilde{v}_{1,i}\tilde{v}_{2,i} \\ \tilde{v}_{1,i}\tilde{v}_{2,i} & \tilde{v}_{2,i}^2 \end{bmatrix}
$$

### 4.3 Autovalores e vector próprio principal

`numpy.linalg.eigh(J)` devolve autovalores em **ordem crescente**: \(\lambda_{\mathrm{small}} \leq \lambda_{\mathrm{large}}\). O código define:

$$
\lambda_2 := \lambda_{\mathrm{small}}, \qquad \lambda_1 := \lambda_{\mathrm{large}}
$$

Seja \(\mathbf{v} = (v_1, v_2)^\top\) o autovector associado a \(\lambda_1\) (segunda coluna da matriz de autovectores devolvida). Então a **orientação do eixo principal** (radianos) é:

$$
\mu_{\mathrm{axis}} = \operatorname{atan2}(v_2, v_1)
$$

O código exporta também \(\cos\mu_{\mathrm{axis}}\), \(\sin\mu_{\mathrm{axis}}\) e o ângulo duplicado \(2\mu_{\mathrm{axis}}\) (útil para estatística de eixos sem ambiguidade de sinal). **Nota:** \(\mathbf{v}\) e \(-\mathbf{v}\) definem a **mesma recta**; o sinal do autovector é convencional.

O campo `Metrics.mu` coincide com \(\mu_{\mathrm{axis}}\) para compatibilidade com gráficos existentes.

### 4.4 Anisotropia do tensor

Se \(\lambda_1 + \lambda_2 > 0\):

$$
A_{\mathrm{tensor}} = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2} \in [0,1]
$$

Caso contrário \(A_{\mathrm{tensor}} = \mu_{\mathrm{axis}} = \mathrm{NaN}\) (autovalores não informativos).

---

## 5. Métricas escalares: D, τ, A_tensor, μ_axis, R

### 5.1 Drift

$$
D = \frac{\sum_i w_i \Delta p_i}{\sum_i w_i |\Delta p_i|}
$$

com convénção \(D=0\) se o denominador for \(0\). Intervalo típico \([-1,1]\).

### 5.2 Tortuosidade

$$
\tau = 1 - \frac{\bigl|\sum_i w_i \Delta p_i\bigr|}{\sum_i w_i |\Delta p_i|}
$$

depois \(\tau \leftarrow \mathrm{clip}(\tau, 0, 1)\).

**Relação:** \(D\) e \(\tau\) encerram informação complementar sobre o **primeiro momento** de \(\Delta p\) com sinal vs. magnitude.

### 5.3 Coerência angular R

Com \(\theta_i = \operatorname{atan2}(\Delta p_i, \Delta t_i^\star)\) nos valores **não padronizados**:

$$
C = \frac{\sum_i w_i \cos\theta_i}{\sum_i w_i}, \quad
S = \frac{\sum_i w_i \sin\theta_i}{\sum_i w_i}, \quad
R = \sqrt{C^2 + S^2} \in [0,1]
$$

\(R\) é a **norma da média vectorial** no círculo; coincide com a **resultante circular** (Mardia & Jupp, 2000).

---

## 6. Intervalos de confiança (bootstrap)

### 6.1 Por transição (métricas por janela)

Se `bootstrap_ci=True` e \(n \geq 8\) (`N_MIN_BOOTSTRAP`):

- Repetir \(B = 1000\) vezes (`N_BOOTSTRAP`):  
  - amostra com reposição índices \(i \in \{1,\ldots,n\}\);  
  - recalcular \(A_{\mathrm{tensor}}\) e \(R\) no subconjunto reamostrado (com a mesma lógica de padronização dentro da reamostra).  
- IC 95%: percentis **2.5** e **97.5** das listas de valores finitos.  
- **Semente fixa:** `numpy.random.default_rng(42)` para reprodutibilidade.

### 6.2 Agregação 2A (entre instrumentos)

Se `bootstrap_ci=True` e **≥ 2** instrumentos válidos:

- Reamostragem **ao nível dos instrumentos** (com reposição): cada bootstrap escolhe \(J\) instrumentos com reposição e recalcula a média ponderada (§7.1).  
- IC 95% para \(A_{\mathrm{tensor}}\) e \(R\) a partir das \(B\) réplicas.

---

## 7. Agregações 2A e 2B

### 7.1 2A — Média ponderada por instrumento

Para escalares \(X \in \{D, \tau, A_{\mathrm{tensor}}, R\}\):

$$
\bar{X} = \frac{\sum_j W_j X^{(j)}}{\sum_j W_j}
$$

onde \(W_j = \mathrm{weight\_sum}^{(j)}\) (soma dos pesos das transições na janela).

Para **\(\mu_{\mathrm{axis}}^{(j)}\)** (orientação do eixo principal por instrumento na janela) — média **circular** entre instrumentos:

$$
C_\mu = \frac{\sum_j W_j \cos\mu^{(j)}}{\sum_j W_j}, \quad
S_\mu = \frac{\sum_j W_j \sin\mu^{(j)}}{\sum_j W_j}, \quad
\bar{\mu} = \operatorname{atan2}(S_\mu, C_\mu)
$$

### 7.2 2B — Pool global

Concatenam-se verticalmente os DataFrames de transições de todas as partes e aplica-se **uma única** chamada a `compute_metrics_from_transitions` ao conjunto fundido.

---

## 8. Conflito direccional

Para uma janela \(w\), com instrumentos \(j\) com \(\mu^{(j)}\) e pesos \(W_j = \mathrm{weight\_sum}^{(j)}\) finitos:

$$
C_{\mathrm{inst}} = \frac{\sum_j W_j \cos\mu^{(j)}}{\sum_j W_j}, \quad
S_{\mathrm{inst}} = \frac{\sum_j W_j \sin\mu^{(j)}}{\sum_j W_j}
$$

$$
R_{\mathrm{inst}} = \sqrt{C_{\mathrm{inst}}^2 + S_{\mathrm{inst}}^2}, \quad
\mathrm{Conflito}(w) = 1 - R_{\mathrm{inst}}
$$

Interpretação: \(\mathrm{Conflito} \approx 0\) — orientações \(\mu\) alinhadas; \(\approx 1\) — \(\mu\) em direcções opostas ou muito dispersas.

---

## 9. Janelamento temporal

### 9.1 Modos

| Modo | Parâmetros | Conteúdo da janela |
|------|------------|---------------------|
| `total` | — | Todas as transições da parte |
| `measures` | `window_size`, `step` (inteiros) | \(\mathrm{meas} \in [m_0,\, m_0 + \mathrm{size})\) |
| `seconds` | `window_size`, `step` (float) | \(t \in [t_{\mathrm{cur}},\, t_{\mathrm{cur}} + \mathrm{size})\) |
| `events` | `window_size`, `step` (inteiros) | Fatias `iloc[i_0 : i_0 + size)` |

### 9.2 Fallback medidas → segundos

Se **todos** os \(\mathrm{meas}\) na parte forem \(0\), o modo `measures` deixa de ser aplicável e o código continua com a lógica de **`seconds`** sobre a coluna `t`.

### 9.3 Ordenação de etiquetas (`window_sort_key`)

Extrai-se um número para ordenação cronológica a partir do prefixo da etiqueta (`m…`, `t…`, `e…`, ou `total` → 0).

---

## 10. Visualizações (geometria)

### 10.1 Elipses do tensor

Os eixos são normalizados ao quadrado \([0,1]\times[0,1]\) com **margem** (padding) para reduzir clipping visual.

Largura e altura de elipse (exibição):

$$
\mathrm{width} = 2\sqrt{\lambda_1}\, s, \quad \mathrm{height} = 2\sqrt{\lambda_2}\, s
$$

com escala \(s\) arbitrária (`scale` no código). Ângulo de rotação: \(\mu_{\mathrm{axis}}\) em graus.

**Fallback** quando \(\lambda_1,\lambda_2\) não estão disponíveis (alguns agregados):

$$
\lambda_1' = \max\left(\frac{1+A}{2}, 10^{-6}\right), \quad
\lambda_2' = \max\left(\frac{1-A}{2}, 10^{-6}\right)
$$

(traço normalizado; preserva a razão \((\lambda_1-\lambda_2)/(\lambda_1+\lambda_2)\).)

### 10.2 Rose diagram

Histograma polar de \(\theta_i = \operatorname{atan2}(\Delta p_i, \Delta t_i^\star)\) em \(n_{\mathrm{bins}}\) bins em \([-\pi, \pi]\), usando apenas transições com \(\Delta t^\star > 0\) no DataFrame de entrada (campo horizontal por defeito). O título indica **n** = número de transições representadas. Modo por janela: repete-se para cada subconjunto de transições.

### 10.3 Flow map (quiver)

Numa grelha (janela × instrumento): \(U \propto A\cos\mu\), \(V \propto A\sin\mu\); cor mapeada a partir de \(D\) via \((D+1)/2\) quando finito.

### 10.4 Trajectórias pitch–tempo

Por defeito (`melodic_skeleton=True` em `plot_pitch_over_time`), traça-se a **série colapsada por (voz, ql)** (`melodic_skeleton_for_plot` em `transitions.py`), evitando linhas que atravessem cabeças de acorde simultâneas como se fossem arpejo.

---

## 11. Algoritmos (pseudocódigo)

### 11.1 `build_directional_transition_tables(evs, epsilon_dt, legacy_mixed_mode, has_seconds, …)`

```
ENTRADA: lista de Event, epsilon_dt, legacy_mixed_mode booleano
SAÍDA: TransitionBuildResult(horizontal: DataFrame, vertical: DataFrame, stats: dict)

Se legacy_mixed_mode:
    df ← transitions_from_events(evs)
    etiquetar transition_kind = legacy_mixed
    opcionalmente partir horizontal / vertical segundo epsilon_dt nas colunas dt
Senão:
    collapsed ← colapsar mesmos (voice, ql) → representante por voz/tempo
    horizontal ← pares consecutivos no tempo por voz (dt > epsilon_dt após filtro)
    vertical ← pares de alturas no mesmo (voice, ql) se include_vertical_auxiliary
Retornar DataFrames e contagens (n_horizontal_main, n_vertical, …)
```

### 11.2 `compute_metrics_from_transitions(df, time_axis, weight_mode, standardize, bootstrap_ci)`

```
ENTRADA: df, time_axis ∈ {"ql","sec"}, weight_mode ∈ {"dur","min"},
         standardize ∈ {bool, "local_zscore", "none", "robust_scale", "global_zscore"}
SAÍDA: Metrics

1. Filtrar dp, dt_col finitos; manter apenas dt_col > 0.
2. dp ← vetor; dt ← vetor da coluna dt_ql ou dt_sec; w ← w_dur ou w_min.
3. w ← max(w, 0); se sum(w) ≤ 0 então w ← ones.
4. D ← sum(w*dp) / sum(w*|dp|)  (ou 0 se denominador 0)
5. τ ← clip(1 - |sum(w*dp)| / sum(w*|dp|), 0, 1)
6. (A, μ, R, λ1, λ2, cos_μ, sin_μ, 2μ) ← _compute_tensor_and_R_internal(dt, dp, w, standardize)
   // θ e R usam dp e dt ORIGINAIS dentro desta função
7. Se bootstrap_ci e n ≥ 8:
       repetir 1000 vezes:
           idx ← amostra aleatória 1..n com reposição
           calcular A, R no subconjunto idx
       IC_A ← percentis 2.5, 97.5 dos A; idem R
8. Retornar Metrics(...) com mu_axis, cos_mu, sin_mu, mu_doubled_angle preenchidos
```

### 11.3 `_compute_tensor_and_R_internal(dt, dp, w, standardize)`

```
1. Se sum(w) ≤ 0 → retornar oito NaNs.
2. Transformar (dt, dp) segundo standardization_mode (§4).
3. Montar J a partir de (ṽ1, ṽ2); eigh → λ2 ≤ λ1; μ_axis ← atan2 do autovector de λ1.
4. A ← (λ1-λ2)/(λ1+λ2) se λ1+λ2 > 0 senão NaN.
5. cos_mu, sin_mu, mu_doubled_angle a partir de μ_axis.
6. θ_i ← atan2(dp_i, dt_i)  // dp e dt ORIGINAIS (não padronizados)
7. C ← sum(w*cos(θ))/sum(w); S ← idem sin; R ← sqrt(C²+S²)
8. Retornar (A, μ, R, λ1, λ2, cos_mu, sin_mu, mu_doubled_angle)  // μ ≡ μ_axis
```

---

## 12. Tutorial

### 12.1 Pré-requisitos

- Python 3.10+ recomendado (CI usa 3.10).  
- Dependências: ver `requirements.txt` (`streamlit`, `numpy`, `pandas`, `matplotlib`, `music21`, `pytest`).  
- Partitura de teste: `tests/fixtures/minimal_score.xml` ou qualquer `.xml` / `.musicxml` / `.mxl`.

### 12.2 Interface Streamlit (recomendado para exploração)

Na pasta do projecto:

```bash
pip install -r requirements.txt
streamlit run Anisotropia.py
```

1. **Upload** do MusicXML.  
2. Escolher **representante de acorde** (centroid / top / bottom).  
3. Escolher **peso** (`dur` vs `min`) e **modo de janela** (compassos, segundos, transições, excerto total).  
4. Definir **ontologia**: `epsilon_dt`, `legacy_mixed_mode`, `standardization_mode`, políticas de grace / pitch_space / unpitched / simultaneidade de acorde.  
5. Activar **modo científico** para **bootstrap IC** (a padronização do tensor é independente — ver `standardization_mode`).  
6. Ler a tabela de resultados; exportar **CSV**, **Excel** (com folha `metadata` se aplicável), **JSON** de metadados, e **relatório** Markdown (`generate_report` em inglês).

A análise de métricas na UI delega em **`run_analysis`** (ver §12.3).

### 12.3 Caminho programático recomendado (`run_analysis`)

```python
from pathlib import Path
from anisotropia import AnalysisConfig, run_analysis

xml_bytes = Path("ficheiro.xml").read_bytes()
cfg = AnalysisConfig(window_mode="total", bootstrap_ci=False)
result = run_analysis(xml_bytes, "ficheiro.xml", cfg)

print(result.df_results)
print(result.reproducibility["config_sha256"])
for w in result.warnings:
    print("warning:", w)
```

Inclui avisos automáticos (baixo **n**, unpitched com proxy de display-pitch, etc.) e metadados de reprodutibilidade (`input_sha256`, `config_sha256`). `grace_policy="include_attached"` **não** está implementado (erro explícito).

### 12.4 Uso programático de baixo nível (módulos)

```python
from pathlib import Path
from anisotropia.parsing import parse_musicxml
from anisotropia.transitions import build_directional_transition_tables
from anisotropia.metrics import compute_metrics_from_transitions
from anisotropia.windowing import window_slices_for_part

xml_bytes = Path("ficheiro.xml").read_bytes()
events_by_part, has_seconds = parse_musicxml(xml_bytes, "ficheiro.xml", chord_rep="centroid")

# Parte com mais transições como referência para janelas (campo horizontal)
def transitions_map(ebp):
    out = {}
    for k, evs in ebp.items():
        out[k] = build_directional_transition_tables(
            evs,
            epsilon_dt=1e-9,
            legacy_mixed_mode=False,
            has_seconds=has_seconds,
        ).horizontal
    return out

trans = transitions_map(events_by_part)
ref = max(trans.keys(), key=lambda k: len(trans[k]))
windows = window_slices_for_part(trans[ref], "measures", window_size=4.0, step=2.0)

time_axis = "sec" if has_seconds else "ql"
for label, _ in windows[:3]:
    df_w = trans[ref]  # na app: alinhar cortes por medida/tempo/evento como em Anisotropia.py
    m = compute_metrics_from_transitions(
        df_w, time_axis=time_axis, weight_mode="dur",
        standardize="local_zscore", bootstrap_ci=len(df_w) >= 8,
    )
    print(label, m.A_tensor, m.R, m.n)
```

Para relatórios Markdown use **`generate_report`** (não `build_report`):

```python
from anisotropia.report import generate_report
import pandas as pd

text = generate_report(
    filename="exemplo.xml",
    df_results=pd.DataFrame(...),  # colunas como na app (mu_axis, cos_mu, …; mu = alias)
    params={"chord_rep": "centroid", "weight_mode": "dur", "legacy_mixed_mode": False, ...},
    n_parts=len(events_by_part),
    n_windows=5,
    total_transitions=len(trans[ref]),
    summary_counts={...},  # opcional: contagens explícitas como na app (n_note_events_total, …)
)
Path("relatorio.md").write_text(text, encoding="utf-8")
```

### 12.5 Exemplo numérico (mão)

Três transições, pesos \(w_i=1\), \(\Delta p \in \{2,-1,1\}\):

$$
\sum w_i \Delta p_i = 2, \quad \sum w_i |\Delta p_i| = 4
$$

$$
D = \frac{2}{4} = 0.5, \quad \tau = 1 - \frac{|2|}{4} = 0.5
$$

Para \(A_{\mathrm{tensor}}\) e \(\mu\) é necessário o par \((\Delta t_i, \Delta p_i)\) completo e a padronização; o exemplo ilustra apenas **\(D\)** e **\(\tau\)**.

### 12.5 Interpretação rápida

| Métrica | Pergunta que responde |
|---------|------------------------|
| \(D\) | A melodia **tende** a subir ou descer em média? |
| \(\tau\) | A linha **zigzagueia** (cancelamento de subidas/descidas)? |
| \(A_{\mathrm{tensor}}\) | Existe um **eixo dominante** no plano \((\Delta t, \Delta p)\) após padronizar? |
| \(\mu_{\mathrm{axis}}\) | Qual a **orientação do eixo** dominante (recta) no plano \((\Delta t, \Delta p)\) após padronizar? |
| \(R\) | Os ângulos \(\theta_i\) estão **alinhados** (resultante circular forte)? |

### 12.6 Problemas frequentes

| Sintoma | Causa provável |
|--------|----------------|
| Janelas em segundos vazias | Ficheiro sem tempos absolutos fiáveis; usar `ql` ou compassos. |
| \(n\) baixo / IC vazio | Poucas transições na janela; aumentar janela ou usar excerto total. |
| `meas` sempre 0 | Alguns exports MusicXML; janelas por compassos degradam para segundos. |
| Muitas transições com \(\Delta t \approx 0\) / rose “vertical” | Modo legado ou acordes em stagger; usar `coincident` + campo horizontal (`legacy_mixed_mode=False`). |
| Diferença vs. partitura “escrita” | Confirmar `pitch_space` (`sounding` vs `written`). |

---

## 13. Apêndices

### Apêndice A — Constantes (`metrics.py`)

| Nome | Valor |
|------|-------|
| `N_MIN_BOOTSTRAP` | 8 |
| `N_MIN_STABLE` | 15 (recomendação na UI) |
| `N_BOOTSTRAP` | 1000 |
| `EPSILON` | \(10^{-9}\) |

### Apêndice B — Limite de ficheiro

`MAX_FILE_SIZE_BYTES = 50 \times 1024^2` — rejeição explícita acima deste tamanho.

### Apêndice B2 — Micro-tempos (`parsing.py`)

| Nome | Valor típico | Uso |
|------|----------------|-----|
| `STAGGER_QL` | \(10^{-8}\) | Desfase entre cabeças de acorde só em modo `stagger`. |
| `STAGGER_T_SEC` | \(10^{-9}\) | Idem em segundos quando `secondsMap` existe. |
| `EPSILON` | \(10^{-9}\) | Tolerância de igualdade de \(\mathrm{ql}\) e mínimos em denominadores. |

### Apêndice C — Correspondência expressão ↔ código

| Conceito | Local típico |
|----------|----------------|
| \(D\), \(\tau\) | `metrics.py` após filtragem |
| \(\mathbf{J}\), \(\lambda\), \(\mu_{\mathrm{axis}}\), \(A\) | `_compute_tensor_and_R_internal` |
| \(\cos\mu\), \(\sin\mu\), ângulo duplicado | idem, campos `Metrics` |
| \(\theta\), \(R\) | mesma função, usa `np.arctan2(dp, dt)` com **dt/dp originais** |
| Ontologia horizontal / vertical | `transitions.py` — `build_directional_transition_tables` |
| Colapso melódico para gráficos | `melodic_skeleton_for_plot` |
| 2A | `_compute_weighted_aggregate`, `aggregate_2A` |
| 2B | `aggregate_2B` |
| Conflito | `compute_directional_conflict` |
| Metadados exportáveis | `excel_export.build_anisotropia_excel_bytes(..., analysis_metadata=...)` |
| Relatório Markdown, `summary_counts` | `report.generate_report`; ver §2.1 |

### Apêndice D — Documentação complementar

- **`MANUAL_METRICAS.md`** — resumo das métricas para a barra lateral da app Streamlit (não substitui este manual).

---

## 14. Bibliografia

Lista canónica (sincronizada com o relatório gerado e `anisotropia/references.py`):

1. **MusicXML (formato de partitura simbólica)** — W3C MusicXML Community Group (2021). MusicXML 4.0. W3C Community Group Specification.  
   *Uso:* partes, vozes, onset e semântica do ficheiro de entrada.
2. **music21** — Cuthbert, M. S., & Ariza, C. (2010). music21: A Toolkit for Computer-Aided Musicology. *ISMIR 2010*.  
   *Uso:* parsing MusicXML e extração de eventos.
3. **Contorno melódico / movimento de altura assinado (D, τ)** — Marvin, E. W., & Friedman, L. (1991). Musical contour: A correlation approach. *Music Analysis*, 10(2), 181–204.  
   *Uso:* deriva D e tortuosidade τ em transições Δp.
4. **Escala robusta (MAD)** — Rousseeuw, P. J., & Croux, C. (1993). Alternatives to the median absolute deviation. *JASA*, 88(424), 1273–1283.  
   *Uso:* modo `robust_scale` (mediana ponderada e MAD × 1,4826).
5. **Tensor de estrutura / anisotropia** — Bigün, J., & Granlund, G. H. (1987). Optimal orientation detection of linear symmetry. *ICCV*, pp. 433–438.  
   *Uso:* tensor **J**, eixo μ, anisotropia \(A_{\mathrm{tensor}}\).
6. **Razão de anisotropia (valores próprios)** — Woodcock, N. H. (1977). Specification of fabric shapes using an eigenvalue method. *GSA Bulletin*, 88(8), 1231–1236.  
   *Uso:* analogia para \((\lambda_1-\lambda_2)/(\lambda_1+\lambda_2)\).
7. **Estatística direccional / resultante circular** — Mardia, K. V., & Jupp, P. E. (2000). *Directional Statistics*. Wiley.  
   *Uso:* \(R\), média circular de μ (2A), conflito direccional.
8. **Intervalos de confiança (bootstrap)** — Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.  
   *Uso:* IC 95% por percentis (B=1000, semente 42).
9. **DTI (visualização de elipses)** — Basser, P. J., Mattiello, J., & LeBihan, D. (1994). Estimation of the effective self-diffusion tensor from the NMR spin echo. *J. Magn. Reson.*, 103(3), 247–254.  
   *Uso:* analogia visual para elipses a partir de λ₁, λ₂.

---

*Fim do manual. Para alterações de comportamento, consultar sempre os testes em `tests/` (incl. `test_transitions.py`) e as funções referidas nas secções 3b, 4 e 11.*
