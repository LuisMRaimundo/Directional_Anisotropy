# Manual de Métricas — Directional_Anisotropy

> **Manual técnico completo (fórmulas, algoritmos, tutorial):** [MANUAL_TECNICO.md](MANUAL_TECNICO.md).  
> **Semântica interpretativa (limites, uso musicológico, tabela de riscos):** [docs/METRIC_SEMANTICS.md](docs/METRIC_SEMANTICS.md).  
> Este ficheiro é um **resumo** para a interface Streamlit. A análise de métricas na app usa **`run_analysis`** (ver MANUAL_TECNICO §12.3).

> **MathJax / Stack Exchange:** blocos de equação em **linhas próprias** com `$$` … `$$`. Evite o delimitador LaTeX “barra + parêntesis recto de abertura” para blocos: em muitos renderizadores Markdown (ex.: Stack Exchange), **`[`** inicia uma hiperligação e a fórmula deixa de ser matemática. Para *inline*, use `$` … `$`.

Este manual descreve o significado das métricas de **Directional_Anisotropy** para um **analisador sistemático de campo direccional notacional**: estrutura direccional em transições $(\Delta t,\,\Delta p)$ extraídas de **dados simbólicos MusicXML**. **Não** é análise de áudio, espectral, psicoacústica, percepção do ouvinte, loudness, timbre, harmonia, função tonal, Schenker, densidade orquestral acústica, ou textura geral. Para limites e distinções interpretativas detalhadas, ver [docs/METRIC_SEMANTICS.md](docs/METRIC_SEMANTICS.md).

---

## 1. Adaptação ao domínio notacional

### Dados notacionais vs. domínios físicos

Os conceitos de anisotropia e tensores provêm de domínios com grandezas físicas contínuas (análise de imagem, petrografia, reologia). Aqui aplicam-se a **dados notacionais discretos**:

| Aspecto | Domínio físico | Domínio notacional |
|---------|----------------|---------------------|
| Dados | Campo contínuo (2D/3D) | Sequência discreta de (onset, pitch) |
| "Gradiente" | Variação local contínua | Transições entre notas consecutivas |
| Unidades | Homogéneas (pixel, mm) | $\Delta t$ (beats/seg) e $\Delta p$ (semitons) — dimensões distintas |

### Padronização (modo científico)

Para tornar $A_{\mathrm{tensor}}$ **independente das escalas** de $\Delta t$ e $\Delta p$ (que têm unidades diferentes), aplica-se **padronização ponderada** dentro de cada janela:

- Cada componente $(\Delta t,\,\Delta p)$ é centrada na média ponderada e dividida pelo desvio-padrão ponderado.
- O tensor $\mathbf{J}$ passa a reflectir a **forma** (correlação/direcção) das transições, não a escala absoluta.
- Isto torna as métricas comparáveis entre excertos com durações e amplitudes melódicas diferentes.
- O modo `global_zscore` na interface é actualmente **alias** de `local_zscore` por janela (não normalização global ao corpus). Ver `MANUAL_TECNICO.md` §4.

### Incerteza (intervalos de confiança)

Quando **modo científico robusto** está activo e há **≥8 transições** na janela, calculam-se IC 95% por **bootstrap** (1000 ressamples) para $A_{\mathrm{tensor}}$ e $R$. Permite avaliar a estabilidade das estimativas.

---

## 2. Conceitos fundamentais

### Transições de altura (pitch)

A análise parte das **transições** entre notas consecutivas: cada transição tem uma variação de altura $\Delta p$ (em semitons, positivo = subida, negativo = descida) e um intervalo temporal $\Delta t$. As métricas caracterizam como estas transições se distribuem no plano (tempo, altura).

### Isotropia vs. anisotropia

