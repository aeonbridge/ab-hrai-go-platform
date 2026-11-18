# Progresso da ESP-ONT-02 (loop de execução)

Registro de cada iteração do roteiro `EXECUCAO_LOOP.md`. Referência de aceite: RT-VIS-03, apêndice A (V-01 a V-31).

## Concluído

### Item 1 · RF-15 slide + selo "sem lastro" (início do RF-12) — 17/11/2026

- **O que mudou**
  - `scripts/ontologia/lastro.py`: contador dos sete conjuntos exibidos (`web/assets/modelo.js`). Só conta como lastro o
    `skos:exactMatch` (em `ontologies/regulatory/alinhamentos/`) para um indivíduo que existe no grafo; `closeMatch`
    fica como "próximo, pendente de revisão" e continua sem lastro. Gera `web/assets/lastro.js`, sem data, reprodutível.
  - Câmara (`web/ao-vivo`): selo na ficha de componente, área, estrato, tensão e cadeira vazia (exato, próximo ou sem lastro).
  - Apresentação (`web/apresentacao`): o slide "Por trás da imagem" lê o contador. Com contador > 0 diz "ontologia em
    construção" e quantas peças já são indivíduos; a frase "cada peça é um indivíduo da ontologia" só aparece com zero.
  - CI (`validate-regulatory.yml`): `lastro.py --check --base-ref HEAD~1` falha se `lastro.js` estiver desatualizado ou
    se o contador subir (no total ou em qualquer conjunto).
  - Teste: `tests/test_lastro.py` (4 testes).
- **Comandos**
  - `python3 tests/verify_regulatory_ontology.py` → OK, 1557 triplas, 23 regras SWRL seguras.
  - `python3 tests/verify_regulatory_instances.py` → OK, 1057 triplas.
  - `python3 scripts/ontologia/experimentos.py` → OK.
  - `python3 scripts/ontologia/afirmacoes.py` → 6 com evidência, 4 contestadas, 2 sem evidência.
  - `python3 scripts/ontologia/lastro.py` → 5 com lastro, 83 sem lastro, de 88.
  - `python3 -m pytest -q tests/test_lastro.py` → 4 passed.
- **Medido**: componentes 5/22, áreas 0/28, traços de contexto 0/14, estratos 0/8, tensões 0/6, ramos 0/4, cadeiras vazias 0/6.
- **Pendente**: zerar o contador é o item 8 (RF-09/RF-12); os 5 componentes "próximos" dependem da revisão A1.

### Item 2 · RF-17 separar núcleo e SCSE — 17/11/2026

- **O que mudou**
  - SCSE 1.1.0 com namespace próprio (`.../ontology/scse#`), sem `example.org`, com `owl:imports` do núcleo.
  - Deixou de redeclarar 8 classes e a propriedade `claimText`; passou a usar as do núcleo. Termos homônimos com sentido
    diferente ganharam nome próprio (`provisionStateHasStatus`, `positionGroundedInEvidence`).
  - Classes de deliberação com casa na SCSE e `owl:equivalentClass` para as do núcleo (compatibilidade com instâncias e
    regras R07/R21). Alinhamentos `PolicyTension ⊑ RegulatoryTension`, `ArgumentClaim ⊑ PolicyClaim`, `EvidenceRecord ⊑ Evidence`.
  - `ontologies/scse/README.md` novo; README do núcleo atualizado; CI roda `tests/test_modulos.py` e `tests/test_lastro.py`.
- **Comandos**: os quatro do protocolo com exit 0; `pytest tests/test_modulos.py` → 4 passed. As 8 regras da SCSE que
  disparavam antes disparam igual depois (mesma contagem por regra), agora com o núcleo importado (32 regras no total).
- **Aceite RF-17**: nenhum termo declarado nos dois módulos (teste); testes dos dois módulos passam.

### Item 3 · RF-03 TBox v1.2.0, regras R24–R30, invariantes, tempo no CI — 17/11/2026

