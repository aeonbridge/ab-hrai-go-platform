# HRAI-GO — General Regulatory Intelligence Ontology

**Versão:** 1.1.0 (proposta; anterior: 1.0.0) · **Idioma dos identificadores:** inglês · **Explicações:** pt-BR

## Objetivo

Ontologia geral de inteligência regulatória multinacional. Sua função é representar instrumentos, versões, dispositivos, requisitos, contextos nacionais, indicadores, tensões, lacunas, argumentos, stakeholders, deliberações e impactos sobre aplicações de IA.

Este módulo é **independente do SCSE (Shadow Council)** e poderá ser reutilizado por ele mediante alinhamentos semânticos documentados.

## Arquivos

- `HRAI_GO_Regulatory_General.ttl`: ontologia OWL 2 em Turtle, incluindo a serialização RDF das regras SWRL.
- `HRAI_GO_Regulatory_General.owl`: mesma ontologia OWL 2 em RDF/XML, incluindo as mesmas regras SWRL.
- `HRAI_GO_Regulatory_General.swrl`: regras SWRL em formato textual didático, para uso em editores compatíveis como SWRLTab.

A extensão `.owl` identifica o tipo de artefato, não um terceiro formalismo: os dois primeiros arquivos são serializações RDF do mesmo grafo.

## Classes canônicas

As 18 classes-base aprovadas: `Jurisdiction`, `LegalInstrument`, `LegislativeProposal`, `LegalProvision`, `NormativeRequirement`, `RegulatoryModel`, `NationalContext`, `ContextIndicator`, `PolicyObjective`, `PolicyInstrument`, `RegulatoryTension`, `RegulatoryGap`, `PolicyClaim`, `PolicyAlternative`, `Stakeholder`, `StakeholderPosition`, `Deliberation`, `PolicyImpactAssessment`.

A modelagem inclui classes auxiliares para versões e estados jurídicos, proveniência, decisões de revisão, alterações normativas, avaliação de conformidade e propagação de impacto.

## Fluxo de atualização contínua

1. **Source Monitoring:** `MonitoringAgent` identifica uma publicação ou mudança e captura `SourceSnapshot`.
2. **Document Change Detection:** gera um `RegulatoryChangeEvent` relacionado a versões ou dispositivos.
3. **Normative Knowledge Extraction:** registra `CandidateAssertion` em `ExtractionBatch`; a informação extraída ainda não é publicada como fato validado.
4. **Verification & Publication:** um `ReviewDecision` explicitamente aprovado possibilita `ReviewedAndApprovedCandidate`. A publicação em `KnowledgeGraphRelease` é transacional e autorizada.
5. **Knowledge Graph Update:** o novo `KnowledgeGraphRelease` preserva `previousGraphRelease`; a estrutura TBox é separadamente versionada por `OntologyRelease`.
6. **Impact Propagation:** SWRL marca dispositivos, requisitos, avaliações e aplicações **potencialmente** afetados por uma mudança; a plataforma agenda uma reavaliação externa.

## Regras

- `R01_ProvisionJurisdictionOrigin`: Jurisdictional origin, not enforceability.
- `R02_RequirementJurisdictionOrigin`: Provenance origin, not binding applicability.
- `R03_PolicyMechanismCountry`: Connects an explicitly recorded policy mechanism to its jurisdiction.
- `R04_IndicatorJurisdiction`: Associates national context with an indicator.
- `R05_ContestedClaim`: Explicit challenge, not a finding of falsehood.
- `R06_ContestedTension`: A tension contains a contested claim.
- `R07_DeliberationStakeholder`: A stakeholder's attributed position participates in deliberation.
- `R08_IndicatorAssessedAlternative`: An alternative was examined using context indicators.
- `R09_ApprovedCandidate`: Review metadata, not automatic ABox publication.
- `R10_VersionChangeProvisionCandidates`: Potential provision changes await exact diff review.
- `R11_ProvisionChangeRequirementCandidates`: Propagates potential impact, not a legal judgment.
- `R12_RequirementChangeAssessmentReview`: Flags dependencies for re-evaluation.
- `R13_ApplicationReviewImpact`: Flags an impacted application without asserting noncompliance.
- `R14_ControlRequirementCandidate`: Potential control association, not proof of satisfaction.
- `R15_ChangeSource`: Source provenance for a change event.
- `R16_TensionNationalContext`: Link tensions to an explicit national context.
- `R17_EvidenceAttachedClaim`: Evidence attachment alone does not verify truth.
- `R18_UpperIndicatorThreshold`: Explicit investigative threshold, not an automatic legal violation.
- `R19_ExecutionBelowAlertRatio`: Investigative execution signal, not evidence of policy failure.
- `R20_ImpactEvaluated`: Records that an impact evaluation exists; does not change compliance status.
- `R21_SyntheticPosition`: Synthetic origin propagates to the position.
- `R22_ProposedProvision`: Provision of a proposal; no binding force.
- `R23_ProspectiveRequirement`: Requirement derived from a proposal; prospective, not binding.

