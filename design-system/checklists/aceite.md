# Checklist de aceite: tela ou componente HRAI-GO

Use antes de considerar pronta qualquer tela, componente ou artefato. Cada item vem de uma
regra de `docs/`.

## Separação epistemológica
- [ ] Toda afirmação exibida tem um `EpistemicTag`, e só um.
- [ ] Nenhum conteúdo propositivo (proposta, hipótese, PL em tramitação) usa traço sólido nem
      os tons verdant, crimson ou civic sólido.
- [ ] Os requisitos não vinculantes estão fora dos totais e no grupo separado
      "Referências a propostas".
- [ ] Toda inferência indica o autor: humano, agente da plataforma ou perspectiva sintética.
- [ ] O conteúdo sintético ou fictício mostra o `SyntheticBanner` ou a marca correspondente,
      sem opção de esconder.

## Tempo e proveniência
- [ ] A tela que mostra norma ou avaliação exibe o `AsOfBar` com o `LegalSnapshot`.
- [ ] "Em vigor" e "Aplicável" aparecem como estados diferentes, quando diferirem.
- [ ] Toda conclusão leva à origem em até um clique ou toque (`ProvenanceChip`).
- [ ] Mudanças aparecem como "de → para".

## Pluralidade
- [ ] Nenhum estrato de stakeholder tem cor própria.
- [ ] Os assentos ou estratos sem fonte aparecem como "Não representado".
- [ ] O `MinorityReport` tem o mesmo peso tipográfico da síntese e não fica recolhido.
- [ ] Não há placar de votos, contagem de curtidas nem nota composta de "melhor política".
- [ ] A perspectiva sintética não usa foto, avatar humano nem a assinatura de posição oficial.

## Tokens
- [ ] Não há cor, sombra ou espaçamento escrito à mão. Tudo vem de token semântico ou de
      domínio.
- [ ] O token novo foi criado nos dois temas (`semantic.light` e `semantic.dark`).
- [ ] `python3 scripts/contrast_check.py` → 0 falhas.
- [ ] `python3 scripts/validate_domain.py` → 0 erros.

## Acessibilidade (WCAG 2.2 AA)
- [ ] Teste do cinza: com `grayscale(1)`, todos os estados continuam distinguíveis.
- [ ] Simulação de deuteranopia: `satisfied` × `notSatisfied` distinguíveis pelo ícone.
- [ ] Navegação completa por teclado, com foco visível em todos os elementos.
- [ ] Grafos têm equivalente em lista ou árvore.
- [ ] O nome acessível dos badges inclui o grupo ("Estado da obrigação: …").
- [ ] Texto do sistema a 200% no mobile, sem truncar rótulo de estado.
- [ ] Alvo de toque de 48 ou mais (44 é o piso). Campo de entrada com fonte de 16 ou mais no
      mobile.
- [ ] Todo gesto tem botão equivalente.
- [ ] `prefers-reduced-motion` é respeitado.

## Web × mobile
- [ ] O layout foi conferido em 390×844 e em 1440×900.
- [ ] As tabelas densas viram cartões em `compact`.
- [ ] Os detalhes abrem em sheet no mobile e em painel lateral na web.

## Iconografia e redação
- [ ] Sem emoji. Sem `sparkles`, `wand` ou `stars` para IA.
- [ ] Os verbos de modalidade estão corretos: "exige" só para obrigação aplicável.
- [ ] Incerteza dita em palavras, e não só por cor ou opacidade.