- **O que mudou**
  - Núcleo 1.2.0: 14 classes, 34 propriedades de objeto e 5 de dados com comentário em cada uma; vocabulários
    controlados (tipos de correspondência, dimensões da QN1, tipos de diferença). Regras R24a/b/c, R25a/b e R26.
  - SCSE 1.2.0: `DecisionRecord`, revisão de posição, posições sobre alternativas, estrato do stakeholder; R29a/b e R30.
  - `scripts/ontologia/swrl_texto.py`: converte SWRL textual em `swrl:Imp`; `raciocinar.py` ganhou `swrlb:notEqual`.
  - Testes: `tests/verify_regulatory_ontology.py` estendido (29 regras, classes v1.2.0, cabeças proibidas);
    `tests/test_invariantes.py` (regras novas sobre fixture, I-1 a I-4, tempo do grafo completo).
- **Decisões de modelagem**: R27 não existe (sem negação em SWRL); R28 vai para o módulo comparativo no item 4, porque
  combina valores dos critérios; R29–R30 ficam no SCSE (casa da deliberação desde o RF-17).
- **Comandos**: os quatro do protocolo com exit 0; `build_regulatory_instances.py --check` OK; pytest dos módulos,
  lastro e invariantes → 27 passed. Grafo completo (núcleo, SCSE, instâncias, cenários, afirmações, alinhamentos):
  5105 triplas em 0,12 s (RNF-02 < 5 s).
- **Pendente**: R28 (item 4).

### Item 4 · RF-16 (formalização) módulo comparativo — 17/11/2026

- **O que mudou**
  - `ontologies/comparativo/` (novo módulo, importa o núcleo): 12 categorias e 25 critérios de Alanoca et al. com as
    definições originais (copiadas literalmente da seção 5.1; "Scope" a partir das Tabelas 1 a 10), E1 a E7 com crédito
    e DOI, perfil de desenho e regra R28.
  - `alanoca2025-definicoes.json`: definições congeladas; o teste confere cada uma contra o texto do PDF.
  - `scripts/ontologia/build_comparativo.py` gera o módulo (com `--check` no CI).
  - `docs/especificacoes/ESP-ONT-02/escalas-E4-proposta.md`: escala proposta para cada um dos 25 critérios e para as
    extensões, com exemplos tirados do que o paper registra para o Brasil. **Aguarda aprovação (D-02).**
- **Observação**: o paper divide "Existing agency" e "Dedicated new agency" nas tabelas por país; a seção 5.1 trata as
  duas como um critério ("Existing Agency or New Agency"). O módulo segue a seção 5.1, o que dá os 25 critérios.
- **Divergência registrada** para o item 11: C18 (Technical Expertise) está como ausente no paper para o Brasil, mas o
  texto do Senado cria o comitê de especialistas (CECIA); resolver contra o texto primário (tese C04).
- **Comandos**: os quatro do protocolo com exit 0; `pytest tests/test_comparativo.py` → 7 passed; R28 dispara só com
  codificações justificadas e aprovadas (fixture).

### Item 5 · RF-05 esquema `SubstantiveArea` — 17/11/2026

- **O que mudou**
  - `ontologies/comparativo/areas.json` + `build_comparativo.py`: 29 áreas (`hrai:SubstantiveArea` e `skos:Concept`),
    as 28 da cúpula e "IA generativa e modelos de propósito geral". Mapeamento proposto para funções do NIST AI RMF,
    capítulos do AI Act e critérios da taxonomia, marcado como pendente de revisão em cada área.
  - Núcleo: anotação `hrai:displayKey` liga um indivíduo ao elemento exibido (`topics:<id>`); o contador de lastro a usa.
  - Contador: áreas 28/28 com lastro; total 33 com lastro e 55 sem lastro, de 88 (antes 5 e 83).
- **Aceite RF-05**: parcial. As áreas da cúpula têm o mesmo id e rótulo no esquema e em `modelo.js` (teste), mas
  `modelo.js` ainda não é gerado do esquema; a geração é o item 8.
- **Comandos**: protocolo com exit 0; pytest (módulos, lastro, invariantes, comparativo, nomenclatura) → 35 passed.

### Item 6 · RF-13 tensões, estratos, assentos e cenários na SCSE — 17/11/2026