- **Isotropia**: As transições de altura distribuem-se de forma semelhante em todas as direcções. Não há direcção privilegiada. Musicalmente: o movimento melódico não segue um padrão direccional claro.
- **Anisotropia**: As transições concentram-se numa direcção dominante. Há um eixo principal de variação. Musicalmente: o movimento melódico tende a seguir uma direcção (subida ou descida) ou um padrão temporal bem definido.

---

## 2. Métricas

### 2.1 D — Drift (deriva)

**Definição**

$$
D = \frac{\sum_i w_i \cdot \Delta p_i}{\sum_i w_i \cdot |\Delta p_i|}
$$

**Intervalo**: -1 a 1

**Interpretação**

- **D > 0**: Tendência média para **subir** em altura. O movimento melódico dominante é ascendente.
- **D < 0**: Tendência média para **descer** em altura. O movimento melódico dominante é descendente.
- **D ≈ 0**: Subidas e descidas equilibradas.

**Notas**

- D é uma média ponderada (normalizada) das variações de altura (contorno melódico; Marvin & Friedman, 1991; ver §7).
- Quanto mais próximo de ±1, mais unidireccional é o movimento.

---

### 2.2 τ (tau) — Tortuosidade

**Definição**

$$
\tau = 1 - \frac{\left|\sum_i w_i \cdot \Delta p_i\right|}{\sum_i w_i \cdot |\Delta p_i|}
$$

**Intervalo**: 0 a 1

**Interpretação**

- **τ ≈ 0**: Movimento em grande parte **unidireccional**. Subidas e descidas não se cancelam; há um sentido claro (como uma escala ou um glissando).
- **τ ≈ 1**: Movimento muito **tortuoso**. Subidas e descidas quase se compensam; a linha melódica oscila sem direcção dominante (ex.: padrões ornamentais, bordões).

**Exemplo**

- Escala cromática ascendente: τ ≈ 0.
- Bordão com pequenas oscilações: τ ≈ 1.

---

### 2.3 $A_{\mathrm{tensor}}$ — Anisotropia do tensor (padronizada)

**Definição**

Construímos um tensor 2×2 no plano (tempo, altura). No **modo científico**, os vectores são padronizados: $\tilde{v}_i = \bigl((\Delta t_i - \bar{\Delta t})/\sigma_{\Delta t},\, (\Delta p_i - \bar{\Delta p})/\sigma_{\Delta p}\bigr)$.

$$
\mathbf{J} = \sum_i w_i \, \tilde{\mathbf{v}}_i \tilde{\mathbf{v}}_i^\top
$$

$$
A_{\text{tensor}} = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2}
$$

**Intervalo**: 0 a 1

**Interpretação**

- **$A_{\mathrm{tensor}} \approx 0$**: **Isotropia notacional**. Transições sem direcção privilegiada.
- **$A_{\mathrm{tensor}} \approx 1$**: **Anisotropia forte**. Movimento melódico com direcção dominante clara.

**Robustez**: A padronização torna $A_{\mathrm{tensor}}$ invariante às escalas de $\Delta t$ e $\Delta p$, adequada para comparação entre excertos.

---

### 2.4 μ (mu) — Orientação principal

**Definição**

$\mu$ é o ângulo (em radianos) do vector próprio principal do tensor $\mathbf{J}$ relativamente ao eixo do tempo ($\Delta t$).

$$
\mu = \arctan2(v_2, v_1)
$$

onde $(v_1, v_2)$ é o vector próprio associado ao maior valor próprio.

**Intervalo**: $-\pi$ a $\pi$ (aprox. $-3{,}14$ a $3{,}14$ radianos)

**Interpretação**

- **$\mu \approx \pi/2$ (≈ 1,57 rad)**: O eixo principal está alinhado com a variação de altura ($\Delta p$). O movimento varia sobretudo em altura, com pouco padrão temporal específico.
- **$\mu \approx 0$**: O eixo principal está alinhado com o tempo. A variação de altura está ligada de forma regular ao tempo (ex.: figurações rítmicas repetidas).
- **$\mu < 0$**: Inclinação no sentido descendente no plano (tempo, altura).
- **$\mu > 0$**: Inclinação no sentido ascendente no plano (tempo, altura).

