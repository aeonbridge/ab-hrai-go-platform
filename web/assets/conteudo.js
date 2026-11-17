/* Conteúdo editável do observatório. Estado em nov/2026.
   Itens com status "Verificar" vêm de conhecimento prévio e precisam de checagem em fonte primária. */
window.HRAIGO_CONTEUDO = {
  setores: [["gov","Governo federal"],["reg","Agência reguladora"],["leg","Legislativo"],["est","Estados e municípios"],["aca","Academia"],["soc","Sociedade civil"],["pri","Setor privado"],["out","Outro"]],
  tensoes: [
    ["t1","Testar viés com dados sensíveis × minimização de dados",4],
    ["t2","Auditoria ex-ante obrigatória × viabilidade para pequenas empresas",4],
    ["t3","Revisão humana efetiva × escala operacional",3],
    ["t4","Explicação ao cidadão × segredo comercial do modelo",2],
    ["t5","Prazo curto de vigência × capacidade de fiscalização",2]
  ],
  polos: ["Auditoria ex-ante obrigatória", "Viabilidade para pequenas empresas"],
  /* assentos sintéticos do Conselho das Sombras: código, perspectiva, posição no eixo (-1 a 1) */
  assentos: [["DD","Direitos digitais",-.7],["TR","Trabalhadores",-.6],["PE","Pequenas empresas",.55],["FI","Fiscalização",.35],["GP","Grandes plataformas",.15],["AA","Auditoria algorítmica",-.25]],
  /* leitura sintética de adequação ao Brasil em capacidade estatal de fiscalização (-2 a 2) */
  criterio: "capacidade estatal de fiscalização",
  modelos: [["ue","UE",-1],["us","EUA",1],["cn","China",-2],["uk","Reino Unido",1],["br","Brasil",0]],
  movimentos: [["support","Sustentar"],["challenge","Contestar"],["evidence","Pedir evidência"],["amend","Propor alternativa"]],

  jurisdicoes: [
    {id:"br",n:"Brasil",modelo:"Risco (PL 2338), investimento (PBIA) e proteção de dados (LGPD)",itens:[
      {t:"PL 2338/2023 · marco legal da IA",st:["Em tramitação","atencao"],d:"Aprovado no Senado em 10/12/2024. Comissão especial instalada na Câmara em 20/05/2025; em out/2026 aguardava parecer do relator, que anunciou votação para depois das eleições.",rel:"Define o regime de risco que orientaria a fiscalização. Enquanto não é lei, requisitos derivados dele são prospectivos.",f:[["Câmara dos Deputados","https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2487262"]]},
      {t:"PBIA 2024–2028 · Plano Brasileiro de IA",st:["Em execução","ok"],d:"Cerca de R$ 23 bi em cinco eixos: infraestrutura (~R$ 5,8 bi), formação (~R$ 1,15 bi), serviços públicos (~R$ 1,76 bi), inovação empresarial (~R$ 13,8 bi) e regulação e governança (~R$ 103 mi). Valores por eixo de apresentações do MCTI citadas por fontes secundárias.",rel:"O Eixo 5 financia o apoio ao processo regulatório e é pequeno diante dos demais.",f:[["MCTI","https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/transformacaodigital/plano-brasileiro-de-inteligencia-artificial"]]},
      {t:"LGPD · art. 20",st:["Em vigor","ok"],d:"Direito de solicitar revisão de decisões tomadas unicamente com base em tratamento automatizado.",rel:"Principal gancho legal vigente para decisões automatizadas.",f:[["Planalto · Lei 13.709/2018","https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"]]},
      {t:"Sandbox regulatório de IA da ANPD",st:["Piloto","ok"],d:"Primeiro ciclo de testagem iniciado em 18/03/2026, com três participantes; metodologia do CIAAM/USP.",rel:"Experiência concreta de regulação experimental no país.",f:[["ANPD · relatório de monitoramento","https://www.gov.br/anpd/pt-br/assuntos/projetos-acoes-iniciativas/sandbox/relatorio-1-de-monitoramento_ciclo-testagem_albert-franca-josua.pdf/@@display-file/file"]]},
      {t:"Consultas públicas ligadas ao PBIA",st:["Encerradas","atencao"],d:"Guia de uso ético de IA do MJSP (Ação 50 do Eixo 5, até 19/04/2026); diretrizes de IA na educação (MEC, out/2025; CNE, até jun/2026), na plataforma Brasil Participativo.",rel:"Geram contribuições que precisam de síntese rastreável, caso de uso direto desta plataforma.",f:[["Agência Gov","https://agenciagov.ebc.com.br/noticias/202603/mjsp-abre-consulta-publica-sobre-guia-de-uso-etico-de-inteligencia-artificial-1"]]}]},
    {id:"ue",n:"União Europeia",modelo:"Risco, horizontal, conformidade ex ante",itens:[
      {t:"AI Act · Regulamento (UE) 2024/1689",st:["Em vigor, escalonado","ok"],d:"Proibições, alfabetização em IA, obrigações de modelos de propósito geral e transparência do art. 50 mantêm o calendário original.",rel:"Principal referência do PL 2338.",f:[["AI Act Explorer","https://artificialintelligenceact.eu/ai-act-explorer/digital-omnibus/"]]},
      {t:"Digital Omnibus on AI · Regulamento (UE) 2026/1744",st:["Em vigor desde 27/07/2026","ok"],d:"Adiou o alto risco: sistemas do Anexo III a partir de 02/12/2027 e IA embarcada em produtos (Anexo I) a partir de 02/08/2028. Marca d'água de sistemas existentes até 02/12/2026.",rel:"O adiamento mostra o custo de capacidade estatal e de normas técnicas que um regime de risco exige.",f:[["Gibson Dunn","https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/"]]}]},
    {id:"us",n:"Estados Unidos",modelo:"Mercado, setorial, responsabilização ex post",itens:[
      {t:"EO 14365 · preempção de leis estaduais",st:["Em vigor","ok"],d:"Dez/2025: força-tarefa no Departamento de Justiça para contestar leis estaduais de IA. Ordem executiva não revoga lei estadual; até ago/2026 não havia lei federal de preempção.",rel:"Os EUA são o fornecedor dominante de modelos e chips usados no Brasil.",f:[["Ropes & Gray","https://www.ropesgray.com/en/insights/alerts/2026/03/the-white-house-legislative-recommendations-national-policy-framework-for-artificial-intelligence-an"]]},
      {t:"Leis estaduais",st:["Em disputa","atencao"],d:"Estados seguem legislando; a aplicação da lei do Colorado foi pausada por ordem de 27/04/2026 (fontes secundárias).",rel:"Mosaico regulatório encarece a conformidade para empresas pequenas.",f:[["SecurePrivacy","https://secureprivacy.ai/blog/trump-ai-executive-order-and-state-law-preemption-what-to-do-now"]]}]},
    {id:"cn",n:"China",modelo:"Dirigido pelo Estado, registro e rotulagem",itens:[
      {t:"Registro de algoritmos e medidas para IA generativa",st:["Em vigor","ok"],d:"Registro de algoritmos de recomendação e medidas provisórias para IA generativa (2023).",rel:"Referência de soberania tecnológica, com custos para direitos.",f:[]},
      {t:"Rotulagem de conteúdo sintético",st:["Verificar","atencao"],d:"Medidas de rotulagem de conteúdo gerado por IA em vigor desde set/2025, segundo conhecimento prévio.",rel:"Comparável ao art. 50 do AI Act.",f:[]}]},
    {id:"uk",n:"Reino Unido",modelo:"Princípios aplicados por reguladores setoriais",itens:[
      {t:"Abordagem pró-inovação por princípios",st:["Verificar","atencao"],d:"Sem lei geral de IA até onde verificado; reguladores existentes aplicam princípios. Padrão de transparência algorítmica no setor público.",rel:"Alternativa de menor custo estatal inicial.",f:[]}]},
    {id:"as",n:"Ásia-Pacífico",modelo:"Leis-quadro de promoção com obrigações seletivas",itens:[
      {t:"Coreia do Sul · Lei Básica de IA",st:["Verificar","atencao"],d:"Aprovada em dez/2024, com vigência prevista para jan/2026, segundo conhecimento prévio.",rel:"Combina fomento e obrigações para IA de alto impacto.",f:[]},
      {t:"Japão · Lei de Promoção de IA",st:["Verificar","atencao"],d:"Lei de 2025 centrada em coordenação e fomento, segundo conhecimento prévio.",rel:"Contraponto ao modelo regulatório europeu.",f:[]}]},
    {id:"ml",n:"Multilateral",modelo:"Princípios e tratados",itens:[
      {t:"Princípios de IA da OCDE",st:["Vigentes","ok"],d:"Adotados em 2019 e revisados em 2024; o Brasil aderiu.",rel:"Vocabulário comum entre países.",f:[]},
      {t:"Recomendação da UNESCO sobre ética da IA",st:["Vigente","ok"],d:"Adotada em 2021 pelos Estados-membros.",rel:"Referência para avaliação ética no setor público.",f:[]},
      {t:"Convenção-Quadro do Conselho da Europa sobre IA",st:["Verificar","atencao"],d:"Primeiro tratado internacional sobre IA, aberto à assinatura em set/2024; adesões a verificar.",rel:"Possível referência vinculante para países fora da UE.",f:[]}]}
  ],

  /* data, escopo (br | mu | fut), título, descrição, efeito na ontologia HRAI-GO */
  eventos: [
    ["2024-07-30","br","PBIA apresentado","Plano Brasileiro de IA 2024–2028, cerca de R$ 23 bi.","R03 liga os instrumentos do plano ao Brasil"],
    ["2024-12-10","br","Senado aprova o PL 2338/2023","Texto segue para a Câmara.","Nova versão de proposta legislativa; R22 e R23 marcam dispositivos e requisitos como prospectivos"],
    ["2025-05-20","br","Comissão especial instalada na Câmara","Relator: dep. Aguinaldo Ribeiro.",""],
    ["2025-09-01","mu","China: rotulagem de conteúdo sintético","Data segundo conhecimento prévio; verificar.",""],
    ["2025-12-11","mu","EUA: EO 14365","Força-tarefa federal contra leis estaduais de IA.","Evento de mudança regulatória externo"],
    ["2026-03-18","br","ANPD inicia o 1º ciclo do sandbox de IA","Três participantes; metodologia CIAAM/USP.",""],
    ["2026-03-20","mu","EUA: diretrizes da Casa Branca para preempção","Documento não vinculante.",""],
    ["2026-04-09","br","Chamada do FIP de IA (BNDESPAR/Finep)","Instrumento financeiro ligado ao PBIA.","Alocação orçamentária; R19 acompanha a execução"],
    ["2026-04-19","br","Encerra consulta do guia ético de IA (MJSP)","Ação 50 do Eixo 5 do PBIA.","Contribuições viram afirmações e posições; R21 separa perspectivas sintéticas"],
    ["2026-07-27","mu","UE: Omnibus de IA entra em vigor","Alto risco adiado para 2027 e 2028.","R10 a R13 marcam requisitos e avaliações para reavaliação; R20 registra o fechamento"],
    ["2026-08-24","br","Relator adia votação do PL 2338","Votação prevista para depois das eleições.","Leituras do modelo brasileiro passam a ter validade condicionada"],
    ["2026-12-02","fut","UE: fim do prazo de marca d'água para sistemas existentes","Previsto.",""],
    ["2027-12-02","fut","UE: obrigações de alto risco (Anexo III)","Previsto.",""],
    ["2028-08-02","fut","UE: alto risco em produtos (Anexo I)","Previsto.",""],
    ["2028-12-31","fut","Fim do horizonte do PBIA","Previsto.","Avaliação final de execução por eixo"]
  ]
};