- **O que mudou**
  - `ontologies/scse/conselho/GOV-BR-001.ttl` (fonte nova): 8 estratos, 20 assentos, 6 cadeiras vazias com motivo,
    6 tensões-semente ligadas a afirmações do núcleo (T1→C07; T2→C08, C11, C12; T3→C03; T4→C01, K01, C02;
    T5→C04, C07; T6→C05, K05, K09) e 4 ramos ligados ao PL 2338 ou ao PBIA. Ligações marcadas como proposta.
  - SCSE: propriedades `tensionBetweenStrata` e `branchConcernsInstrument`.
  - `ontologies/consultas/V16_sementes_sem_ligacao.rq`: zero linhas.
  - Contador: 57 com lastro, 31 sem lastro, de 88 (estratos, tensões, ramos e cadeiras vazias completos).
- **Aceite RF-13**: parcial. Cada semente aponta para as afirmações (consulta V-16 = 0). "Câmara e mural leem tensões
  da SCSE" depende de gerar `modelo.js` do grafo (item 8).
- **Comandos**: protocolo com exit 0; pytest → 38 passed.

### Item 7 · RF-08 consultas PC1–PC9 + regressão no CI — 17/11/2026

- **O que mudou**
  - `ontologies/consultas/PC1..PC9_*.rq` (SPARQL versionado, PC9 = QN1) e `README.md` com a pergunta de cada uma.
  - `scripts/ontologia/consultas.py`: raciocina sobre o grafo completo e roda as consultas; grava
    `consultas-resultado.json`; `--check` falha se uma consulta quebrar ou perder linhas (CI).
  - `tests/test_consultas.py`: as nove versionadas; regressão no grafo real; cada PC responde certo sobre fixture.
  - Scripts ignoram arquivos `._*` (AppleDouble do disco exFAT), que quebravam a leitura.
- **Respostas hoje**: PC6 26 linhas, PC7 6, PC8 5; PC1, PC2, PC3, PC4, PC5 e PC9 com zero linhas porque dependem das
  extrações (itens 11, 12) e das especificidades (item 16). Zero linhas = nada registrado, não "não existe".
- **Comandos**: protocolo com exit 0; `consultas.py --check` OK; pytest → 3 passed (consultas).

### Item 8 (parte A) · lastro zero com sementes; método de extração documentado — 17/11/2026

- **Decisão do autor**: elementos de documentos-semente são criados automaticamente e contam como lastro, com o estado
  "semente" visível na ficha; a metodologia fica explícita.
- **O que mudou**
  - `docs/especificacoes/ESP-ONT-02/METODO_EXTRACAO.md`: três origens (fonte primária, documento-semente, análise
    externa), passos da semeadura, mapeamento de campos, estados de lastro, o que o método não faz.
  - `scripts/ontologia/semear.py` (determinístico, sem LLM) → `ontologies/regulatory/sementes/GOV-BR-001_sementes.ttl`:
    17 componentes e 14 traços de contexto, cada um com snapshot do documento-semente (SHA-256), fontes citadas,
    `displayKey` e `CandidateAssertion` no lote `Lote_Sementes_GOV_BR_001`; nenhuma decisão de revisão.
  - Traços sem fonte real (sem fonte ou só "Brasil fictício", `BRF-*`) marcados `seedHasRealSource false`; asserções
    do documento marcadas como "hipótese de trabalho".
  - Núcleo: anotações `seedSourceId`, `seedVerification`, `seedBasis`, `seedHasRealSource`.
  - Contador: **88 de 88 com lastro (31 sementes), 0 sem lastro**. Selo "Semente ... pendente de revisão" na câmara;
    o slide passa a dizer que cada peça é indivíduo da ontologia e quantas ainda são sementes.
  - RT-VIS-03, M2: parágrafo sobre as três origens e os documentos-semente (PDF recompilado).
- **Comandos**: protocolo com exit 0; `semear.py --check`, `lastro.py --check` e `consultas.py --check` OK; pytest
  (todos os `tests/test_*.py`) → 162 passed.
- **Pendente (parte B)**: gerar `modelo.js` do grafo (RF-09) e "por quê?" até a fonte nas fichas (V-14, V-19).

### Item 8 (parte B) · `modelo.js` gerado do grafo; "De onde vem" e "Por quê?" nas fichas — 17/11/2026