**Nota**: Em muitas passagens, $\mu$ fica próximo de $\pi/2$ porque a variação de altura tende a dominar face ao tempo.

---

### 2.5 R — Coerência angular

**Definição**

Para cada transição, calcula-se o ângulo $\theta_i = \operatorname{arctan2}(\Delta p_i,\,\Delta t_i)$ e a média circular ponderada no círculo trigonométrico:

$$
C = \frac{\sum_i w_i \cos\theta_i}{\sum_i w_i}, \quad S = \frac{\sum_i w_i \sin\theta_i}{\sum_i w_i}
$$

$$
R = \sqrt{C^2 + S^2}
$$

**Intervalo**: 0 a 1

**Interpretação**

- **R ≈ 1**: As transições apontam numa direcção consistente (alta coerência). O movimento tem uma orientação bem definida.
- **R ≈ 0**: As transições distribuem-se por todas as direcções (baixa coerência). O movimento parece aleatório ou sem direcção preferencial.

**Relação com anisotropia**

- R alto está associado a anisotropia.
- R baixo está associado a isotropia.

---

## 3. Agregações 2A e 2B

### 2A — Média ponderada por instrumento

Calcula-se cada métrica por instrumento e faz-se a **média ponderada** entre instrumentos, usando o peso total (W) de cada um. Dá mais importância a instrumentos com mais transições.

**Uso**: Ver o perfil médio da orquestra/ensemble.

### 2B — Pool global de transições

As transições de todos os instrumentos são reunidas num único conjunto e as métricas são calculadas sobre esse conjunto global.

**Uso**: Ver o perfil global da partitura, tratando o colectivo como um todo.

---

## 4. Escala anisotropia ↔ isotropia

| Extremo | Características | Métricas típicas |
|---------|-----------------|------------------|
| **Isotropia** | Movimento difuso, sem direcção clara; transições em muitas direcções | $A_{\mathrm{tensor}} \approx 0$, $R \approx 0$ |
| **Anisotropia** | Movimento direccional; padrão bem definido; eixo principal dominante | $A_{\mathrm{tensor}} \approx 1$, $R \approx 1$ |

O indicador visual de **Anisotropia / Isotropia** na aplicação usa directamente o valor de $A_{\mathrm{tensor}}$: quanto mais próximo de 1, mais anisotrópico; quanto mais próximo de 0, mais isotrópico.

---

## 5. Referências técnicas

- **Modo científico**: Padronização $(\Delta t,\,\Delta p)$ + bootstrap IC 95% quando $n \geq 8$. Recomendado para rigor.
- **n estável**: Janelas com $n \geq 15$ transições dão estimativas mais estáveis.
- **Pesos**: Cada transição é ponderada pela duração do evento de origem (modo `dur`) ou por $\min(\text{duração},\,\Delta t^{\mathrm{ql}})$ (modo `min`).
- **Janelas**: A análise pode ser feita por:
  - **Compassos**: janelas por medida musical (tamanho e passo em compassos).
  - **Segundos**: janelas por tempo real (tamanho e passo em segundos).
  - **Transições**: janelas por número de transições consecutivas.
  - **Excerto total**: uma única janela com toda a partitura (sem segmentação).
- **Acordes**: Um acorde conta como um único evento; a altura representativa pode ser o centroide, a nota superior ou a nota inferior (configurável).
- **2A com IC**: Quando modo científico e ≥2 instrumentos, o IC 95% para 2A é obtido por bootstrap sobre instrumentos.

---

## 6. Visualizações e indicadores adicionais

### 6.1 Elipses do tensor

