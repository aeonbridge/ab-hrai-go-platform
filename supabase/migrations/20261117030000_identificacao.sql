-- HRAI-GO · identificação opcional do participante
-- A participação continua anônima por padrão: o apelido ("Academia·7f3") e o avatar em pixel são derivados
-- do identificador anônimo da sessão (auth.uid()) e nunca mudam. Quem quiser pode mostrar o próprio nome a
-- qualquer momento gravando a chave k = 'nome'; v é o nome (texto de 1 a 60 caracteres) ou null para voltar a
-- ficar anônimo. O nome aparece ao lado do apelido, nunca no lugar dele. A RLS existente (escrita só com
-- pid = auth.uid()) garante que ninguém identifica outra pessoa.
alter table public.respostas drop constraint if exists respostas_k_check;
alter table public.respostas add constraint respostas_k_check
  check (k in ('setor', 'q1', 'q2', 'q3', 'q4', 'nome') or k ~ '^r:[A-Za-z0-9-]{1,64}$');

alter table public.respostas drop constraint if exists respostas_nome_check;
alter table public.respostas add constraint respostas_nome_check
  check (k <> 'nome' or jsonb_typeof(v) = 'null'
         or (jsonb_typeof(v) = 'string' and char_length(btrim(v #>> '{}')) between 1 and 60));

comment on column public.respostas.k is
  'Chave da resposta: setor, q1..q4, nome (identificação opcional; null = anônimo) ou r:<pid> (reação a uma contribuição).';
