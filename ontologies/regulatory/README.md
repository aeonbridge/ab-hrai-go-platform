# HRAI-GO — General Regulatory Intelligence Ontology

Parte do **HRAI-GO (Human-centred Regulatory AI, Governance Observatory)**. O prefixo `hrai:` e os nomes de arquivo `HRAI_GO_*` são identificadores legados (a sigla nasceu como *High-Risk AI*, significado aposentado); ver `docs/NOMENCLATURA.md`.

**Versão:** 1.2.0 (proposta; anteriores: 1.1.0, 1.0.0) · **Idioma dos identificadores:** inglês · **Explicações:** pt-BR

## Objetivo

Ontologia geral de inteligência regulatória multinacional. Sua função é representar instrumentos, versões, dispositivos, requisitos, contextos nacionais, indicadores, tensões, lacunas, argumentos, stakeholders, deliberações e impactos sobre aplicações de IA.

Este módulo é o **núcleo regulatório** e não depende do SCSE (Shadow Council). O módulo SCSE (`ontologies/scse/`) importa este núcleo com `owl:imports` e não redeclara suas classes (ESP-ONT-02, RF-17). As classes de deliberação (`Deliberation`, `StakeholderPosition`, `SyntheticStakeholderPerspective`, `SyntheticStakeholderPosition`) continuam aqui só por compatibilidade com as instâncias e as regras R07 e R21; a casa delas passou a ser o SCSE, com `owl:equivalentClass` declarada lá. Modelagem nova de deliberação usa as classes do SCSE.

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

### v1.2.0 (ESP-ONT-02, RF-03)

Termos aditivos para comparação, cobertura, capacidade, correspondência e especificidade: `RegulatoryDesignCriterion`,
`CriterionCoding`, `SubstantiveArea`, `ProvisionCorrespondence` (tipos equivalente, adaptado, parcial, divergente),
`CapacityRequirement`, `CapacityShortfallIndicator`, `RiskExposureIndicator`, `CoverageAssessment`, `claimQualifies`,
`claimComplements` e `NationalSpecificity` (dimensão da QN1, tipo de diferença, `JurisdictionComparison`,
`groundedInSpecificity`). Regras novas, todas de sinalização:

- `R24a_FunctionCoverageInForce`, `R24b_FunctionCoverageProposed`, `R24c_FunctionCoveragePlanned`: cobertura de área
  por jurisdição, com a força jurídica vinda da classe do instrumento (vigente, proposta ou plano).
- `R25a_CapacityShortfall`, `R25b_RequirementCapacityRisk`: indicador abaixo do limiar inferior e requisito que
  pressupõe essa capacidade. Sinal para investigar, não juízo de inviabilidade.
- `R26_Transposition`: correspondência equivalente ou adaptada, revisada e aprovada, entre jurisdições diferentes.
- R27 não existe: SWRL não tem negação; "exposição sem cobertura" é consulta SPARQL sob um `CoverageAssessment`.
- R28 (perfil de desenho) fica no módulo comparativo, junto dos critérios que combina; R29 e R30 (apoio sintético e
  alternativa divergente) ficam no módulo SCSE, casa das classes de deliberação.

