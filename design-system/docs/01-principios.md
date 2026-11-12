# 1. Princípios

O HRAI-GO é usado por quem regula, por quem é regulado e por quem é afetado. Uma tela
desta plataforma pode acabar citada num parecer, numa auditoria ou num debate público.
Por isso o design system tem uma função antes da estética: **impedir que um tipo de
conhecimento se passe por outro**.

Fonte: *HRAI-GO — Plataforma Aberta de Inteligência Regulatória e Governança de IA*,
documento pedagógico de 11/11/2026 (aqui chamado de "spec").

## 1.1 Separação epistemológica visível

A spec (§1) define seis objetos que não podem ser convertidos silenciosamente uns nos
outros: **texto jurídico oficial, interpretação jurídica, evidência empírica, hipótese de
agente, posição de stakeholder e proposta normativa**. Na interface isso vira regra:

- Toda afirmação exibida carrega um, e só um, `epistemicKind` (`EpistemicTag`), com ícone,
  rótulo e estilo de borda próprios.
- **Proposta nunca parece obrigação.** Tudo o que é propositivo usa borda tracejada e o tom
  `iris`. O tom `iris` nunca aparece em algo vinculante.
- Conteúdo sintético (perspectiva gerada por agente) e fictício (exemplo, simulação) leva
  marca própria, que não pode ser removida da renderização.

## 1.2 Evidência antes de inferência

Princípio de projeto da spec (§18): *evidence before inference; inference before
recommendation; recommendation before human decision*. A ordem de leitura de qualquer tela
segue essa sequência:

1. **Evidência**: a fonte, o trecho, a data.
2. **Inferência**: o que se concluiu, por quem e com que confiança.
3. **Recomendação**: o que se propõe, sempre condicional.
4. **Decisão humana**: quem revisou ou quem decide. Essa camada nunca é preenchida por
   agente.

Na prática, um resultado não aparece sem o caminho até sua origem: o `ProvenanceChip`
precisa estar a um toque ou clique de distância. Um ranking ou uma nota não aparece antes
dos dados que o geraram.

## 1.3 O tempo jurídico é sempre explícito

Leis mudam, e "conforme" só faz sentido numa data. Toda tela que mostra norma ou avaliação
mostra também o `LegalSnapshot` e os dois eixos de tempo (`validTime` e `recordTime`, spec
§6.2), pelo componente `AsOfBar`. Nenhuma avaliação aparece sem data.

## 1.4 Pluralidade sem falsa representatividade

- Nenhum estrato de stakeholder recebe cor própria: todos usam cromo neutro, com ícone e
  rótulo. Cor implicaria hierarquia de confiança.
- Contagem de assentos ou de agentes nunca aparece como "vontade social". O Shadow Council
  mostra **cobertura** e **grau de suporte argumentativo**, nunca placar de votação (spec
  §10.7).
- Lacuna de fonte aparece como **"Não representado"**, num assento vazio e tracejado. Nunca
  se preenche a lacuna com uma posição plausível.
- O dissenso tem lugar fixo na composição (o `MinorityReport`) e não pode ser colapsado numa
  média.

## 1.5 Sem nota única de "melhor política"

O FORESIGHT compara alternativas por indicadores separados e por fronteira de Pareto. A
interface não oferece índice composto de qualidade regulatória. Direitos fundamentais não
aparecem como custo compensável num mesmo eixo (spec §10.7).

## 1.6 Sóbrio, legível, institucional

- Claro por padrão, com tema escuro opcional e paridade completa entre os dois.
- Tipografia que aguenta texto jurídico longo: serif para a norma, sans para a interface,
  mono para identificadores.
- Nenhum efeito decorativo que concorra com o conteúdo: sem gradiente, sem brilho, sem
  glassmorphism. O peso visual fica com o estado jurídico, não com a marca.
- **Sem emoji e sem ícone de "brilhos" (sparkles) para representar IA.** Agente aparece como
  agente, com o ícone `bot` ou `cpu`, rótulo e identidade. IA não é mágica, e a interface
  não deve sugerir que seja.

## 1.7 Voz e redação

| Faça | Não faça |
|---|---|
| "Evidência insuficiente para concluir" | "Não conforme" quando falta prova (spec §13.1) |
| "PL 2338/2023 · em tramitação · não vinculante" | "Nova lei de IA exige…" |
| "Hipótese do `RegulatoryTensionAgent`, não revisada" | "A plataforma identificou que a lei é falha" |
| "Perspectiva sintética baseada em 4 fontes" | "O setor produtivo acha que…" |
| "Inconclusivo por falta de dados" | Esconder a alternativa sem resultado |
| "Em vigor · aplicação a partir de 02/08/2027" | "Vigente" quando a obrigação ainda não se aplica |

Regras:

- **Verbo de modalidade correto.** "Exige" só para obrigação aplicável. "Propõe" para
  proposta. "Sustenta" para posição. "Sugere" para hipótese.
- **Sempre atribuir.** Toda inferência diz quem a fez: humano, agente da plataforma ou
  perspectiva sintética.
- **Nomes canônicos em inglês, rótulos em português.** O identificador (`InsufficientEvidence`)
  aparece em mono no detalhe técnico. O rótulo da interface vem de `label.pt-BR` nos tokens.
- **Incerteza dita em palavras**, nunca só por opacidade, cor ou tamanho.
