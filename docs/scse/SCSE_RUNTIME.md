# SCSE Runtime — conselho multi-provider

Implementação executável do Shadow Council definido em
`SCSE_Shadow_Council_Simulation_Spec.tex`. O runtime segue o protocolo R0–R8, as
memórias isoladas, a separação entre motor jurídico e conselho e os artefatos de
saída da especificação. O conselho é composto por **Anthropic, OpenAI, xAI (Grok)
e Gemini**, e os quatro são obrigatórios na configuração.

> Os resultados são deliberações sintéticas sob premissas declaradas. Não são
> parecer jurídico, consulta pública nem previsão do Brasil real.

## Instalação

```bash
pip install -e '.[all,dev]'      # SDKs anthropic, openai, google-genai + pytest
export OPENROUTER_API_KEY=...    # padrão: uma assinatura e uma chave para os 4 providers
# opcional, só com --transport direct:
# export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... XAI_API_KEY=... GEMINI_API_KEY=...
```

## Transporte: OpenRouter por padrão

Por padrão, todas as chamadas passam pelo OpenRouter (`[defaults] transport = "openrouter"`).
O nome do provider nas métricas continua sendo a família do modelo (anthropic, openai,
xai, gemini). Para manter a comparação entre providers limpa, o adaptador:

- fixa o host original de cada modelo (`provider.only`/`order` = `openrouter_upstream`);
- desliga o fallback entre hosts (`allow_fallbacks = false`);
- exige hosts que honrem `response_format` e `reasoning` (`require_parameters = true`);
- traduz o esforço de cada provider para `reasoning.effort`;
- contabiliza o custo cobrado (`usage.cost`), o que faz `maxCostUsd` valer para todos os providers.

Os adaptadores diretos continuam disponíveis: `--transport direct`,
`transport = "direct"` num provider ou no braço do experimento. Rodar o mesmo braço
pelas duas vias mede se a camada intermediária altera o comportamento.

Os 12 slugs configurados foram encontrados no catálogo da API do OpenRouter em
2026-11-15. `scse models verify` valida a presença dos IDs no catálogo; não testa
autenticação nem uma chamada de geração. Os hosts `xai` e `google-ai-studio` ainda
não foram validados em chamadas reais.

## Uso rápido

```bash
scse validate scenarios/brasil-ficticio/*.json
scse models list                      # perfil -> tier -> modelo de cada provider
scse models verify                    # confere os IDs no catálogo de cada provider
scse models ping                      # faz uma chamada curta de geração
scse run scenarios/brasil-ficticio/BR-PBIA-001.json --dry-run    # offline, provider mock
scse run scenarios/brasil-ficticio/BR-PBIA-001.json --seats 8 --replicates 1 --critic
scse experiment experiments/scse/provider-practice.toml --plan   # estima custo
scse experiment experiments/scse/provider-practice.toml
```

Sem instalar: `PYTHONPATH=src python -m scse ...`.

## Escolha de modelo por perfil

O perfil vem do estrato (definido no world pack) ou do papel no pipeline. Cada
perfil aponta para um tier, e cada provider declara um modelo por tier em
`config/scse/models.toml`.

| Perfil | Tier | Usado por | Por quê |
|---|---|---|---|
| `perspective.deep` | deep | reguladores, poder público operador, pesquisa | Exigem leitura normativa, institucional e técnica mais densa |
| `perspective.standard` | standard | empresas, sociedade civil, trabalhadores, afetados, infraestrutura | Posições mais diretas; custo menor por turno |
| `critic` | standard | crítica cruzada na R7 | Verificação de aderência às fontes, sempre por provider diferente do autor |
| `synthesizer` | deep | redação das tensões (opcional) | Síntese neutra de muitos argumentos |
| `smoke` | light | `scse models ping` | Teste de conectividade barato |

| Tier | Anthropic | OpenAI | xAI | Gemini |
|---|---|---|---|---|
| deep | `claude-opus-5-5` (effort high) | `gpt-6-sol` (reasoning high) | `grok-4.7` | `gemini-4-argon` (thinking high) |
| standard | `claude-sonnet-5-5` (effort medium) | `gpt-6.1-terra` | `grok-4.6` | `gemini-3.8-flash` |
| light | `claude-haiku-5-5` | `gpt-6-luna` | `grok-4.5` | `gemini-3.5-flash-lite` |

Os IDs desta tabela foram encontrados no catálogo do OpenRouter em 2026-11-15.
Isso não garante acesso de geração pela chave configurada. Os IDs diretos vêm da
documentação dos respectivos SDKs.

### Como trocar um modelo

1. Editar `openrouter_id` (OpenRouter) ou `id` (API direta) no TOML.
2. Variável de ambiente: `SCSE_MODEL__XAI__DEEP=x-ai/grok-4.6`.
3. Linha de comando: `scse run ... --set openai.deep=openai/gpt-6.1-terra` ou
   `--set gemini.standard.thinking_level=low`. Um valor no formato `fornecedor/modelo`
   altera o slug do OpenRouter; um id simples altera o id da API direta.
