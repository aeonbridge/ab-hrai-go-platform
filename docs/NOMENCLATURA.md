# Nomenclatura oficial: HRAI-GO

**Decisão registrada em 17/11/2026.** Este arquivo é a fonte canônica do nome da plataforma.
Qualquer outro texto do repositório que divergir dele está errado e deve ser corrigido.

## Nome

> **HRAI-GO: Human-centred Regulatory AI, Governance Observatory**
>
> *Plataforma de inteligência regulatória humano–IA*

| Letra | Significado | Por quê |
|---|---|---|
| **H** | *Human-centred* | O humano vem primeiro: supervisão humana, papéis humanos que contestam, qualificam ou apoiam com evidência, e revisão humana antes de publicar. Termo alinhado ao AI Act, à OCDE e ao PL 2338. |
| **R** | *Regulatory* | Inteligência regulatória: normas, versões, dispositivos, obrigações, tensões e lacunas. |
| **AI** | *AI* | Objeto regulado (aplicações de IA) e meio de análise (agentes, Shadow Council). |
| **GO** | *Governance Observatory* | Papel público da plataforma: observar, comparar e expor a governança de IA (Brasil e mundo) de forma aberta. |

## Formas de uso

| Contexto | Forma |
|---|---|
| Primeira menção em qualquer documento | **HRAI-GO (Human-centred Regulatory AI, Governance Observatory)** |
| Menções seguintes | **HRAI-GO** |
| Subtítulo / tagline | *Plataforma de inteligência regulatória humano–IA* |
| Português, quando for preciso traduzir | *Observatório de Governança de IA Regulatória centrada no humano* |
| Identificadores de código e arquivos | `hrai-go`, `hrai_go`, `HRAIGO` (sem mudança) |

Grafia: sempre `HRAI-GO`, com hífen e em maiúsculas. Escreva *Human-centred* em inglês britânico,
como no AI Act, com hífen e com vírgula antes de *Governance Observatory*.

## Origem e nome legado

A sigla nasceu como **High-Risk AI**, de uma ontologia de sistemas de IA de alto risco. **Esse
significado está aposentado.** Ele continua só onde mudar quebraria compatibilidade:

- namespaces e arquivos de ontologia (`hrai:`, `hrai-*.owl`, `HRAI_GO_Regulatory_*.ttl`/`.owl`);
- o título do documento externo *Guia de Conformidade e Governança para Sistemas de Inteligência
  Artificial de Alto Risco (HRAI)*, que é referência bibliográfica e mantém o título original.

Nesses casos "HRAI" é um identificador técnico ou um título citado. Não é a expansão da sigla.

## O que não fazer

- Não expandir HRAI-GO como *High-Risk AI*.
- Não usar "Human–AI Regulatory Intelligence" como expansão da sigla, porque as letras não batem
  (daria HARI). A ideia de rede humano–IA fica no subtítulo.
- Não inventar variações (ex.: "HRAI Governance", "HRAIGO Platform" em prosa).

## Garantia

O teste `tests/test_nomenclatura.py` falha se o nome canônico sumir dos pontos de entrada (README,
pyproject, site, documento principal) ou se algum texto voltar a expandir HRAI-GO como *High-Risk AI*.
