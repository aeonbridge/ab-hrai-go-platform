# Escalas da extensão E4: proposta para aprovação (decisão D-02)

**Estado: proposta, aguardando aprovação humana.** Preparada pela sessão do loop (item 4 do `EXECUCAO_LOOP.md`). Nada
aqui entra na ontologia antes da aprovação: as codificações (`hrai:CriterionCoding`) só usam escalas aprovadas, e a
regra R28 só dispara sobre codificações justificadas por dispositivo e com `ApprovalDecision`.

Critérios: Alanoca et al. (2025), *Comparing Apples to Oranges*, FAccT '25, doi:10.1145/3715275.3732059, com as
definições originais em `ontologies/comparativo/alanoca2025-definicoes.json`. A escala não muda a definição do critério;
ela só torna o valor comparável e rastreável (E4).

**Como ler os exemplos.** A coluna "Exemplo" aplica a escala ao texto que o próprio paper registra para o Brasil
(Tabelas 9 e 10, PL 2338 no texto aprovado pelo Senado). São exemplos de uso da escala, não codificações do projeto:
a codificação de verdade (item 11) cita o dispositivo do texto primário e passa por revisão.

Regra geral proposta para critérios de presença: **0** ausente · **1** previsto de forma genérica, sem regra
operacional ou com dúvida · **2** previsto com regra operacional (quem, como, quando).

| Critério | Escala proposta | Exemplo (PL 2338, texto do Senado, segundo o paper) |
|---|---|---|
| C01 Law adoption | 0 sem texto formal · 1 proposta em tramitação · 2 aprovada em uma casa · 3 adotada | 2 ("approved by the Brazilian Senate") |
| C02 Novelty of legal regime | 0 adapta marco existente · 1 misto · 2 lei nova específica para IA | 2 ("New law") |
| C03 Maturity of AI-relevant regulatory landscape | 0 incipiente · 1 emergente · 2 intermediário · 3 maduro | 1 ("emerging digital regulatory environment") |
| C04 Applies to Generative AI | 0 não se aplica · 1 menção secundária · 2 regras específicas | 2 ("Applies to general purpose AI ... and generative AI") |
| C05 Industry | 0 não visa · 1 visa de forma secundária · 2 alvo principal | 2 ("Law targets industry") |
| C06 Government/Federal Agencies | idem C05 | 1 ("Not primarily targeting government"): revisar se 0 ou 1 |
| C07 Individuals/Citizens | idem C05 | 1 ("Not primarily targeting individuals"): revisar se 0 ou 1 |
| C08 Continued Reporting | presença (0–2) | 2 (registro e documentação da avaliação preliminar) |
| C09 Third-Party Audits | presença (0–2) | 1 (auditoria pela autoridade competente, não por terceiro independente) |
| C10 Existing Agency or New Agency | 0 só agências existentes · 1 sistema que coordena as existentes · 2 agência nova | 1 (Sistema Nacional de Regulação e Governança de IA, SIA) |
| C11 Liability | presença (0–2) | 2 ("Includes a liability regime") |
| C12 Regulatory Sandboxes | presença (0–2) | 2 ("Includes regulatory sandboxes") |
| C13 Criminal Charges | presença (0–2) | 0 ("Not included") |
| C14 Fines | 0 ausente · 1 previstas sem teto · 2 previstas com teto definido | 2 (até R$ 50 milhões ou 2% do faturamento) |
| C15 Temporary Injunctions | presença (0–2) | 1 ("Included"; conferir no texto se há regra operacional) |
| C16 Standard Setting | presença (0–2) | 0 ("Not directly included within the law") |
| C17 Auditing | presença (0–2) | 1 (auditoria pela autoridade competente) |
| C18 Technical Expertise | presença (0–2) | 0 segundo o paper; **divergência a resolver contra o texto primário**: o texto do Senado cria o comitê de especialistas (CECIA) no SIA (tese C04) |
| C19 International Cooperation | 0 sem alinhamento · 1 alinha definições · 2 alinhamento explícito a marcos globais | 1 (definições da OCDE e classificação do AI Act) |
| C20 Civil Society Inclusion | 0 ausente · 1 baixa · 2 média · 3 alta | 3 ("higher level of inclusion of civil society") |
| C21 Private Sector Inclusion | idem C20 | 2 ("Inclusion of private stakeholders") |
| C22 Ex Ante | 0 nenhum · 1 baixo · 2 médio · 3 alto | 3 ("High level of ex ante requirements") |
| C23 Ex Post | idem C22 | 2 ("Medium level of ex post remedies") |
| C24 Technology-Focused | 0 não · 1 camada secundária · 2 camada principal | 1 ("as a secondary regulatory layer") |
| C25 Application-Focused | idem C24 | 2 ("Primarily targets context or application based AI") |

Extensões:

| Extensão | Escala proposta | Exemplo |
|---|---|---|
| E1 Forma jurídica | categórica: 0 guia voluntário · 1 princípios não estatutários · 2 plano ou estratégia · 3 lei ou projeto de lei | PBIA 2 · white paper do Reino Unido 1 · NIST AI RMF 0 · PL 2338 3 |
| E2 Objetivo primário | categórica, sem ordem: direitos · inovação · desenvolvimento e soberania · segurança (`codingValueLabel`) | PBIA: desenvolvimento e soberania |
| E3 Cobertura substantiva | por área: 0 sem cobertura · 1 só em proposta ou plano · 2 em instrumento vigente (R24a/b/c) | — |
| E5 Versão | não é escala: toda codificação aponta a versão (`codingSubject`) | PL 2338 de 2023 e de 2024 codificados separadamente |
| E6 Capacidade de implementação | 0 sem indicador · 1 indicador abaixo do limiar (R25a) · 2 indicador no limiar ou acima | Eixo 5 do PBIA (0,45% do plano, tese C07): depende do indicador do item 12 |
| E7 Participação na implementação | idem C20 (0 a 3) | — |

**Dependência na ontologia.** A regra R28 (perfil "regulação horizontal por risco") usa E1 = 3, C22 ≥ 3 e C25 ≥ 2. Se
as escalas aprovadas forem diferentes, a regra é ajustada no mesmo commit da aprovação.

**Para aprovar:** marque cada linha como aprovada, ajustada ou rejeitada (pode ser neste arquivo). A sessão então grava
as escalas aprovadas como `skos:Concept` de valor, com a decisão humana registrada.
