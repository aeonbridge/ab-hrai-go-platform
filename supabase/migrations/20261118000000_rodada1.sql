-- HRAI-GO · posição da rodada 1 (posição cega) para a métrica de revisão de posição (ESP-ONT-02, RF-10)
-- A primeira posição que a pessoa registra no eixo da tensão T5, antes de ver o conselho, é gravada também na chave
-- k = 'q2r1' e nunca mais muda; a chave 'q2' guarda a posição atual (rodada 3). A diferença entre as duas é a revisão
-- de posição. v é um número entre -1 e 1. A RLS existente (escrita só com pid = auth.uid()) continua valendo.
alter table public.respostas drop constraint if exists respostas_k_check;
alter table public.respostas add constraint respostas_k_check
  check (k in ('setor', 'q1', 'q2', 'q2r1', 'q3', 'q4', 'nome') or k ~ '^r:[A-Za-z0-9-]{1,64}$');

alter table public.respostas drop constraint if exists respostas_q2r1_check;
alter table public.respostas add constraint respostas_q2r1_check
  check (k <> 'q2r1' or (jsonb_typeof(v) = 'number' and (v #>> '{}')::numeric between -1 and 1));
