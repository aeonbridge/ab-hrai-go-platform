# Módulo comparativo do HRAI-GO

Parte do **HRAI-GO (Human-centred Regulatory AI, Governance Observatory)**. Classifica os instrumentos para comparação
entre jurisdições (ESP-ONT-02, RF-16; RT-VIS-03, passo M3).

**Versão:** 1.0.0 · **Namespace:** `https://github.com/aeonbridge/ab-hrai-go-platform/ontology/comparativo#` ·
importa o núcleo regulatório.

## Conteúdo

- **Taxonomia de base** (`comp:TaxonomiaAlanoca2025`): as 12 categorias e os 25 critérios de Alanoca, Gur-Arieh, Zick e
  Klyman, *Comparing Apples to Oranges: A Taxonomy for Navigating the Global Landscape of AI Regulation*, FAccT '25,
  doi:10.1145/3715275.3732059. Cada critério é `skos:Concept` e `hrai:RegulatoryDesignCriterion`, com a definição
  original em inglês (`skos:definition`), rótulo em português (`skos:altLabel`) e a fonte (`dcterms:source`). As
  definições ficam congeladas em `alanoca2025-definicoes.json` e são conferidas contra o PDF do paper.
- **Extensões declaradas** (`comp:ExtensoesHRAIGO`): E1 a E7, cada uma com o caso que comporta, crédito e DOI.
- **Perfis de desenho** e a regra **R28** (`comp:R28_HorizontalRiskBasedProfile`): rótulo de leitura derivado de valores
  codificados com dispositivo e revisão aprovada; os critérios continuam visíveis.

As **escalas** dos critérios (E4) não estão aqui: são uma proposta aguardando aprovação humana
(`docs/especificacoes/ESP-ONT-02/escalas-E4-proposta.md`). As codificações (`hrai:CriterionCoding`) do Brasil e da UE
vêm depois, com as escalas aprovadas.

## Gerar e verificar

```
python3 scripts/ontologia/build_comparativo.py           # gera .ttl e .owl
python3 scripts/ontologia/build_comparativo.py --check   # falha se estiverem desatualizados
python3 -m pytest -q tests/test_comparativo.py
```
