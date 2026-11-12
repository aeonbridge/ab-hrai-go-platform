# 3. Semântica de domínio

Este é o núcleo do sistema. Os valores controlados da ontologia HRAI-GO têm assinatura
visual fixa, definida em `tokens/domain.tokens.json`.

## 3.1 Como uma assinatura é composta

Cada valor tem até quatro portadores de significado, sempre nesta ordem de força:

1. **Rótulo** (`label.pt-BR`): sempre presente e sempre visível. É o portador primário.
2. **Ícone** (Lucide): distinto dentro do grupo, para não depender de cor.
3. **Traço** (`stroke`): `solid`, `dashed`, `dotted` ou `double`. Separa as famílias em
   escala de cinza.
4. **Tom** (`tone`): resolve para `color.tone.<tom>.*` no tema ativo. Reforça, nunca carrega
   sozinho.

Um componente consome o token assim:

```
estado = domain.obligationStatus.insufficientEvidence
cor do texto = color.tone[estado.tone].fg         → ochre.700 (claro) / ochre.200 (escuro)
fundo        = color.tone[estado.tone].bg
borda        = color.tone[estado.tone].border  + border-style: estado.stroke
ícone        = estado.$extensions.org.hraigo.icon   → lucide:triangle-alert
rótulo       = estado.$extensions.org.hraigo.label["pt-BR"]  → "Evidência insuficiente"
```

**Teste do cinza:** com a tela em escala de cinza (filtro `grayscale(1)`), todo estado
continua identificável. Esse teste faz parte do aceite (`checklists/aceite.md`).

## 3.2 Tipo epistêmico (`epistemicKind`)

São os seis objetos que a spec (§1) proíbe misturar. Toda afirmação na tela tem exatamente
um.

| Valor | Rótulo | Ícone | Traço | Tom |
|---|---|---|---|---|
| `officialLegalText` | Texto jurídico oficial | `scale` | sólido | civic |
| `legalInterpretation` | Interpretação jurídica | `message-square-quote` | pontilhado | civic |
| `empiricalEvidence` | Evidência empírica | `microscope` | sólido | lagoon |
| `agentHypothesis` | Hipótese de agente | `circle-help` | pontilhado | iris |
| `stakeholderPosition` | Posição de stakeholder | `megaphone` | sólido | ochre |
| `normativeProposal` | Proposta normativa | `file-pen-line` | tracejado | iris |

Regras:

- **Família normativa (civic):** só o texto oficial tem traço sólido. A interpretação usa a
  mesma cor com traço pontilhado, porque deriva do texto mas pode ser contestada.
- **Família propositiva (iris):** a hipótese e a proposta usam traços diferentes do sólido.
  Nada em iris é vinculante.
