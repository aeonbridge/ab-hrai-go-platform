# Padrão de formatação dos relatórios técnicos HRAI-GO

**Decisão registrada em 17/11/2026.** Todo relatório técnico, especificação ou documento conceitual em
LaTeX do HRAI-GO (Human-centred Regulatory AI, Governance Observatory) segue a **ABNT NBR 10719:2015**
(*Informação e documentação: relatório técnico e/ou científico: apresentação*). A implementação usa a
classe [abnTeX2](https://www.abntex.net.br/) e o pacote da casa `docs/latex/hraigo-abnt.sty`.

| Peça | Arquivo |
|---|---|
| Pacote de estilo (layout, fontes, folha de rosto, formulário, macros) | `docs/latex/hraigo-abnt.sty` |
| Modelo pronto para copiar | `docs/latex/modelo-relatorio-tecnico.tex` |
| Bibliografia compartilhada (NBR 6023) | `docs/latex/referencias.bib` |
| Compilação | `scripts/build-relatorios.sh [arquivo.tex]` |
| Verificação automática | `tests/test_padrao_relatorios.py` |

Referência de aplicação usada para conferir a formatação: o manual de relatórios técnicos do Instituto
Superior de Educação Ivoti (versão 2023), que segue a NBR 10719:2015.

## 1. Normas aplicadas

| Norma | Assunto | Como é atendida |
|---|---|---|
| NBR 10719:2015 | Estrutura e apresentação do relatório | classe `abntex2` + `hraigo-abnt.sty` |
| NBR 6023 | Referências | `abntex2cite` (opção `alf`) + `referencias.bib` |
| NBR 10520 | Citações | sistema autor-data: `\cite{chave}` e `\citeonline{chave}` |
| NBR 6024 | Numeração progressiva das seções | `\chapter`, `\section`, `\subsection`, `\subsubsection`, `\subsubsubsection` |
| NBR 6027 | Sumário | `\tableofcontents*` |
| NBR 6028 | Resumo e palavras-chave | ambiente `resumorelatorio` + `\palavraschave{}` |
| IBGE (1993) | Tabelas | legenda acima, fonte abaixo, sem linhas verticais (`booktabs`) |

Limitação conhecida: o `abntex2cite` imprime o sobrenome nas citações em MAIÚSCULAS, como na
NBR 10520:2002. A revisão de 2023 também admite só a inicial maiúscula. Mantemos o comportamento da
classe até o abnTeX2 oferecer a opção.

## 2. Estrutura obrigatória (NBR 10719, seção 4)

| Parte | Elemento | Situação | Comando |
|---|---|---|---|
| Externa | Capa | opcional (não usada) | — |
| Pré-textual | Folha de rosto | **obrigatório** | `\imprimirfolhaderostorelatorio` |
| | Verso: equipe técnica | opcional | `\equipe{...}` |
| | Errata | opcional | `\begin{errata}` |
| | Agradecimentos (bases do patrocínio) | opcional, usado por padrão | automático via `\imprimirfolhaderostorelatorio` |
| | Resumo na língua vernácula + palavras-chave | **obrigatório** | `\begin{resumorelatorio}` |
| | Listas de ilustrações, tabelas, siglas, símbolos | opcional (recomendado acima de 5 itens) | `\listoffigures*`, `\listoftables*`, `siglas`, `simbolos` |
| | Sumário | **obrigatório** | `\tableofcontents*` |
| Textual | Introdução, desenvolvimento, considerações finais | **obrigatório** | após `\textual` |
| Pós-textual | Referências | **obrigatório** | `\postextual` + `\bibliography{referencias}` |
| | Glossário | opcional | `\glossary` / capítulo próprio |
| | Apêndices (elaborados pelos autores) | opcional | `apendicesenv` |
| | Anexos (de terceiros) | opcional | `anexosenv` |
| | Índice | opcional | `\printindex` |
| | Formulário de identificação | opcional (último elemento) | `\imprimirformularioidentificacao[resumo]` |

Autoria: o autor é o doutorando Jefferson Wellington da Cunha (jc@aeonbridge.com | jefferson.cunha@ufpe.br) e a
[AeonBridge Co.](https://aeonbridge.com/) é a patrocinadora do projeto. As bases do patrocínio (recursos humanos
qualificados, financeiros e infraestrutura, incluindo os modelos de linguagem do Shadow Council) aparecem no
elemento pré-textual **Agradecimentos** (NBR 10719, opcional), impresso automaticamente depois da folha de rosto. O pacote já traz esses valores (`\autor`, `\qualificacao`, `\contato`,
`\patrocinador`), e os relatórios não devem sobrescrevê-los.

A folha de rosto segue a ordem da NBR 10719, 4.2.1.1.1: órgão responsável; projeto; título e
subtítulo (separados por dois-pontos); volume; código; classificação de segurança; autor; local; ano.

## 3. Regras de apresentação (NBR 10719, seção 5)

- **Papel:** A4, impressão em anverso (`oneside`).
- **Margens:** superior e esquerda 3 cm; inferior e direita 2 cm.
- **Fonte:** uma só família em todo o documento, inclusive nos títulos: TeX Gyre Termes (equivalente a
  Times), tamanho 12 no texto, nos títulos e nas legendas. Citações com mais de três linhas, notas de rodapé,
  paginação, notas e fontes de tabelas e ilustrações usam tamanho 10.
- **Cor:** texto sempre em preto. Cores só em ilustrações (figuras e diagramas). Caixas de destaque têm
  moldura cinza ou preta e texto preto; status em tabelas usam negrito, não cor.
- **Títulos das seções** (corpo 12, alinhados à esquerda, um espaço entre o indicativo e o título):

  | Nível | Comando | Exemplo |
  |---|---|---|
  | Primária | `\chapter` | **1 SEÇÃO PRIMÁRIA** (negrito, maiúsculas, página nova) |
  | Secundária | `\section` | 1.1 SEÇÃO SECUNDÁRIA (maiúsculas) |
  | Terciária | `\subsection` | **1.1.1 Seção terciária** (negrito) |
  | Quaternária | `\subsubsection` | 1.1.1.1 Seção quaternária |
  | Quinária | `\subsubsubsection` | *1.1.1.1.1 Seção quinária* (itálico) |

  Títulos sem indicativo numérico (listas, resumo, sumário, referências, apêndices, anexos) são centralizados,
  em negrito e maiúsculas. O sumário repete a tipografia de cada nível.
- **Folha de rosto:** tudo em corpo 12, centralizado e com espaçamento 1,5. Só o título vai em negrito; o
  subtítulo fica em fonte normal.
- **Espaçamento:** 1,5 entre linhas no texto; simples em tabelas, quadros e notas destacadas.
- **Parágrafo:** recuo de 1,25 cm, inclusive no primeiro parágrafo de cada seção.
- **Paginação:** todas as folhas são contadas a partir da folha de rosto. O número aparece a partir da
  primeira folha textual (Introdução), em algarismos arábicos, tamanho 10, no canto superior direito, sem
  título corrente nem filete.
- **Seções:** numeração progressiva em algarismos arábicos (NBR 6024), até o 5.º nível (`\chapter` a
  `\subsubsubsection`), sem pular níveis. Seções primárias (`\chapter`) começam em página nova. Não use
  `\paragraph` como título solto, porque na abnTeX2 ele é o 5.º nível numerado.
- **Código:** `\begin{lstlisting}[style=hraigo]`.
- **Ilustrações e tabelas:** `\caption{...}` **acima**, `\fonte{...}` **abaixo**, sempre citadas no
  texto antes de aparecerem. Notas explicativas abaixo da fonte com `\nota{...}` (comando da abnTeX2).
- **Siglas:** na primeira menção, escreva por extenso e coloque a sigla entre parênteses.
- **Nome da plataforma:** na primeira menção, *HRAI-GO (Human-centred Regulatory AI, Governance
  Observatory)*; ver `docs/NOMENCLATURA.md`.

## 4. Identificação e séries

| Série | Uso | `\tipotrabalho` |
|---|---|---|
| `RT-<TEMA>-<nn>` | Relatório técnico (resultados, método, avaliação) | Relatório técnico |
| `ESP-<TEMA>-<nn>` | Especificação técnica (requisitos, contratos) | Especificação técnica |
| `DC-<TEMA>-<nn>` | Documento conceitual ou pedagógico | Documento conceitual |

Os temas atuais são `ONT` (ontologia), `VIS` (visão), `PLAT` (plataforma) e `SCSE` (Shadow Council).
O número sequencial não é reaproveitado.

| Documento | Código |
|---|---|
| `docs/relatorios/ontologia/relatorio.tex` | RT-ONT-01 |
| `docs/especificacoes/ESP-ONT-02/especificacao.tex` | ESP-ONT-02 |
| `docs/relatorios/visao/hrai-go-visao.tex` | RT-VIS-03 |
| `docs/hrai-go/HRAI-GO_Plataforma_Inteligencia_Regulatoria_Shadow_Council.tex` | DC-PLAT-01 |
| `docs/scse/SCSE_Shadow_Council_Simulation_Spec.tex` | ESP-SCSE-01 |

## 5. Referências

- Use `docs/latex/referencias.bib`. Não renomeie uma chave que já esteja em uso.
- Toda entrada deve poder ser conferida num arquivo de `docs/ai-regulations/` ou `docs/references/`, ou
  numa URL com data de acesso (`urlaccessdate`). Não invente metadados.
- Escreva autor-entidade em MAIÚSCULAS e entre chaves duplas: `author = {{BRASIL. SENADO FEDERAL}}`.
- Título sem autor que começa com letra acentuada: proteja a primeira palavra em maiúsculas
  (`title = {{ANÁLISE} comparativa ...}`), porque o BibTeX não põe acentos em maiúscula.
- Fontes usadas por um único relatório podem ficar num `.bib` local, ao lado do `.tex`:
  `\bibliography{referencias,refs-local}`.

## 6. Elementos visuais da casa

`hraigo-abnt.sty` define a paleta (`latao`, `tinta`, `lagoa`, `coral`, `cinza`, `violeta`), as caixas
`\destaque{...}` (nota de leitura) e `\alerta{...}` (advertência) e a coluna `L` para `tabularx`. Não
use `\nota` para caixas, porque na abnTeX2 esse comando é a linha "Nota:" abaixo de tabelas e figuras.
As cores precisam continuar legíveis em impressão em tons de cinza.

## 7. Compilação

```bash
scripts/build-relatorios.sh                                  # todos os documentos registrados
scripts/build-relatorios.sh docs/relatorios/visao/hrai-go-visao.tex
```

Motor: XeLaTeX + BibTeX via `latexmk`. Dependências: TeX Live com `abntex2`, `tex-gyre`, `latexmk`
(no Debian/Ubuntu: `texlive-xetex texlive-publishers texlive-fonts-recommended texlive-lang-portuguese
texlive-latex-extra latexmk`).

## 8. Novo relatório: passo a passo

1. Copie `docs/latex/modelo-relatorio-tecnico.tex` para `docs/relatorios/<tema>/relatorio.tex`.
2. Preencha `\titulo`, `\subtitulo`, `\codigo`, `\versao`, `\data` e `\palavraschave`.
3. Escreva o resumo (150 a 500 palavras): objetivo, método, resultados e conclusões.
4. Registre o arquivo em `scripts/build-relatorios.sh` e em `tests/test_padrao_relatorios.py`.
5. Rode `scripts/build-relatorios.sh <arquivo>` e `pytest tests/test_padrao_relatorios.py`.