- **O que mudou**
  - `scripts/ontologia/build_modelo.py` gera `web/assets/modelo.js` e `web/assets/grafo.js` do grafo (componentes e
    traços das sementes, áreas do módulo comparativo, estratos, tensões, ramos e cadeiras vazias da SCSE). A força de
    cada área é derivada dos componentes com a regra que a câmara já usava (conferida nas 28 áreas antes da troca).
  - Semeadura cobre os 22 componentes; os 5 exatos apontam para o indivíduo de fonte primária (`skos:exactMatch`).
  - Núcleo: anotações de apresentação `seedKind`, `seedLegalStatus`, `seedTopicsBasis`, `seedArea`, `displayOrder`.
  - Câmara: ficha com "De onde vem" (indivíduo, documento de origem com SHA-256, fontes citadas, fonte primária,
    afirmações, revisão) e "Por quê?" da força de cada área.
  - CI: `build_modelo.py --check` falha se `modelo.js` for editado à mão ou divergir do grafo.
  - Única diferença visível: a ordem interna de duas listas (tópicos de um componente, estratos de uma tensão) passou
    a seguir a ordem de exibição, porque RDF não guarda ordem; só afeta texto da ficha.
- **Comandos**: protocolo com exit 0; os quatro `--check` (sementes, lastro, modelo, consultas) OK; pytest → 163 passed.

### Item 9 · RF-01 texto do Senado como nova versão do PL — 17/11/2026

- **O que mudou**
  - `scripts/ontologia/extrair_pl2338.py` (pdftotext + expressões regulares, sem LLM) →
    `ontologies/regulatory/instances/br/HRAI_GO_Regulatory_BR_PL2338.ttl` (+ `.owl`): duas versões de
    `pbia:PL_2338_2023` (texto inicial de 03/05/2023 e texto aprovado pelo Senado em 10/12/2024, com
    `previousLegalVersion`), 45 e 79 artigos com citação, caput, texto integral, capítulo e seção, cada um documentado
    no snapshot do PDF (SHA-256). Evento de mudança do texto do Senado; um candidato por versão; nenhuma decisão.
  - **Observado**: o texto do Senado numera até o art. 80, mas o art. 31 não aparece no documento (79 artigos).
    Registrado na versão; o `EXECUCAO_LOOP.md` dizia "80 artigos".
  - Raciocínio: os 124 dispositivos são inferidos como `ProposedProvision` (R22, sem força vinculante) e com
    jurisdição (R01); a mudança reabre potencialmente os 79 artigos (R10), e a PC7 passou de 6 para 85 linhas.
  - CI instala `poppler-utils` e confere que a extração é reprodutível a partir dos PDFs.
- **Aprovação**: humana (D-03). **Comandos**: protocolo com exit 0 (instâncias: PBIA e PL validados); pytest → 168 passed.

### Item 10 · RF-11 teses com estado recalculado; tese C04 reavaliada — 17/11/2026

- **O que mudou**
  - Afirmações (`A1_analise_comparativa_BR_AIAct.ttl`): cada evidência do PL aponta o artigo extraído do PDF de 2023;
    evidência nova `Ev_PL2024_Art54` (texto do Senado, art. 54, cria o Cecia) sustenta a contra-afirmação K04.
  - **C04 reavaliada**: continua contestada, agora pelo texto primário; nota registra que a pergunta aberta é
    independência e mandato do Cecia frente ao painel do art. 68 do AI Act. Classificação geral inalterada: 6 com
    evidência, 4 contestadas, 2 sem evidência.
  - **Divergência encontrada** (para revisão): a evidência rotulada "art. 33, parágrafo único" (condições diferenciadas
    para micro e pequenas empresas e startups) aparece, na extração do PDF de 2023, antes do art. 33, no art. 32.
  - `tests/test_afirmacoes.py` no CI: o estado gravado tem de ser igual a um recálculo a partir do grafo (V-17).
  - Apêndice de afirmações da ESP-ONT-02 regenerado e PDF recompilado.
- **Comandos**: protocolo com exit 0; pytest → todos passam.

### Item 11 · RF-04 / RF-06 / RF-14 instâncias UE, Reino Unido e EUA; correspondências — 17/11/2026

