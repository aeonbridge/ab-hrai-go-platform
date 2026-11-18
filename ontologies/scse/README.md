# SCSE — Shadow Council Simulation Environment Ontology

Módulo de deliberação do **HRAI-GO (Human-centred Regulatory AI, Governance Observatory)**: tensões de deliberação,
conselho, estratos, assentos, rodadas, posições, cenários e decisões.

**Versão:** 1.1.0 · **Namespace:** `https://github.com/aeonbridge/ab-hrai-go-platform/ontology/scse#`

## Relação com o núcleo regulatório (RF-17)

- Importa o núcleo (`owl:imports <https://github.com/aeonbridge/ab-hrai-go-platform/ontology/regulatory>`) e usa as
  classes dele, sem redeclará-las: `LegalProvision`, `NormativeRequirement`, `LegalStatus`, `LegalException`,
  `Jurisdiction`, `ComplianceAssessment`, `PolicyAlternative`, `PolicyObjective` e a propriedade `claimText`.
- Termos com o mesmo nome e sentido diferente ficaram aqui com nome próprio: `provisionStateHasStatus` (status de um
  estado datado de dispositivo; o `hasLegalStatus` do núcleo vale para versões de instrumento) e
  `positionGroundedInEvidence` (fundamento de uma posição documentada; o `perspectiveGroundedIn` do núcleo vale para a
  perspectiva sintética).
- As classes de deliberação têm a casa aqui (`scse:Deliberation`, `scse:StakeholderPosition`,
  `scse:SyntheticStakeholderPerspective`, `scse:SyntheticStakeholderPosition`), com `owl:equivalentClass` para as
  classes homônimas do núcleo, mantidas por compatibilidade.
- Alinhamentos: `PolicyTension ⊑ hrai:RegulatoryTension`, `ArgumentClaim ⊑ hrai:PolicyClaim`,
  `EvidenceRecord ⊑ hrai:Evidence`.

A versão 1.0.0 usava o namespace provisório `example.org` e redeclarava classes do núcleo.

## Arquivos

- `SCSE_Shadow_Council_Ontology.ttl`: ontologia OWL 2 em Turtle, com as regras SWRL (R01–R09) serializadas em RDF.
- `SCSE_Shadow_Council_Ontology.owl`: o mesmo grafo em RDF/XML.

Os indivíduos do namespace `scse/example#` são ilustrações sintéticas, não dados reais.

## Verificação

`python3 -m pytest -q tests/test_modulos.py`: nenhum termo declarado nos dois módulos, importação do núcleo, classes de
deliberação com equivalência e as regras do SCSE disparando sobre o núcleo importado.
