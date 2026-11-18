# Consultas de competência (ESP-ONT-02, RF-08)

Cada arquivo `.rq` responde a uma pergunta de competência do RT-VIS-03 (Tabela 4), agrupada pela pergunta norteadora:

| Consulta | Pergunta | Serve a |
|---|---|---|
| `PC9_especificidades.rq` | Especificidades do Brasil frente às demais jurisdições, com evidência (passo M5) | QN1, lida antes das demais |
| `PC1_cobertura_por_area.rq` | Áreas que cada modelo cobre, com força jurídica (R24a/b/c) | QN1 |
| `PC5_codificacoes.rq` | Classificação nos critérios da taxonomia, com dispositivo e revisão | QN1 |
| `PC2_correspondencias.rq` | Correspondências BR × AI Act e a especificidade de cada divergência | QN2 |
| `PC3_incorporado_sem_capacidade.rq` | Requisitos que pressupõem capacidade abaixo do limiar ou sem indicador | QN2 |
| `PC6_afirmacoes.rq` | Afirmações, evidências, contestações, qualificações e complementos | QN2/QN3 |
| `PC4_exposicao_sem_cobertura.rq` | Exposição sem cobertura, só dentro de um `CoverageAssessment` | QN3 |
| `PC7_reaberto_por_mudanca.rq` | O que uma mudança de texto reabre (R10 a R13) | transversal |
| `PC8_posicoes.rq` | Posições humanas e sintéticas, sem misturar as origens | transversal |
| `V16_sementes_sem_ligacao.rq` | Aceite V-16: tensões-semente sem afirmação (deve dar zero) | aceite |

Execução sobre o grafo completo, depois do raciocínio:

```
python3 scripts/ontologia/consultas.py           # grava docs/especificacoes/ESP-ONT-02/consultas-resultado.json
python3 scripts/ontologia/consultas.py --check   # regressão: falha se uma consulta quebrar ou perder linhas
python3 -m pytest -q tests/test_consultas.py     # inclui teste de cada PC sobre dados de fixture
```

Uma consulta com zero linhas responde "nada registrado ainda", não "não existe": PC1, PC2, PC3, PC4, PC5 e PC9 dependem
das extrações e codificações dos itens 11, 12 e 16 do `EXECUCAO_LOOP.md`.
