# 6. Acessibilidade

O piso é a **WCAG 2.2 nível AA**. Uma plataforma de governança pública que exclui
leitores de tela ou pessoas com baixa visão contradiz o próprio propósito.

## 6.1 Contraste (medido)

- O `scripts/contrast_check.py` mede todo par semântico nos dois temas e grava o resultado
  em `docs/contrast-report.md`. Medição atual: **0 falhas**.
- O par de texto mais baixo é 5,59:1 (link no tema escuro sobre `bg.subtle`). O texto de
  estado tem no mínimo 7,01:1. Os contornos ficam todos em 4,1:1 ou mais.
- O script retorna erro (`exit 1`) se algum par cair abaixo do piso. Ele deve rodar no CI de
  quem consumir os tokens.
- Regra para pares novos: todo token novo de cor entra na função `pairs()` do script antes
  do merge.
- Contraste é medido contra o **fundo real**. Um badge `soft` sobre `bg.subtle` é um par
  próprio, e já está medido.

## 6.2 Cor nunca sozinha

- Todo estado de domínio tem rótulo, ícone distinto e traço (`03-semantica-de-dominio.md`).
- Faça o teste do cinza: aplique `filter: grayscale(1)` na tela e confirme que todos os
  estados continuam distinguíveis.
- Teste também com simulação de deuteranopia e protanopia, principalmente o par `satisfied` ×
  `notSatisfied` (check × x).
- Gráficos usam marcador e rótulo direto por série, mais um padrão de traço. Uma legenda só
  com cor é defeito.

## 6.3 Teclado e foco

- Todo controle é acessível por Tab em ordem lógica. O anel de foco usa `border.focus`
  (3px com afastamento de 2px, 3:1 ou mais contra o fundo) e nunca é removido.
- Atalhos: `⌘K`/`Ctrl K` para a busca global, `[` / `]` para a rodada anterior e a próxima
  no council, e `Esc` para fechar painel ou sheet. Todos estão documentados em "Atalhos"
  (`?`).
- Grafos (`ArgumentGraph`, grafo de conhecimento) têm equivalente em lista ou árvore,
  navegável com setas, com `role="tree"`.
- Tabelas: `ObligationMatrix` e `ComparisonTable` usam `<table>` com `scope`. A navegação por
  célula com setas é um aprimoramento, não um substituto.

## 6.4 Leitor de tela

- O nome acessível de um badge inclui o grupo e o valor: "Estado da obrigação: evidência
  insuficiente". Não é só "evidência insuficiente".
- O `SyntheticBanner` é lido antes do conteúdo do contêiner (vem primeiro no DOM).
- O `AsOfBar` é uma região (`role="region"`, rótulo "Data de referência"). Ao mudar a data,
  um `aria-live="polite"` anuncia "Avaliação recalculada para 01/06/2026".
- Mudanças de estado assíncronas (fim de avaliação ou de rodada) usam `aria-live="polite"`.
  Erro de fonte usa `assertive`.
- O texto normativo mantém a estrutura com títulos e listas, para que se possa navegar por
  artigo.

## 6.5 Mobile

- Alvo de toque de 48 por padrão e 44 no mínimo. Entre alvos adjacentes, 8px ou mais.
- Fonte de campo de entrada em 16px ou mais.
- Respeitar o tamanho de texto do sistema até 200%. Badges quebram linha e as tabelas
  viram cartões.
- Gestos de deslizar têm botão equivalente visível.
- VoiceOver e TalkBack: os cartões de obrigação são lidos como "LGPD, artigo 20. Estado:
  evidência insuficiente. Vinculante na data. 0 evidências.".

## 6.6 Movimento e tempo

- `prefers-reduced-motion` desliga as transições espaciais.
- Nenhuma sessão expira sem aviso e sem opção de estender. Revisões longas salvam rascunho
  automaticamente.

## 6.7 Linguagem

- A interface usa linguagem simples. O termo jurídico ou técnico aparece com uma
  explicação curta no primeiro uso ou num glossário em tooltip, partindo do glossário
  bilíngue da spec (Apêndice A).
- Siglas são expandidas no primeiro uso da página (`<abbr title>`).
