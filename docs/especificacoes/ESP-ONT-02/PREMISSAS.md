# Premissas da sessão do loop (ESP-ONT-02)

O autor autorizou em 17/11/2026 ("pode fazer assumptions e deixar registradas para não parar"): quando um passo depende
de decisão humana, a sessão adota uma **premissa**, registra aqui e segue. Premissa **não é decisão**: decisões do autor
ficam em `decisoes.json` e viram `ApprovalDecision` no grafo; premissas são provisórias, reversíveis e não aprovam
nada (invariante I-3). Cada linha diz o que foi assumido, o efeito e como desfazer.

| Id | Pendência | Premissa adotada | Efeito | Como desfazer |
|---|---|---|---|---|
| P-01 | D-06: PDF da "Análise Comparativa" fora do repositório | As 12 teses continuam como resumidas pelo autor; nenhuma tese é alterada por falta do PDF | Teses e estados (6/4/2) inalterados | Colocar o PDF no corpus e conferir cada tese contra ele |
| P-02 | D-08: parágrafo sobre micro e pequenas empresas e startups (texto de 2023) | Vale a extração do PDF: o parágrafo está no art. 32, parágrafo único. O rótulo da evidência passa a dizer art. 32, com nota do rótulo antigo | Rótulo de `a1:Ev_PL_Art33PU` corrigido; IRI mantido | Restaurar o rótulo antigo no arquivo de afirmações |
| P-03 | D-10: escopos de cobertura (`CoverageAssessment`) | Nenhum escopo é declarado enquanto a cobertura por área não estiver extraída de todos os instrumentos de cada jurisdição (lei vigente, proposta e plano); declarar escopo parcial geraria lacunas falsas (ex.: a LGPD cobre governança de dados, mas não está extraída por dispositivo) | PC4 segue em zero, com o motivo no relatório | Declarar os escopos quando a cobertura por área estiver extraída |
| P-04 | D-13: revisão das 52 codificações | As codificações são usadas como candidatas, sempre marcadas como não revisadas; nada que exija aprovação (R28) é ativado | R28 continua sem disparar; comparador mostra "candidata" | Aprovar (decisão) ou corrigir valores em `codificar.py` |
| P-05 | D-12: textos oficiais chineses que faltam | A China segue comparada com o que há: texto oficial das medidas de IA generativa e fontes secundárias marcadas | Comparações com a China seguem "não codificado" exceto S7 | Acrescentar os textos e rodar a extração |
