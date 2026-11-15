# HRAI-GO — General Regulatory Intelligence Ontology

**Versão:** 1.0.0 · **Idioma dos identificadores:** inglês · **Explicações:** pt-BR

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

## Separações epistemológicas obrigatórias

- `LegislativeProposal` não significa norma aprovada ou em vigor. É uma subclasse de `LegalInstrument` documental e disjunta de `EnactedLegalInstrument`.
- `hasJurisdictionalOrigin` expressa a origem territorial da norma, **não** sua aplicabilidade ao caso concreto.
- Datas `effectiveFrom` e `effectiveUntil` são atributos declarados; uma avaliação temporal externa deve verificar transições e exceções.
- `claimSupportedByEvidence` não demonstra a veracidade de um `PolicyClaim`.
- `ReviewedAndApprovedCandidate` registra uma decisão explícita de revisão; SWRL não altera automaticamente a base publicada.
- Ausência de evidência no grafo não significa descumprimento. A conclusão de compliance exige avaliação especializada e evidências com proveniência.
- `hasUpperAlertThreshold` é uma configuração de análise para indicador numérico, não um limite legal universal.
- O ambiente de execução deve registrar as versões do grafo, ontologia, regras, documentos e modelos utilizados nas avaliações.

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

O teste `tests/verify_regulatory_ontology.py` verifica parsing RDF, isomorfismo entre Turtle e RDF/XML, existência das 18 classes canônicas, quantidade e segurança estrutural das regras SWRL e ausência de regras que afirmem `assessmentHasStatus` automaticamente.

O teste estrutural **não equivale** a execução de SWRL em reasoner como Drools, Pellet ou outro mecanismo compatível.

O teste `tests/verify_regulatory_instances.py` valida cada ABox: isomorfismo Turtle/RDF-XML, existência dos termos `hrai:` na TBox, `rdfs:domain`/`rdfs:range`, tipos de literais, disjunção `LegislativeProposal`/`EnactedLegalInstrument` e ausência de `assessmentHasStatus`. Ele também executa as 18 regras SWRL serializadas na TBox com um interpretador simples de encadeamento progressivo e confere as inferências esperadas (R03-R08, R15-R17). Assim como o teste da TBox, isso é um teste estrutural, não substitui um reasoner.