- Conversão entre tipos só ocorre por ação humana registrada, por exemplo uma interpretação
  oficial publicada por um `VerifiedStakeholder`. A interface mostra a linhagem ("derivado
  de hipótese de agente, revisado por…").

## 3.3 Vinculação (`bindingness`)

Este é o critério de aceite §15.3 da spec: *nenhuma proposição pendente é apresentada como
obrigação legal vigente*. Toda linha de requisito no VERIFY leva um destes marcadores ao
lado do estado:

| Valor | Rótulo | Ícone |
|---|---|---|
| `binding` | Vinculante na data | `lock` |
| `deferred` | Em vigor · aplicação diferida | `calendar-clock` |
| `nonBinding` | Não vinculante | `lock-open` |

Linhas `nonBinding` (por exemplo, requisitos derivados do PL 2338/2023) ficam num
**grupo separado** ("Referências a propostas · não entram na conclusão"), recolhido por
padrão e fora dos totais.

## 3.4 Estado normativo (`normativeState`)

São os dez estados da spec §6.3. **`InForce` não é sinônimo de `Applicable`.**

| Valor | Rótulo | Ícone | Traço | Tom |
|---|---|---|---|---|
| `proposed` | Proposta | `file-pen-line` | tracejado | iris |
| `underDeliberation` | Em tramitação | `messages-square` | tracejado | iris |
| `approved` | Aprovada · não promulgada | `file-check-2` | sólido | iris |
| `enacted` | Promulgada | `stamp` | tracejado | civic |
| `inForce` | Em vigor | `scale` | sólido | civic |
| `applicable` | Aplicável | `gavel` | duplo | civic |
| `suspended` | Suspensa | `circle-pause` | sólido | ochre |
| `repealed` | Revogada | `archive-x` | sólido | neutral |
| `superseded` | Substituída | `history` | sólido | neutral |
| `uncertain` | Situação incerta | `circle-help` | pontilhado | ochre |

A progressão de traço também codifica força jurídica: tracejado (ainda não obriga), sólido
(em vigor) e duplo (aplicável ao caso). `approved` continua em iris porque aprovação numa
casa não é lei (spec §6.3). Num texto em vigor com obrigações de aplicação diferida, o
`VersionTimeline` mostra **dois marcos**: vigência e aplicação.

## 3.5 Estado de obrigação (`obligationStatus`)

São os seis valores da spec §7.3, por obrigação e por aplicação.

| Valor | Rótulo | Ícone | Traço | Tom |
|---|---|---|---|---|
| `satisfied` | Atendida | `circle-check` | sólido | verdant |
| `notSatisfied` | Não atendida | `circle-x` | sólido | crimson |
| `insufficientEvidence` | Evidência insuficiente | `triangle-alert` | sólido | ochre |
| `notApplicable` | Não aplicável | `circle-minus` | sólido | neutral |
| `legalUncertainty` | Incerteza jurídica | `circle-help` | pontilhado | iris |
| `pendingReview` | Aguardando revisão | `hourglass` | tracejado | civic |

Regras:

- **`insufficientEvidence` não se resume a "vermelho" nem a "verde".** Em totais e gráficos,
  ele tem barra própria e nunca entra no mesmo agregado de `notSatisfied` (spec §13.1:
  "não presume ilicitude nem conformidade").
- `pendingReview` é um resultado automatizado ainda não validado. Ele aparece com o mesmo
  peso visual dos outros e com o aviso "resultado automatizado". Não é exibido como
  conclusão.
- Um resumo de avaliação nunca é um único selo ("Conforme ✓"). É sempre a distribuição dos
  seis estados, mais o `LegalSnapshot` e a data.
- Verde contra vermelho é o par mais frágil para daltonismo. A distinção entre os dois é
  garantida pelo ícone (check × x) e pelo rótulo, nunca pela cor.

## 3.6 Revisão (`reviewStatus`)

`pending` · `reviewed` · `contested` · `corrected` · `invalidated`. O versionamento da spec
§10 é imutável: um objeto corrigido ou invalidado continua acessível, riscado, com link para
a versão vigente. Uma contestação **não apaga** o registro anterior (§15.3).

## 3.7 Sintético e fictício (`synthetic`)

| Valor | Rótulo | Renderização |
|---|---|---|
| `syntheticPerspective` | Perspectiva sintética | Borda tracejada neutra, ícone `bot` e o rótulo, mais o número de fontes ("baseada em 4 fontes") |
| `fictionalExample` | Exemplo fictício · dados simulados | Fundo hachurado (`color.simulation.*`, listras a 45° com período de 6px) e faixa de rótulo no topo |

Proibição metodológica (spec §10.5): uma perspectiva sintética **nunca** usa a assinatura de
`voice.officialInstitution`, nunca usa foto ou avatar de pessoa (só o ícone do estrato) e
nunca omite o rótulo. Essa marca não tem prop para desligar.

## 3.8 Voz e autoridade

São dois eixos independentes.

**Voz (`voice`)** indica quem fala: `officialInstitution` (Posição institucional oficial,
`landmark`), `individual` (Fala individual, `user-round`), `platformAgent` (Agente da
plataforma, `cpu`, traço pontilhado) e `perspectiveAgent` (Perspectiva sintética, `bot`,
traço tracejado).

**Nível de autoridade (`authorityLevel`)** indica o que a pessoa pode fazer na plataforma
(spec §12.1): `publicContributor`, `verifiedStakeholder`, `expertReviewer`,
`regulatorySourceCurator`, `ontologyMaintainer` e `systemOperator`.

- Só `verifiedStakeholder` usa tom civic (identidade institucional verificada). Os outros
  níveis são neutros: o nível é **permissão**, não credibilidade. A credibilidade vem da
  evidência (spec §8.3).
- O rótulo do `systemOperator` inclui "sem autoridade jurídica".

## 3.9 Estratos de stakeholders (`stakeholderStratum`)

São os oito estratos da spec §10.2. **Nenhum tem matiz**: todos usam cromo neutro, com ícone
e rótulo. Ver o motivo em `01-principios.md` §1.4.

## 3.10 Shadow Council

| Grupo | Valores |
|---|---|
| `coverageState` | `covered` (Coberto por fontes) · `partial` (Cobertura parcial) · `unrepresented` (Não representado · sem fonte) |
| `councilRound` | `r0` Dossiê de evidências → `r1` Posições independentes → `r2` Contraditório → `r3` Revisão estruturada → `r4` Relatório de minoria → `r5` Síntese e revisão humana |
| `councilMode` | `exploratory` (tracejado) · `validated` (sólido, civic) |
| `deliberationOutcome` | `open` · `convergent` · `dissentRecorded` · `inconclusive` |

O assento `unrepresented` é desenhado como um contorno tracejado vazio. **A ausência fica
visível.** Ela não é preenchida nem omitida da grade.

## 3.11 Argumentação (`argumentRelation`)

São as arestas do grafo de argumentos. Cada uma tem traço, marcador de ponta e rótulo:

| Relação | Traço | Ponta | Tom |
|---|---|---|---|
| apoia | sólido | seta | verdant |
| contesta | tracejado | barra (⊣) | crimson |
| qualifica | pontilhado | losango | ochre |
| substitui | duplo | seta aberta | neutral |
| deriva de | sólido fino | círculo | neutral |

Num grafo com mais de 40 arestas, os rótulos aparecem ao passar o mouse ou ao focar a
aresta, e a legenda fica fixa.

## 3.12 Comparação entre jurisdições (`equivalence`)

`semantic` (Equivalência semântica) · `functional` (Semelhança funcional) · `legal`
(Equivalência jurídica) · `divergent` (Divergência).

O tipo de equivalência é **sempre dito por extenso**. Não existe badge genérico
"equivalente". Conceitos parecidos não produzem deveres idênticos (spec §9.2).

## 3.13 Outros grupos

- `controversyStage`: os sete passos da spec §8.3 (Detectar → … → Acompanhar), num stepper.
- `tensionType`: as dez classes de tensão da spec §8.2, em chip neutro com ícone.
- `confidence`: medidor de três segmentos com rótulo, em tom **neutro**. Confiança não é
  boa nem ruim, então não recebe cor de semáforo.
- `time`: `validTime`, `recordTime`, `legalSnapshot`. Ver `AsOfBar` em `04-componentes.md`.
- `module`: NORM (civic), VERIFY (lagoon), DEBATE e SHADOW COUNCIL (ochre), FORESIGHT (iris).
  **A cor de módulo só aparece no cromo de navegação**: indicador ativo e overline do título.
  O conteúdo de cada módulo usa as assinaturas de estado acima. Exemplo: uma obrigação
  atendida é verde em qualquer módulo, inclusive no DEBATE.
- `knowledgeGraph`: forma e tom dos nós dos seis grafos.
