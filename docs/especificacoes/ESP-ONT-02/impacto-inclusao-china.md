# Impacto da inclusão de uma nova jurisdição: China (decisão D-01c, 17/11/2026)

Validação do processo de inclusão de jurisdição no HRAI-GO (Human-centred Regulatory AI, Governance Observatory),
pedida pelo autor (D-01b: deixar a China fora para medir depois; D-01c: incluir com textos oficiais).

## Passos executados

1. **Fontes no corpus** (`docs/ai-regulations/ch/`): dois textos oficiais da Administração do Ciberespaço da China (CAC),
   impressos do site — CH01, Medidas Provisórias para Serviços de IA Generativa (Ordem nº 15, texto integral, em vigor
   desde 15/08/2023); CH-02, comunicado das Regras de Síntese Profunda (resumo, em vigor desde 10/01/2023) — e duas fontes
   secundárias (Regulations.AI 2026; Law Library of Congress 2023).
2. **Extração** (`scripts/ontologia/extrair_china.py`): jurisdição, 14 instrumentos, 7 autoridades; versão oficial das
   medidas de IA generativa com os 24 artigos (texto em chinês, capítulo, citação, snapshot com SHA-256). Instrumentos
   que só aparecem nas fontes secundárias ficam marcados como tal.
3. **Inclusão**: o arquivo passou de `em-espera/` para `instances/cn/`; gêmeo OWL gerado; validação das instâncias OK.
4. **Detecção automática do que faltava**: a consulta de aceite V30 acusou que **as 8 especificidades da QN1** não tinham
   comparação com a nova jurisdição. Achado no próprio processo: a consulta multiplicava as linhas pelo número de
   instrumentos (112 linhas); passou a usar `DISTINCT`.
5. **Ajuste**: cada especificidade ganhou a comparação com a China. Só uma tem valor codificado com fonte primária: S7
   (supervisão), pelo art. 16 do texto oficial (supervisão repartida entre os departamentos competentes). As demais
   ficam "não codificado", com o motivo.
6. **Testes e CI**: toda a suíte passa; o teste da China passou a exigir a comparação em todas as especificidades.

## Medidas (antes → depois)

| Medida | Antes | Depois |
|---|---|---|
| Triplas do grafo completo, após raciocínio | 11.725 | 12.234 (+509) |
| Jurisdições com instrumento no corpus | 4 (BR, UE, RU, EUA) | 5 (+China) |
| V30, especificidades sem comparação completa | 0 | 8 ao incluir → 0 após o ajuste |
| PC9, linhas da resposta à QN1 | 42 | 56 (+14 comparações com a China) |
| Demais consultas (PC1 a PC8) | — | inalteradas |
| Contador "sem lastro" da câmara | 0 de 88 | 0 de 88 (a câmara não exibe a China) |
| Fila de monitoramento | — | inalterada (a inclusão não é mudança de texto de instrumento já existente) |

## O que a validação mostra

- A inclusão de jurisdição é detectada pelo CI sem regra nova: a V30 lista exatamente o que precisa de comparação.
- O efeito fica restrito à QN1 (comparações); nada mudou nas QN2 e QN3, que dependem das especificidades, não das
  comparações.
- Para uma jurisdição com só fontes secundárias, quase tudo fica "não codificado". O texto oficial é o que torna a
  comparação útil (caso S7).
- A câmara e o monitoramento não mudam, porque não exibem jurisdições estrangeiras e não houve mudança de texto.

## Para a próxima jurisdição

Mesmos passos: fontes em `docs/ai-regulations/<código>/`, extrator, arquivo em `instances/<código>/`, gêmeo OWL, CI.
A V30 aponta as comparações que faltam; registre a decisão em `decisoes.json`.
