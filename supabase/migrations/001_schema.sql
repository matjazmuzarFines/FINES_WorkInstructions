-- =====================================================================
-- FINES - Work Instructions | 001: osnovna shema
-- wi_   = tabele projekta Work Instructions (navodila za proizvodnjo / montažo)
-- ln_wi_ = povezovalne tabele
-- spl_  = splošne tabele (spl_druzine, spl_normativi že obstajata iz FINES_Production)
--
-- Zaženi v Supabase -> SQL Editor (ista baza kot FINES_Production).
-- Pred tem: Authentication -> Users -> Add user: admin@fines.si (Auto Confirm).
-- Idempotentno (lahko se zažene večkrat).
-- =====================================================================

-- Skupna funkcija: posodobi updated_at
create or replace function wi_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- =====================================================================
-- ADMINI - uporabniki, ki smejo urejati navodila (admin dostop v aplikaciji)
-- =====================================================================
create table if not exists wi_admini (
  id          bigint generated always as identity primary key,
  email       text not null unique,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

insert into wi_admini (email) values ('admin@fines.si') on conflict (email) do nothing;

-- Ali je prijavljeni uporabnik admin (uporabljeno v RLS politikah)
create or replace function wi_je_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from wi_admini
    where visible and lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

-- =====================================================================
-- SEKCIJE IN PODSEKCIJE (urejanje: Admin -> Nastavitve)
-- koda se uporabi v internem ID programa: {sekcija}-{podsekcija}-{zaporedna}
-- =====================================================================
create table if not exists wi_sekcije (
  id          bigint generated always as identity primary key,
  koda        text not null unique,          -- npr. MO, PR
  naziv       text not null,
  opis        text,
  vrstni_red  integer not null default 0,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists wi_podsekcije (
  id          bigint generated always as identity primary key,
  sekcija_id  bigint not null references wi_sekcije(id),
  koda        text not null,                 -- npr. VAR, LAS
  naziv       text not null,
  opis        text,
  vrstni_red  integer not null default 0,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint wi_podsekcije_uq unique (sekcija_id, koda)
);

insert into wi_sekcije (koda, naziv, vrstni_red) values
  ('MO', 'Montaža', 1),
  ('PR', 'Proizvodnja', 2)
on conflict (koda) do nothing;

insert into wi_podsekcije (sekcija_id, koda, naziv, vrstni_red)
select s.id, v.koda, v.naziv, v.red
from (values
  ('MO', 'PRE', 'Predpriprava', 1),
  ('MO', 'MON', 'Montaža', 2),
  ('MO', 'ELE', 'Elektromontaža', 3),
  ('MO', 'TES', 'Testiranje', 4),
  ('MO', 'PAK', 'Pakiranje', 5),
  ('PR', 'LAS', 'Laser', 1),
  ('PR', 'KRI', 'Krivljenje', 2),
  ('PR', 'VAR', 'Varjenje', 3),
  ('PR', 'BRU', 'Brušenje', 4)
) as v(sekcija, koda, naziv, red)
join wi_sekcije s on s.koda = v.sekcija
on conflict (sekcija_id, koda) do nothing;

-- =====================================================================
-- PROGRAMI (navodila) in KORAKI
-- =====================================================================
create table if not exists wi_programi (
  id          bigint generated always as identity primary key,
  interni_id  text not null unique,          -- npr. PR-VAR-001
  naziv       text not null,
  opis        text,
  zaporedna   integer not null default 1,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists ln_wi_programi_podsekcije (
  id             bigint generated always as identity primary key,
  program_id     bigint not null references wi_programi(id),
  podsekcija_id  bigint not null references wi_podsekcije(id),
  visible        boolean not null default true,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  constraint ln_wi_programi_podsekcije_uq unique (program_id, podsekcija_id)
);

create table if not exists ln_wi_programi_druzine (
  id          bigint generated always as identity primary key,
  program_id  bigint not null references wi_programi(id),
  druzina_id  bigint not null references spl_druzine(id),
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint ln_wi_programi_druzine_uq unique (program_id, druzina_id)
);

-- Povezave programov na idente (proizvodne šifre)
create table if not exists ln_wi_programi_identi (
  id          bigint generated always as identity primary key,
  program_id  bigint not null references wi_programi(id),
  ident       text not null,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint ln_wi_programi_identi_uq unique (program_id, ident)
);
create index if not exists ln_wi_programi_identi_ident_idx on ln_wi_programi_identi(ident);

create table if not exists wi_koraki (
  id          bigint generated always as identity primary key,
  program_id  bigint not null references wi_programi(id),
  vrstni_red  integer not null default 0,
  naziv       text not null default '',
  opis        text,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists wi_koraki_program_idx on wi_koraki(program_id);

-- Slike koraka (največ 6 na korak - preverja aplikacija). Slike se brišejo (prostor).
create table if not exists wi_slike (
  id          bigint generated always as identity primary key,
  korak_id    bigint not null references wi_koraki(id),
  pot         text not null,                 -- pot v bucketu wi_slike
  opis        text,
  vrstni_red  integer not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists wi_slike_korak_idx on wi_slike(korak_id);

-- =====================================================================
-- ŠIFRE (splošna tabela - izvoz šifranta artiklov, sifre.xls)
-- Uvoz: Admin -> Nastavitve -> Uvoz šifer. V aplikaciji se ne ureja.
-- =====================================================================
create table if not exists spl_identi (
  id                       bigint generated always as identity primary key,
  sifra                    text not null unique,   -- Proizvodna šifra
  klasifikat               text generated always as (split_part(sifra, '-', 1)) stored, -- npr. 096
  vrsta                    text,
  rd                       boolean,
  rdp                      boolean,
  pm                       boolean,
  vk                       boolean,
  naziv                    text,
  urejenost_teh_dok        boolean,
  urejenost_nab_param      boolean,
  vgradnja                 text,
  status                   text,
  kataloska_st             text,
  em                       text,
  klasifikacija            text,
  tip_materiala            text,
  pripadnost               text,
  dobavitelj               text,
  proizvajalec             text,
  material                 text,
  standard                 text,
  faktor_1                 numeric,
  faktor_2                 numeric,
  neaktiven                boolean,
  oznaka_dokumenta         text,
  dodatni_naziv            text,
  poreklo                  text,
  rabatna_skupina          text,
  bruto_teza               numeric,
  neto_teza                numeric,
  tarifna_stevilka         text,
  naziv_ang                text,
  kratica                  text,
  druzina                  text,
  karakteristicno_stevilo  text,
  odpiranje                text,
  upravljanje              text,
  partner                  text,
  model                    text,
  kreiral_uporabnik        text,
  kreiral_cas              timestamp,
  azuriral_uporabnik       text,
  azuriral_cas             timestamp,
  prodajna_cena            numeric,
  nabavna_cena             numeric,
  cena_kooperacija         numeric,
  povprecna_cena           numeric,
  cena_zadnjega_prevzema   numeric,
  datum_zad_prevzema       date,
  faktor_vrednosti         numeric,
  planirana_lastna_cena    numeric,
  planirana_prodajna_cena  numeric,
  prodajna_cena_indeks     numeric,
  visible                  boolean not null default true,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);
create index if not exists spl_identi_klasifikat_idx on spl_identi(klasifikat);

-- Zgodovina uvozov (šifre ...)
create table if not exists wi_uvozi (
  id          bigint generated always as identity primary key,
  tip         text not null,                 -- 'identi'
  datoteka    text not null,
  stevilo     integer not null default 0,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- =====================================================================
-- updated_at triggerji
-- =====================================================================
do $$
declare t text;
begin
  foreach t in array array[
    'wi_admini', 'wi_sekcije', 'wi_podsekcije', 'wi_programi', 'ln_wi_programi_podsekcije',
    'ln_wi_programi_druzine', 'ln_wi_programi_identi', 'wi_koraki', 'wi_slike', 'spl_identi', 'wi_uvozi'
  ] loop
    execute format('drop trigger if exists %I on %I', t || '_updated_at', t);
    execute format(
      'create trigger %I before update on %I for each row execute function wi_set_updated_at()',
      t || '_updated_at', t);
  end loop;
end;
$$;

-- =====================================================================
-- RLS - branje: vsi prijavljeni (authenticated); pisanje: samo admini.
-- DELETE politike ni (podatke skrijemo z visible = false), razen slik.
-- =====================================================================
do $$
declare t text;
begin
  foreach t in array array[
    'wi_admini', 'wi_sekcije', 'wi_podsekcije', 'wi_programi', 'ln_wi_programi_podsekcije',
    'ln_wi_programi_druzine', 'ln_wi_programi_identi', 'wi_koraki', 'wi_slike', 'spl_identi', 'wi_uvozi'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', t || '_select', t);
    execute format('drop policy if exists %I on %I', t || '_insert', t);
    execute format('drop policy if exists %I on %I', t || '_update', t);
    execute format('create policy %I on %I for select to authenticated using (true)', t || '_select', t);
    execute format('create policy %I on %I for insert to authenticated with check (wi_je_admin())', t || '_insert', t);
    execute format(
      'create policy %I on %I for update to authenticated using (wi_je_admin()) with check (wi_je_admin())',
      t || '_update', t);
  end loop;
end;
$$;

-- Slike koraka se smejo brisati (admin)
drop policy if exists wi_slike_delete on wi_slike;
create policy wi_slike_delete on wi_slike for delete to authenticated using (wi_je_admin());

-- =====================================================================
-- STORAGE: bucket wi_slike (zaseben, dostop prek podpisanih URL-jev)
-- Branje: prijavljeni; nalaganje / zamenjava / brisanje: admini.
-- =====================================================================
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('wi_slike', 'wi_slike', false, 10485760, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

-- Bucket je bil ustvarjen ročno: zaklenemo ga (brez javnih povezav), omejimo na slike do 10 MB
update storage.buckets
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp']
where id = 'wi_slike';

drop policy if exists "wi_slike_select" on storage.objects;
drop policy if exists "wi_slike_insert" on storage.objects;
drop policy if exists "wi_slike_update" on storage.objects;
drop policy if exists "wi_slike_delete" on storage.objects;

create policy "wi_slike_select" on storage.objects
  for select to authenticated using (bucket_id = 'wi_slike');
create policy "wi_slike_insert" on storage.objects
  for insert to authenticated with check (bucket_id = 'wi_slike' and wi_je_admin());
create policy "wi_slike_update" on storage.objects
  for update to authenticated using (bucket_id = 'wi_slike' and wi_je_admin());
create policy "wi_slike_delete" on storage.objects
  for delete to authenticated using (bucket_id = 'wi_slike' and wi_je_admin());