## Separações epistemológicas obrigatórias

- `LegislativeProposal` não significa norma aprovada ou em vigor. É uma subclasse de `LegalInstrument` documental e disjunta de `EnactedLegalInstrument`.
- `hasJurisdictionalOrigin` expressa a origem territorial da norma, **não** sua aplicabilidade ao caso concreto.
- Datas `effectiveFrom` e `effectiveUntil` são atributos declarados; uma avaliação temporal externa deve verificar transições e exceções.
- `claimSupportedByEvidence` não demonstra a veracidade de um `PolicyClaim`.
- `ReviewedAndApprovedCandidate` registra uma decisão explícita de revisão; SWRL não altera automaticamente a base publicada.
- Ausência de evidência no grafo não significa descumprimento. A conclusão de compliance exige avaliação especializada e evidências com proveniência.
- `hasUpperAlertThreshold` é uma configuração de análise para indicador numérico, não um limite legal universal.
- O ambiente de execução deve registrar as versões do grafo, ontologia, regras, documentos e modelos utilizados nas avaliações.

## Mudanças da 1.1.0

Extensão **aditiva**: nenhum termo da 1.0.0 foi removido ou renomeado, e todas as triplas da 1.0.0 (exceto `versionIRI` e `versionInfo`) continuam presentes. Lacunas encontradas ao instanciar a ontologia com o PBIA, o PL 2338 e o conselho sintético no protótipo `prototypes/cascata-regulatoria`:

| Lacuna | Mudança |
|---|---|
| Não havia como representar um plano de investimento público, seu orçamento e sua execução (ex.: eixos e valores do PBIA). | `PublicPolicyPlan` e `PolicyPlanAxis` (subclasses de `PolicyInstrument`), `BudgetAllocation`, `ExecutionRecord`, valores com moeda, período e estágio de execução; `R19` sinaliza execução abaixo de uma razão de alerta configurada por analista. |
| `pursuesObjective` tem domínio `RegulatoryModel`; usá-lo num instrumento faria um reasoner classificá-lo como modelo regulatório. | `instrumentPursuesObjective` (domínio `PolicyInstrument`). |
| Impactos sinalizados por R12/R13 não tinham fechamento controlado; `impactReviewStatus` era texto livre. | `ImpactReviewOutcome` com três indivíduos, `impactEvaluationHasOutcome`, `impactEvaluationBy`, `impactEvaluatedAt`; `R20` registra que a avaliação existe. `impactReviewStatus` foi marcado `owl:deprecated`. |
| `Stakeholder` não distinguia perspectiva sintética de ator real. | `SyntheticStakeholderPerspective` e `IdentifiedStakeholder`, disjuntas; `R21` propaga a origem sintética para a posição; `perspectiveGroundedIn`. Alinhamento conceitual com `scse:PerspectiveAgent`, sem importação. |
| Dispositivos de uma proposta herdavam `provisionInJurisdiction` sem marca de que não vinculam. | `ProposedProvision` (R22) e `ProspectiveRequirement` (R23); comentários de origem em `instrumentInJurisdiction` e `provisionInJurisdiction`; `proposalInJurisdiction` passa a ser subpropriedade de `instrumentInJurisdiction`. |

### Impactos em aberto

SWRL é monotônico e de mundo aberto: nenhuma regra pode concluir que um impacto *não* foi avaliado. A lista de pendências é uma consulta de mundo fechado feita pela plataforma, fora do raciocínio:

```sparql
PREFIX hrai: <https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory#>
SELECT ?assessment ?event WHERE {
  ?assessment hrai:assessmentNeedsReviewDueTo ?event .
  FILTER NOT EXISTS { ?assessment hrai:assessmentImpactEvaluatedFor ?event }
}
```

### Ressalvas da 1.1.0

- `R19` compara valores na mesma moeda, mas não normaliza inflação nem verifica se período e estágio (`committed`, `disbursed`, `paid`) são comparáveis. Isso é responsabilidade de quem configura `executionAlertRatio`.
- `IdentifiedStakeholder` registra que a identidade foi verificada; a ontologia não define o processo de verificação.
- A mudança é uma proposta de `OntologyRelease` e deve passar pelo processo de governança da TBox antes de ser adotada.

## Validação

O teste `tests/verify_regulatory_ontology.py` verifica parsing RDF, isomorfismo entre Turtle e RDF/XML, existência das 18 classes canônicas e das 11 classes da 1.1.0 com suas superclasses, as disjunções obrigatórias, a quantidade de regras SWRL (23), a segurança de cada regra (toda variável da cabeça aparece no corpo), a presença de ressalva em cada regra e a ausência de regras que afirmem `assessmentHasStatus`, `hasLegalStatus` ou `releasePublishesCandidate` automaticamente. Até a 1.0.0, o README anunciava esta última checagem, mas o teste não a fazia.

O teste estrutural **não equivale** a execução de SWRL em reasoner como Drools, Pellet ou outro mecanismo compatível.