- **O que mudou**
  - `scripts/ontologia/extrair_internacional.py` (pdftotext + expressões regulares, sem LLM):
    - UE: AI Act (Regulamento 2024/1689) como norma vigente, versão de 12/07/2024 e os **113 artigos** com título,
      capítulo, seção e texto integral;
    - Reino Unido: white paper de 2023 como instrumento não estatutário (E1), com a frase "will not put these
      principles on a statutory footing initially" e os **5 princípios** com a definição literal; análise de impacto
      capturada como snapshot;
    - EUA: NIST AI RMF 1.0 como guia voluntário (E1), com as **4 funções** e a definição literal.
    Cada documento com `SourceSnapshot` (SHA-256 conferido no teste) e candidato pendente.
  - `scripts/ontologia/correspondencias.py`: **18 correspondências** candidatas entre o texto do Senado e o AI Act
    (13 adaptadas, 4 parciais, 1 divergente), cada uma com a justificativa e a área. É julgamento de leitura (análise
    assistida por LLM), não extração; sem revisão humana, R26 não infere transposição (testado). PC2: 18 linhas.
  - CI confere que extração e correspondências são reprodutíveis.
- **Fica para depois**: codificações nos 25 critérios (V-08) dependem das escalas aprovadas (D-02); registrar ao lado
  as codificações descritivas dos autores do paper para a concordância (V-09).
- **Comandos**: protocolo com exit 0 (5 arquivos de instância validados); pytest → todos passam.

### Item 12 · RF-07 indicadores de capacidade e exposição — 17/11/2026

- **O que mudou**
  - Núcleo: `hrai:baseYear` (ano ou período como a fonte informa; "não informado na fonte" quando não informa).
  - `instances/br/HRAI_GO_Regulatory_BR_Capacidade.ttl` (candidato): ano-base dos 16 indicadores do PBIA (7 com ano
    na fonte, 9 sem); orçamento de governança do Eixo 5 (R$ 103,25 milhões, 0,45% dos R$ 23,03 bilhões, conferido na
    Tabela 2); exposição qualitativa dos dados de saúde do SUS; três requisitos do texto do Senado que pressupõem
    capacidade (arts. 25, 34 e 49), ligados à capacidade de orçamento e de profissionais técnicos.
  - PC3 ganhou o caso "indicador sem limiar": com indicador e sem limiar aprovado, não há sinal, há falta de critério.
    PC3: 8 linhas. PC4 continua em zero: exige `CoverageAssessment` (escopo declarado), que é decisão de método.
  - Nenhum limiar fixado pela sessão (teste); proposta de limiar vai para a fila (D-09).
- **"Os mesmos para todas as jurisdições"**: o corpus não traz indicadores equivalentes de UE, Reino Unido e EUA
  (orçamento de supervisão, profissionais); nas comparações eles aparecem como "não codificado" (item 16).
- **Comandos**: protocolo com exit 0 (6 arquivos de instância validados); pytest → 179 passed.

### Item 13 · M10 monitoramento: o que uma mudança reabre — 17/11/2026

- **O que mudou**
  - PC7 ampliada: além de dispositivos, requisitos, avaliações e aplicações (R10 a R13), reabre codificações (E5),
    especificidades da QN1 e afirmações cuja evidência cita dispositivo da versão anterior. PC7: 92 linhas.
  - `scripts/ontologia/monitorar.py` gera `web/assets/monitoramento.js`; a página Monitoramento do site mostra
    "Reaberto no grafo" acima do pulso normativo: o texto do Senado reabre 79 dispositivos, 3 requisitos e 4
    afirmações (entre elas a C04); o evento ilustrativo do cenário E1 aparece marcado como ilustrativo.
  - `tests/test_monitoramento.py` e `monitorar.py --check` no CI.
- **Comandos**: protocolo com exit 0; pytest → todos passam.

### Itens 16 e 17 · RF-18 especificidades (QN1) e relatório das perguntas norteadoras — 17/11/2026

- **Como foi feito**: o passo M5 pede todas as jurisdições na mesma régua; as codificações esperam as escalas (D-02).
  Nesta primeira execução a detecção foi feita pela sessão sobre o grafo, item a item (análise assistida por LLM), e
  cada linha cita os indivíduos do grafo em que se apoia. Comparação sem valor equivalente no corpus = "não codificado".
