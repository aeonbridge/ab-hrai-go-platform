-- HRAI-GO · reações entre participantes (modo participante da câmara ao vivo)
-- Uma reação é uma linha comum de respostas com k = 'r:<pid do autor>' e v = 'apoio' | 'contesto' | 'fonte' | 'nenhuma'.
-- A chave primária (sala, pid, k) garante uma reação por pessoa por contribuição; a RLS existente
-- (escrita só com pid = auth.uid()) continua valendo, então ninguém reage em nome de outro.
alter table public.respostas drop constraint if exists respostas_k_check;
alter table public.respostas add constraint respostas_k_check
  check (k in ('setor', 'q1', 'q2', 'q3', 'q4') or k ~ '^r:[A-Za-z0-9-]{1,64}$');
