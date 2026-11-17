# HRAI-GO Platform — instruções do projeto

## Nome da plataforma (obrigatório)

- Nome oficial: **HRAI-GO: Human-centred Regulatory AI, Governance Observatory**.
- Subtítulo: *Plataforma de inteligência regulatória humano–IA*.
- Fonte canônica: `docs/NOMENCLATURA.md`. Leia antes de escrever README, documentos, páginas web,
  títulos, metadados ou textos para o público.
- Na primeira menção de cada documento novo, escreva o nome completo; depois, só `HRAI-GO`.
- Nunca expanda HRAI como *High-Risk AI*. Esse é o significado legado e sobrevive só em
  namespaces de ontologia (`hrai:`, `hrai-*.owl`) e no título citado do Guia HRAI.
- `tests/test_nomenclatura.py` protege essas regras; mantenha-o passando.

## Relatórios técnicos (obrigatório)

- Todo documento LaTeX (relatório, especificação, documento conceitual) segue a ABNT NBR 10719:2015
  pelo padrão da casa: `docs/PADRAO_RELATORIOS.md`.
- Comece pelo modelo `docs/latex/modelo-relatorio-tecnico.tex`, com a classe `abntex2` e o pacote
  `docs/latex/hraigo-abnt.sty`. Não use `article`, `geometry`, `fancyhdr`, `\maketitle` nem
  `thebibliography`.
- Use as referências de `docs/latex/referencias.bib` (NBR 6023, autor-entidade em MAIÚSCULAS) e
  nunca invente metadados.
- Registre cada novo documento em `scripts/build-relatorios.sh` e em `tests/test_padrao_relatorios.py`,
  e compile com `scripts/build-relatorios.sh <arquivo.tex>`.

## Objetivo do trabalho (leia antes de desenvolver)

- O bootstrap termina quando a própria plataforma responde, ainda que de forma inicial, às três perguntas
  norteadoras (RT-VIS-03 cap. 2; ESP-ONT-02 Introdução; `docs/especificacoes/ESP-ONT-02/EXECUCAO_LOOP.md`):
  - **QN1 (âncora):** quais as especificidades do Brasil em relação às demais jurisdições analisadas que devem
    nortear um modelo de governança de IA com foco estratégico para o Brasil como nação, e não apenas uma proposta
    regulatória baseada em princípios e valores afins?
  - **QN2:** o que está sendo considerado e não deveria?
  - **QN3:** o que não está sendo considerado e deveria?
- QN2 e QN3 são subordinadas à QN1: todo item cita a especificidade brasileira em que se apoia. Não use o AI Act
  como régua implícita.
- Todo requisito ou tarefa deve servir a uma das perguntas; se não servir, pergunte antes.

## Autoria (obrigatório)

- Autor do trabalho: **Jefferson Wellington da Cunha**, doutorando (jc@aeonbridge.com | jefferson.cunha@ufpe.br).
- **[AeonBridge Co.](https://aeonbridge.com/)** é patrocinadora do projeto, não autora. Toda menção a ela leva o link
  https://aeonbridge.com/. As bases do patrocínio (recursos humanos, financeiros, infraestrutura e modelos do
  Shadow Council) saem nos Agradecimentos de cada relatório (`\imprimirpatrocinio` em `hraigo-abnt.sty`); se a lista
  de modelos em `config/scse/models.toml` mudar, atualize `\textopatrocinio`. Não atribua autoria a "Equipe HRAI-GO",
  "Plataforma HRAI-GO" nem "Aeonbridge" em relatórios, metadados ou páginas.
- Nos relatórios LaTeX, autoria e patrocínio já vêm de `docs/latex/hraigo-abnt.sty` (`\autor`, `\qualificacao`,
  `\contato`, `\patrocinador`); não os sobrescreva.