- **O que mudou**
  - Núcleo: anotações `answersGuidingQuestion` e `answerScope`.
  - `scripts/ontologia/responder_qn.py` → `ontologies/regulatory/respostas/QN_respostas.ttl`:
    - **QN1, 8 especificidades**: soberania computacional com orçamento (S1), LLM em português (S2), matriz renovável
      (S3), orçamento de governança de 0,45% (S4), déficit de 530 mil profissionais de TIC (S5), dados de saúde do SUS
      (S6), supervisão por sistema que coordena reguladores existentes (S7, comparada com o art. 70 do AI Act e com o
      Reino Unido), responsabilidade civil pelo CDC e Código Civil com inversão do ônus (S8). Cada uma com dimensão, tipo,
      evidência brasileira e comparação com UE, Reino Unido e EUA;
    - **QN2, 2 itens**: avaliação de impacto obrigatória sem profissionais (S5); supervisão e acreditação sem orçamento (S4, S7);
    - **QN3, 2 itens**: uso de dados públicos sensíveis (SUS) para treinar modelos sem regra específica (S6); sistema de
      supervisão sem fonte de financiamento própria (S4, S7). Ambos com o escopo declarado (busca/leitura no texto do Senado);
    - **achado**: a "lacuna" de energia e meio ambiente da cúpula vem do modelo-semente; o texto do Senado trata o tema
      (arts. 30, 59, 60, 61). Vai para a revisão das sementes (D-07);
    - correspondências 45×70 e 25×27 ligadas às especificidades que as explicam (PC2).
  - Consultas de aceite `V27`, `V28`, `V30` = zero linhas; PC9 responde (42 linhas).
  - `scripts/ontologia/relatorio_qn.py` → `docs/relatorios/perguntas-norteadoras/relatorio-QN.md` (+ `web/assets/respostas.js`):
    seções QN1, QN2, QN3 nesta ordem, cada item com estado e decisão "pendente", marcado como resposta inicial.
  - CI regenera respostas e relatório e falha se divergirem do grafo; `tests/test_respostas_qn.py`.
- **Comandos**: protocolo com exit 0; pytest → 186 passed.

### Decisão D-01 aplicada · China no corpus — 17/11/2026

- **Decisão do autor**: incluir a China (mensagem "D-01 adicionado", com dois PDFs em `docs/ai-regulations/ch/`).
- **Fontes**: as duas são **secundárias** (Regulations.AI, resumo de 2026 em imagem; Law Library of Congress, relatório de
  junho de 2023). Não há texto oficial chinês no corpus; incluí-lo fica pendente (D-12).
- `scripts/ontologia/extrair_china.py` → `instances/cn/HRAI_GO_Regulatory_CN.ttl`: jurisdição, 14 instrumentos (3 leis,
  6 regras administrativas, 3 normas técnicas não vinculantes, 1 plano, 1 minuta) e 7 autoridades. A lista foi
  transcrita das imagens do resumo pela sessão (LLM); 7 instrumentos também aparecem no relatório da LoC, conferido
  automaticamente. Todos marcados "fonte secundária" e pendentes.
- Especificidades da QN1 ganharam a comparação com a China (V-30 continua em zero); S7 compara com a supervisão
  centralizada pela CAC, segundo fonte secundária.

### Decisões D-02, D-03 e D-04 registradas — 17/11/2026

- **Como**: `docs/especificacoes/ESP-ONT-02/decisoes.json` guarda cada decisão do autor com data e o texto da mensagem;
  `scripts/ontologia/registrar_decisoes.py` gera `ontologies/regulatory/decisoes/decisoes_autor.ttl` com uma
  `ApprovalDecision` por decisão, atribuída ao autor (`ReviewActor`). A sessão transcreve; não decide (I-3, testado).
- **D-02 (escalas da E4 aprovadas)**: `ontologies/comparativo/escalas-E4.json`; o módulo comparativo ganhou os níveis de
  cada escala (`comp:ScaleLevel`, número e rótulo) ligados à decisão.