Para cada janela (ou instrumento), o tensor $\mathbf{J}$ é representado como elipse: eixo maior $\propto \sqrt{\lambda_1}$, menor $\propto \sqrt{\lambda_2}$, rotação $=\mu$. Quando se dispõe dos autovalores reais (métricas por instrumento), usam-se estes. Para agregados (2A/2B), usa-se forma normalizada:
$$
\lambda_1 = \tfrac{1 + A_{\mathrm{tensor}}}{2},\quad
\lambda_2 = \tfrac{1 - A_{\mathrm{tensor}}}{2}
$$
(traço unitário), preservando a razão de anisotropia. A escala é arbitrária para visualização.

### 6.2 Conflito direccional entre instrumentos

$$
\mathrm{Conflito}(w) = 1 - R_{\mathrm{inst}}(w)
$$
onde $R_{\mathrm{inst}}$ é a resultante circular ponderada das orientações $\mu^{(j,w)}$. Peso $W_{j,w} =$ soma dos pesos das transições do instrumento $j$ na janela $w$. Alto conflito: camadas em direcções diferentes; baixo: orientação global coerente.

**Não confundir com:** dissonância contrapontística, tensão harmónica, densidade textural ou tensão perceptiva — mede apenas o alinhamento de $\mu$ entre partes (ver [docs/METRIC_SEMANTICS.md §9](docs/METRIC_SEMANTICS.md#9-directional-conflict)).

### 6.3 Rose diagram

$\theta_i = \operatorname{arctan2}(\Delta p_i,\,\Delta t_i)$ em coordenadas polares. Picos estreitos $\Rightarrow$ anisotropia forte; distribuição circular $\Rightarrow$ isotropia. Pode ser calculado por janela (ODF por segmento) ou para o excerto total.

---

## 7. Referências bibliográficas

(Sincronizado com `anisotropia/references.py` e `MANUAL_TECNICO.md` §14.)

- **MusicXML (formato de partitura simbólica)**: W3C MusicXML Community Group (2021). MusicXML 4.0. W3C Community Group Specification. — Partes, vozes, onset e semântica do ficheiro de entrada.
- **music21**: Cuthbert, M. S., & Ariza, C. (2010). music21: A Toolkit for Computer-Aided Musicology. *ISMIR 2010*. — Parsing MusicXML e extração de eventos.
- **Contorno melódico / movimento de altura assinado (D, τ)**: Marvin, E. W., & Friedman, L. (1991). Musical contour: A correlation approach. *Music Analysis*, 10(2), 181–204. — Deriva D e tortuosidade τ em transições Δp.
- **Escala robusta (MAD)**: Rousseeuw, P. J., & Croux, C. (1993). Alternatives to the median absolute deviation. *JASA*, 88(424), 1273–1283. — Modo `robust_scale` (mediana ponderada e MAD × 1,4826).
- **Tensor de estrutura / anisotropia**: Bigün, J., & Granlund, G. H. (1987). Optimal orientation detection of linear symmetry. *ICCV*, pp. 433–438. — Tensor **J**, eixo μ, anisotropia \(A_{\mathrm{tensor}}\).
- **Razão de anisotropia (valores próprios)**: Woodcock, N. H. (1977). Specification of fabric shapes using an eigenvalue method. *GSA Bulletin*, 88(8), 1231–1236. — Analogia para \((\lambda_1-\lambda_2)/(\lambda_1+\lambda_2)\).
- **Estatística direccional / resultante circular**: Mardia, K. V., & Jupp, P. E. (2000). *Directional Statistics*. Wiley. — \(R\), média circular de μ (2A), conflito direccional.
- **Intervalos de confiança (bootstrap)**: Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall. — IC 95% por percentis (B=1000, semente 42).
- **DTI (visualização de elipses)**: Basser, P. J., Mattiello, J., & LeBihan, D. (1994). Estimation of the effective self-diffusion tensor from the NMR spin echo. *J. Magn. Reson.*, 103(3), 247–254. — Analogia visual para elipses a partir de λ₁, λ₂.
