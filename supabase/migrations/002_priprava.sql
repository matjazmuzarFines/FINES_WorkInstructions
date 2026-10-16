-- =====================================================================
-- FINES - Work Instructions | 002: priprava delovnega mesta
-- Seznam (alineje) dodatne opreme / materiala, ki ga delavec pripravi pred delom
-- (npr. "Tesnilni trak 20 mm", "Cev prozorna fi 20 - 300 mm").
-- tip: 'oprema' zdaj, kasneje 'orodje' (ista tabela, ločen prikaz).
-- Zaženi PO 001_schema.sql. Idempotentno.
-- =====================================================================

create table if not exists wi_priprava (
  id          bigint generated always as identity primary key,
  program_id  bigint not null references wi_programi(id),
  tip         text not null default 'oprema',
  naziv       text not null,
  vrstni_red  integer not null default 0,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists wi_priprava_program_idx on wi_priprava(program_id);

drop trigger if exists wi_priprava_updated_at on wi_priprava;
create trigger wi_priprava_updated_at before update on wi_priprava
  for each row execute function wi_set_updated_at();

-- RLS: branje vsi prijavljeni, pisanje samo admini, brez brisanja (visible = false)
alter table wi_priprava enable row level security;
drop policy if exists wi_priprava_select on wi_priprava;
drop policy if exists wi_priprava_insert on wi_priprava;
drop policy if exists wi_priprava_update on wi_priprava;
create policy wi_priprava_select on wi_priprava for select to authenticated using (true);
create policy wi_priprava_insert on wi_priprava for insert to authenticated with check (wi_je_admin());
create policy wi_priprava_update on wi_priprava for update to authenticated using (wi_je_admin()) with check (wi_je_admin());