- **D-03 (extrações revisadas)**: 34 candidatos aprovados (PL 2023 e 2024, AI Act, Reino Unido, NIST, capacidade, 18
  correspondências) e o mapeamento das 29 áreas. Com a revisão, **R26 infere 13 transposições**, exatamente as
  correspondências adaptadas; parciais e divergentes não transpõem (testado).
- **D-04 (alinhamentos e ligações aprovados)**: os 5 componentes "próximos" ficam como correspondência aproximada; as
  ligações tensão→afirmação (T1 a T6) e ramo→instrumento aprovadas. As fichas mostram "aprovado pelo autor (D-04)".
- Fora das decisões (continuam pendentes): PBIA (lote anterior), China (D-12), sementes (D-07), respostas (D-11).

### Decisões D-05 e D-07 registradas — 17/11/2026

- **D-07 (sementes revisadas)**: os 36 candidatos do lote de sementes aprovados pelo autor. Contador: 88 de 88 com lastro,
  0 sementes pendentes, 31 revisadas; o selo da câmara diz "Semente revisada pelo autor" e as fichas, "aprovado pelo
  autor (D-07)"; o slide deixa de mencionar sementes pendentes.
- **D-05 (domínio dos IRIs: aeonbridge.io)**: decisão registrada. Implementar exige escolher o caminho dos IRIs e apontar
  um endereço do domínio para a publicação (DNS fora do repositório); pendente de confirmação dos detalhes (D-05a).

## Aguardando decisão

| Id | Decisão | Quem | Bloqueia |
|---|---|---|---|
| D-01 | ~~China~~ **resolvida em 17/11/2026**: incluída com fontes secundárias | autor | — |
| D-02 | ~~escalas da E4 aprovadas~~ **resolvida em 17/11/2026** (`decisoes.json`) | autor | — |
| D-03 | ~~extrações e correspondências revisadas~~ **resolvida em 17/11/2026** (`decisoes.json`) | autor | — |
| D-04 | ~~alinhamentos e ligações aprovados~~ **resolvida em 17/11/2026** (`decisoes.json`) | autor | — |
| D-05 | ~~domínio dos IRIs~~ **resolvida em 17/11/2026: aeonbridge.io** | autor | — |
| D-05a | Detalhes da D-05: caminho dos IRIs (por exemplo `https://aeonbridge.io/hrai-go/ontology/regulatory#`) e apontamento do domínio para a publicação | autor | V-24 |
| D-07 | ~~sementes~~ **resolvida em 17/11/2026** (`decisoes.json`) | autor | — |
| D-08 | Conferir a localização do parágrafo sobre micro e pequenas empresas e startups no texto de 2023 (art. 32 na extração; art. 33 no rótulo da evidência) | autor | rótulo de `a1:Ev_PL_Art33PU` |
| D-09 | Limiar inferior de alerta para o orçamento de governança (hoje 0,45% do PBIA) e para profissionais técnicos; sem limiar, R25 não sinaliza | autor | PC3 "abaixo do limiar" |
| D-10 | Declarar os escopos de avaliação de cobertura (`CoverageAssessment`: jurisdição, snapshot, área) para a PC4 valer | autor | PC4, QN3 |
| D-11 | Decidir cada item da resposta inicial (8 especificidades da QN1, 2 itens da QN2, 2 da QN3, 1 achado) em `docs/relatorios/perguntas-norteadoras/relatorio-QN.md` | autor | V-26, V-29 |
| D-12 | Incluir textos oficiais chineses (CAC, Assembleia Popular Nacional) para substituir as fontes secundárias | autor | comparações com a China "não codificado" |
| D-06 | PDF da "Análise Comparativa" no repositório (hoje as teses vêm de resumo) | autor | rastreabilidade das teses |

## Checklist V-01 a V-31

Legenda: ✅ verificado com evidência · 🟡 parcial · ⬜ não iniciado · ⏸ depende de decisão humana.