4. Por experimento: a seção `[overrides]` do arquivo de experimento.

Para mudar quem usa qual tier, edite `[profiles]`. Para mudar o perfil de um
estrato, edite `profile` no world pack.

## Distribuição de provider e modelo por estrato

Cada estrato tem uma lista `mix` em `[strata.<id>]` (`models.toml`, ou no arquivo de
experimento). O padrão é peso igual para os 4 providers em todos os estratos, cada um
com o modelo do tier do perfil do estrato:

```toml
[strata.regulators]
mix = [
  { provider = "anthropic", tier = "deep",     weight = 15 },   # 15% Opus
  { provider = "anthropic", tier = "standard", weight = 10 },   # 10% Sonnet
  { provider = "openai",    model = "openai/gpt-6-sol", weight = 25 },
  { provider = "xai",       weight = 25 },                      # tier do perfil
  { provider = "gemini",    weight = 25 },
]
```

- `provider` é obrigatório. `tier` ou `model` são opcionais; sem eles vale o tier do perfil do estrato.
- `weight` é relativo: pesos que somam 100 lêem-se como percentuais. Um estrato ausente usa `[strata.default]`.
- A alocação é determinística (weighted round-robin suave). Em qualquer janela de assentos, cada entrada fica a no máximo 1 assento da sua cota, e a janela desloca 1 posição por réplica. Com menos assentos do que entradas, os percentuais se realizam no acumulado das réplicas.
- `--providers a,b` filtra o mix e renormaliza os pesos.
- O `council-roster.json` e o `run-manifest.json` registram, por estrato, o percentual configurado e os assentos realizados.

| `assignment` | Comportamento | Quando usar |
|---|---|---|
| `weighted` (padrão) | Distribuição por estrato conforme `[strata]` | Execução principal |
| `rotate` | Pesos iguais entre os providers selecionados, ignorando `[strata]` | Linha de base de rotação pura |
| `fixed` | O provider é fixo por estrato (`[assignment.fixed]`) | Só como controle. Viés e perspectiva ficam confundidos |
| `single` | Todo o conselho num único provider (`--providers xai`) | Ablação: mede o falso consenso de uma família de modelos |

O `BalanceCheck` sinaliza um provider com mais de 50% dos assentos, um estrato
com mais de 30% e conselhos de provider único.

## Protocolo implementado

| Etapa | O que o runtime faz |
|---|---|
| R0 Prepare | Valida o contrato JSON Schema (FR-01), resolve o world pack e congela o `WorldSnapshot` com hash (FR-03) |
| R1 IndependentReview | Posições privadas, sem ver os demais assentos |
| R2 OpeningStatements | Publica as teses partindo dos rascunhos privados |
| R3 CrossExamination | Contestação, apoio e pedidos de evidência; não é permitido apoiar ou contestar a própria tese |
| R4 EvidenceRevision | Só os assentos com teses contestadas: revisar, retirar ou manter |
| R5 Negotiation | Emendas, salvaguardas e alternativas |
| R6 CounterfactualBranches | Uma avaliação por ramo (`branchId` obrigatório); o estado-base fica imutável |
| R7 MinorityAndAudit | Relatórios minoritários, auditoria de fundamentação e crítica cruzada opcional |
| R8 Publish | `report.json` validado contra `report.schema.json` e demais artefatos |

Regras aplicadas em código, independentemente do modelo:

- Ação fora da rodada, alvo inexistente ou alvo alheio para revisar ou retirar é rejeitado e registrado no ledger.
- Fonte citada que não está no snapshot é removida. A tese é marcada `insufficientGrounding` e rebaixada para `hypothesis`.
- O conselho só emite `syntheticPerspective`, `hypothesis` ou `unknown`; nunca `verifiedLegalFact`.
- Os achados jurídicos vêm só do `LegalAssessmentEngine`: um PL vira `proposalOnly` (FR-08) e nenhum voto sintético altera um achado.
- Respostas fora do contrato JSON ganham uma nova tentativa de reparo. Recusas e erros viram eventos e o assento se abstém.
- `tokenBudget` e `maxCostUsd` interrompem a execução, e o relatório registra a interrupção.
- O ledger é encadeado por hash. `ledgerIntact` no manifesto verifica a cadeia.

## Cenários: Brasil fictício e PBIA (2026–2033)

O world pack fica em `scenarios/brasil-ficticio/world.json`: 8 estratos e 20
assentos, com quotas do spec, 19 evidências e 9 indicadores. Os indicadores
marcados `[FICTÍCIO]` são inventados. Os dados reais (orçamento de R$ 23,03 bi,
governança, supercomputador, PL 2338, LGPD) vêm de fontes secundárias com
`verificationStatus=pending`. Povos indígenas e comunidades tradicionais ficam
marcados como `Unrepresented`: não há fonte para essas perspectivas no pacote,
e o runtime não inventa posição.

