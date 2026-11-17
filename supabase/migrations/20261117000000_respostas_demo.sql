-- HRAI·GO · respostas da demo ao vivo
-- Cada participante entra com sessão anônima do Supabase Auth (Authentication > Sign In / Providers >
-- "Allow anonymous sign-ins" precisa estar ativado). Ninguém informa nome ou e-mail.
-- Leitura pública das respostas da sala (é o que o telão mostra); escrita só da própria linha (RLS).

create table if not exists public.respostas (
  sala      text        not null check (sala ~ '^[a-z0-9-]{4,40}$'),
  pid       uuid        not null default auth.uid(),
  k         text        not null check (k in ('setor','q1','q2','q3','q4')),
  v         jsonb       not null check (octet_length(v::text) <= 1200),
  setor     text        check (setor is null or setor in ('gov','reg','leg','est','aca','soc','pri','out')),
  ts        bigint      not null,
  criado_em timestamptz not null default now(),
  primary key (sala, pid, k)
);

alter table public.respostas enable row level security;

drop policy if exists "leitura das respostas" on public.respostas;
create policy "leitura das respostas" on public.respostas
  for select to anon, authenticated using (true);

drop policy if exists "participante insere a propria" on public.respostas;
create policy "participante insere a propria" on public.respostas
  for insert to authenticated with check (pid = (select auth.uid()));

drop policy if exists "participante altera a propria" on public.respostas;
create policy "participante altera a propria" on public.respostas
  for update to authenticated using (pid = (select auth.uid())) with check (pid = (select auth.uid()));

-- tempo real para o telão
do $$ begin
  alter publication supabase_realtime add table public.respostas;
exception when duplicate_object then null; end $$;

-- Limpeza após a sessão (LGPD: não guardar além do necessário):
-- delete from public.respostas where sala = 'sala-xxxxxx';