| Id | Estado | Evidência / observação |
|---|---|---|
| V-01 | 🟡 | nome completo no README e relatórios (`tests/test_nomenclatura.py`); conferir site e `dcterms:title` |
| V-02 | ✅ | `SourceSnapshot` com SHA-256 conferido para PBIA, PL 2023, PL 2024, AI Act, white paper e análise de impacto do Reino Unido, NIST AI RMF (`tests/test_internacional.py`) |
| V-03 | ✅ | decisão D-01 registrada (China incluída com fontes secundárias marcadas); nenhuma jurisdição sem snapshot com SHA-256 (`tests/test_china.py`, `tests/test_internacional.py`) |
| V-04 | ✅ | `tests/test_modulos.py` no CI (`validate-regulatory.yml`); item 2 |
| V-05 | ✅ | TBox 1.2.0, R24–R26 (núcleo), R28 (comparativo), R29–R30 (SCSE); I-1 a I-4 em `tests/test_invariantes.py` |
| V-06 | ✅ | `tests/test_comparativo.py`: 25 critérios com definições originais conferidas no PDF, E1–E7 com crédito e DOI |
| V-07 | ✅ | escalas aprovadas pelo autor (D-02), `ApprovalDecision` em `decisoes_autor.ttl`; níveis no módulo comparativo |
| V-08 | ⬜ | escalas aprovadas; falta codificar BR e UE nos 25 critérios com dispositivo de origem |
| V-09 | ⬜ | registrar codificações dos autores do paper e publicar concordância (após D-02) |
| V-10 | ✅ | 18 correspondências revisadas (D-03); sem correspondência pendente; R26 infere 13 transposições |
| V-11 | 🟡 | indicadores do Brasil com fonte e ano-base (teste); PC3 responde (8 linhas: "indicador sem limiar"); PC4 sem `CoverageAssessment`; falta revisão (D-03) e limiar (D-09) |
| V-12 | ✅ | `consultas.py --check` e `tests/test_consultas.py` no CI; cada PC testada sobre fixture |
| V-13 | ✅ | `test_rnf02_full_graph_reasons_under_five_seconds` no CI: 0,12 s para 5105 triplas |
| V-14 | 🟡 | ficha da área mostra o "Por quê?" da força com os componentes; cadeia de regras SWRL até a fonte na interface fica para quando houver inferência exibida de fonte primária (itens 11–12) |
| V-15 | ✅ | `modelo.js` gerado do grafo (`build_modelo.py --check` no CI); contador = 0 sem lastro (88/88, 31 sementes) |
| V-16 | ✅ | `ontologies/consultas/V16_sementes_sem_ligacao.rq` = 0 linhas (`tests/test_conselho.py`, CI) |
| V-17 | ✅ | `tests/test_afirmacoes.py` no CI recalcula as 12 teses e compara com o estado gravado; C04 reavaliada contra o art. 54 do texto do Senado |
| V-18 | 🟡 | celular participante com Minhas escolhas, Mesa e Agora já existe; falta teste de toque (item 15) |
| V-19 | 🟡 | ficha com "De onde vem" em componente, área, estrato, tensão e cadeira vazia; falta teste em aparelho real |
| V-20 | ⬜ | item 14 |
| V-21 | ⬜ | item 14 |
| V-22 | ⬜ | item 14 |
| V-23 | ✅ | texto do Senado como nova versão reabre dispositivos, requisitos e afirmações (`tests/test_monitoramento.py`); codificações e especificidades entram na mesma consulta quando existirem |
| V-24 | ⏸ | domínio decidido (aeonbridge.io, D-05); falta caminho e apontamento (D-05a) |
| V-25 | ⬜ | item 15 |
| V-26 | 🟡 | relatório gerado pela plataforma (`relatorio-QN.md`), seções QN1, QN2, QN3; "publicado" depende das decisões (D-11) |
| V-27 | ✅ | PC9 responde; `V27_especificidades_sem_evidencia.rq` = 0 |
| V-28 | ✅ | `V28_itens_sem_especificidade.rq` = 0 |
| V-29 | ⏸ | 8 especificidades e 4 itens aguardam decisão humana (D-11) |
| V-30 | ✅ | `V30_especificidades_incompletas.rq` = 0: dimensão, tipo e comparação com UE, Reino Unido e EUA em todas |
| V-31 | ✅ | `tests/test_identificacao_ao_vivo.py`; migração aplicada no Supabase em 17/11/2026 (rejeição por `respostas_nome_check` confirmada); commit 285407a |