Invariantes I-1 a I-4 e tempo de raciocínio do grafo completo: `tests/test_invariantes.py`.

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
PREFIX hrai: <https://hrai-go.aeonbridge.io/ontology/regulatory#>
SELECT ?assessment ?event WHERE {
  ?assessment hrai:assessmentNeedsReviewDueTo ?event .
  FILTER NOT EXISTS { ?assessment hrai:assessmentImpactEvaluatedFor ?event }
}
```

### Ressalvas da 1.1.0

- `R19` compara valores na mesma moeda, mas não normaliza inflação nem verifica se período e estágio (`committed`, `disbursed`, `paid`) são comparáveis. Isso é responsabilidade de quem configura `executionAlertRatio`.
- `IdentifiedStakeholder` registra que a identidade foi verificada; a ontologia não define o processo de verificação.
- A mudança é uma proposta de `OntologyRelease` e deve passar pelo processo de governança da TBox antes de ser adotada.

## Instâncias (ABox)

As instâncias ficam em `instances/<jurisdição>/`, separadas da TBox, que **não** é alterada por elas. Cada ABox declara `owl:imports` da ontologia geral. O `.ttl` é a fonte editável; o `.owl` é gerado por `python scripts/build_regulatory_instances.py`.

| Arquivo | Fonte | Conteúdo |
|---|---|---|
| `instances/br/HRAI_GO_Regulatory_BR_PBIA_2025.ttl` / `.owl` | PBIA 2024-2028 (MCTI/CGEE, 2025), versão VN 8, SHA-256 `b6542407…f46f5` | Jurisdição Brasil, contexto nacional e 16 indicadores, modelo regulatório, 12 objetivos, 20 instrumentos de política com orçamento (`schema:MonetaryAmount`), PL 2338/2023 e 6 normas citadas, 2 lacunas, 5 tensões, 8 afirmações, 69 stakeholders institucionais (CCT, GT, Núcleo de IA, financiadores, desenvolvedores) com 4 posições, deliberação, alternativas e 17 aplicações de IA |

Decisões de modelagem do PBIA:

- O PBIA é um **plano de política pública**: `PolicyInstrument`, nunca `LegalInstrument`. Nenhum `NormativeRequirement` é derivado dele.
- Normas citadas (LAI, LGPD, Decretos 10.046/2019 e 12.308/2024, Portaria MCTI 8.251/2024, AI Act) são apenas referências: sem dispositivos, sem versões vigentes.
- O PL 2338/2023 é `LegislativeProposal`, com `ProposedLegalStatus` válido para a data da fonte.
- Todo o conteúdo está em `CandidateAssertion` sem `ReviewDecision`: **pendente de revisão**, ainda não publicável em `KnowledgeGraphRelease`.
- Stakeholders só em nível institucional; pessoas físicas citadas (titulares/suplentes do CCT, equipes) não são instanciadas. Vínculos usam `schema:memberOf`, `schema:parentOrganization`, `schema:funder`, `schema:provider` e `dcterms:contributor`, sem estender a TBox.
- O indicador de renováveis de 83% (Eixo 4) diverge dos 89,2% (Eixo 1). Ambos estão registrados e anotados para verificação na fonte primária.

## Validação

O teste `tests/verify_regulatory_ontology.py` verifica parsing RDF, isomorfismo entre Turtle e RDF/XML, existência das 18 classes canônicas e das 11 classes da 1.1.0 com suas superclasses, as disjunções obrigatórias, a quantidade de regras SWRL (23), a segurança de cada regra (toda variável da cabeça aparece no corpo), a presença de ressalva em cada regra e a ausência de regras que afirmem `assessmentHasStatus`, `hasLegalStatus` ou `releasePublishesCandidate` automaticamente. Até a 1.0.0, o README anunciava esta última checagem, mas o teste não a fazia.

O teste estrutural **não equivale** a execução de SWRL em reasoner como Drools, Pellet ou outro mecanismo compatível.

O teste `tests/verify_regulatory_instances.py` valida cada ABox: isomorfismo Turtle/RDF-XML, existência dos termos `hrai:` na TBox, `rdfs:domain`/`rdfs:range`, tipos de literais, disjunção `LegislativeProposal`/`EnactedLegalInstrument` e ausência de `assessmentHasStatus`. Ele também executa as 18 regras SWRL serializadas na TBox com um interpretador simples de encadeamento progressivo e confere as inferências esperadas (R03-R08, R15-R17). Assim como o teste da TBox, isso é um teste estrutural, não substitui um reasoner.

**IRIs:** desde 17/11/2026 sob `https://hrai-go.aeonbridge.io/` (decisões D-05 e D-05a); antes, sob `https://github.com/aeonbridge/ab-hrai-go-platform/`. IRIs resolvíveis no navegador quando a publicação no subdomínio estiver ativa (RNF-01).