| Cenário | Modo | Pergunta | Ramos contrafactuais |
|---|---|---|---|
| BR-PBIA-001 | policy | Sustentação dos objetivos do PBIA até 2033 com o fim do ciclo em 2028 | financiamento mantido / corte de 50% / descontinuidade |
| BR-PBIA-002 | policy | Soberania computacional × custo × energia × dependência | nuvem nacional obrigatória / choque de chips / híbrido com localização |
| BR-PBIA-003 | policy | Formação, requalificação e trabalho sem ampliar desigualdade | negociação coletiva / meta dobrada com cota regional / fuga de talentos |
| BR-PBIA-004 | policy | Avaliação de impacto ex-ante e contestação humana na IA pública | auditoria ex-ante / documentação por risco / fiscalização ×3 |
| BR-PBIA-005 | solution | Assistente fictício de triagem de benefícios | revisão humana obrigatória / indeferimento automático (estresse) |

## Experimento: a prática de cada provider

`experiments/scse/provider-practice.toml` cruza os 5 cenários com os braços abaixo, com 3 réplicas cada.

| Braço | Condição do spec | O que isola |
|---|---|---|
| `mixed-weighted` | SCSE | Conselho estratificado e misto, conforme `[strata]` (referência) |
| `fixed-by-stratum` | controle | Efeito de fixar provider por estrato |
| `solo-<provider>` × 4 | ablação | Comportamento e falso consenso de cada família de modelos |
| `B2-unstratified` | B2 | Debate multiagente sem estratos |
| `B1-single-agent-<provider>` × 4 | B1 | Agente único de cada provider |

Métricas por provider (`provider-scorecard.json`): `schemaValidRate`,
`repairRate`, `refusalRate`, `groundingRate`, `invalidCitationRate`,
`hypothesisShare`, `challengesPerR3Turn`, `receivedChallengeRate`,
`responsivenessRate`, `criticGroundedRate`, `selfSupportShare` e
`selfChallengeShare` (comparados com `baselineShare` = 1/nº de providers),
tokens, latência e custo. Por cenário, o `sensitivity-report.json` traz a
dispersão entre réplicas e a sobreposição estrutural das tensões.

**O que essas métricas não medem:** verdade, qualidade ou utilidade. Elas
descrevem o comportamento de cada modelo dentro do protocolo. Para qualidade,
aplique a rubrica de especialistas da especificação (`ClaimEvidencePrecision`,
`RelevantGapRecall`, `ExpertUtilityScore` etc.) sobre casos auditados.

## Artefatos por execução

`report.json`, `report.md`, `run-manifest.json`, `world-snapshot.jsonld`,
`council-roster.json`, `deliberation-events.jsonl`, `claims.json`,
`compliance-matrix.json`, `tensions.json`, `minority-report.md`,
`provider-scorecard.json`, `turn-stats.json`, `run-summary.json`. Por cenário:
`sensitivity-report.json`. Por experimento: `experiment-summary.{json,md}`.

### Registro integral do HTTP OpenRouter

Cada réplica real roteada pelo OpenRouter grava todos os requests e responses em
`rep-NN/http/openrouter-http.jsonl`. O corpo HTTP completo fica em `bodyBase64`
(byte a byte) e, quando UTF-8, também em `bodyText`; inclui método, URL, cabeçalhos,
status, timestamps, hash SHA-256 e IDs para correlacionar cada par. A credencial
de autenticação e cabeçalhos de chave/cookie são redigidos. O diretório e o arquivo
recebem permissões restritas (`0700`/`0600`, quando suportadas pelo filesystem), e
cada evento é sincronizado em disco antes de a chamada prosseguir. Se não for
possível gravar o request, o cliente bloqueia o envio.

`run-manifest.json` registra o caminho, contagens, SHA-256 e se todos os requests
tiveram uma resposta HTTP ou erro de transporte associado. Os comandos
`scse models verify` e `scse models ping` também gravam em
`runs/openrouter-checks/`. A CLI carrega `.env` da raiz sem substituir variáveis
já exportadas pelo processo.

## Limitações conhecidas

- Os slugs dos 12 modelos foram localizados no catálogo do OpenRouter; a chave configurada retornou `401 User not found` nas chamadas de geração e precisa ser substituída antes de validar o acesso aos modelos.
- O comportamento padrão do OpenRouter para `response_format` sem `require_parameters` e a tradução de `reasoning.effort` por host vêm de fontes secundárias. O adaptador exige os parâmetros justamente por isso.
- Os adaptadores reais foram testados com clientes simulados (formato da requisição e parsing), não contra as APIs. Rode `scse models ping` antes da primeira execução.
- O schema do turno usa `anyOf` para campos anuláveis. Se algum provider recusar o schema, use `structured_output = "json_mode"` naquele provider; a validação local continua garantindo o contrato.
- Sem preço declarado (OpenAI, xAI e Gemini), o custo desses providers sai como desconhecido e só o `tokenBudget` os limita.
- Fora do escopo desta versão: verificação online de fontes, decomposição normativa em SHACL, API REST e SCSE Studio.
