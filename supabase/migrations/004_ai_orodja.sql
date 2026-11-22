-- =====================================================================
-- FINES - Work Instructions | 004: AI orodja
--  * objava AI treninga na produkcijo (lokalni strežnik -> Supabase, produkcija samo bere)
--  * AI video creation: zahteve razvojnikov z datotekami (STEP, kosovnica, slike, pojasnila)
--  * poraba API kreditov (mesečni proračun, npr. 100 $ z naročnino Max)
-- Zaženi PO 003_koncna_slika.sql. Idempotentno.
-- =====================================================================

-- ---------------------------------------------------------------------
-- AI TRENING (objava) - piše samo gumb "Objavi na produkcijo" na lokalnem strežniku
-- ---------------------------------------------------------------------
create table if not exists wi_ai_modeli (
  id             bigint generated always as identity primary key,
  koda           text not null unique,          -- ime mape trening/modeli/<koda>
  naziv          text not null,
  opis           text,
  zahteva_id     bigint,                        -- zahteva AI video creation, iz katere je model nastal
  objavljeno_at  timestamptz,
  visible        boolean not null default true,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create table if not exists wi_ai_poskusi (
  id               bigint generated always as identity primary key,
  model_id         bigint not null references wi_ai_modeli(id),
  ai               text not null,               -- astra / fable
  poskus           text not null,               -- 01, 02 ...
  meta             jsonb,
  deli             jsonb,
  koraki           jsonb,
  porocilo         text,
  spoznanja        text,
  video            text,                        -- pot v bucketu wi_trening
  video_velikost   bigint,
  predogled        text,                        -- pot v bucketu wi_trening
  ocena            jsonb,
  visible          boolean not null default true,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint wi_ai_poskusi_uq unique (model_id, ai, poskus)
);

-- Skupna besedila treninga (npr. kljuc = 'znanje' -> trening/ZNANJE.md)
create table if not exists wi_ai_besedila (
  id          bigint generated always as identity primary key,
  kljuc       text not null unique,
  vsebina     text,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- AI VIDEO CREATION - zahteve razvojnikov
-- ---------------------------------------------------------------------
create table if not exists wi_ai_zahteve (
  id          bigint generated always as identity primary key,
  naziv       text not null,
  opis        text,                             -- pojasnila razvojnika (posebnosti sestava)
  status      text not null default 'oddano'
              check (status in ('oddano', 'v_delu', 'koncano', 'zavrnjeno')),
  oddal       text not null default coalesce(auth.jwt() ->> 'email', ''),
  nacin       text not null default 'lokalno'   -- lokalno (naročnina v VS Code) / api (krediti)
              check (nacin in ('lokalno', 'api')),
  model_koda  text,                             -- model v treningu (trening/modeli/<koda>)
  opomba      text,                             -- opomba admina (npr. razlog zavrnitve)
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists wi_ai_zahteve_status_idx on wi_ai_zahteve(status) where visible;

create table if not exists wi_ai_zahteve_datoteke (
  id          bigint generated always as identity primary key,
  zahteva_id  bigint not null references wi_ai_zahteve(id),
  vrsta       text not null check (vrsta in ('step', 'kosovnica', 'slika', 'drugo')),
  ime         text not null,
  pot         text not null,                    -- pot v bucketu wi_ai_vhod
  velikost    bigint,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- PORABA API KREDITOV
-- ---------------------------------------------------------------------
create table if not exists wi_ai_poraba (
  id                  bigint generated always as identity primary key,
  zahteva_id          bigint references wi_ai_zahteve(id),
  model               text not null,            -- npr. claude-opus-5-5
  vhodni_zetoni       bigint not null default 0,
  izhodni_zetoni      bigint not null default 0,
  cache_branje        bigint not null default 0,
  cache_pisanje       bigint not null default 0,
  cena_usd            numeric(12, 4) not null default 0,
  opis                text,
  visible             boolean not null default true,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create table if not exists wi_ai_nastavitve (
  id          bigint generated always as identity primary key,
  kljuc       text not null unique,
  vrednost    jsonb not null,
  visible     boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Mesečni proračun API kreditov (Max 5x = 100 $ / mesec); dan_obnove = dan v mesecu, ko se krediti obnovijo
insert into wi_ai_nastavitve (kljuc, vrednost)
values ('proracun', '{"mesecni_usd": 100, "dan_obnove": 1, "api_vklopljen": false}')
on conflict (kljuc) do nothing;

-- updated_at
do $$
declare t text;
begin
  foreach t in array array[
    'wi_ai_modeli', 'wi_ai_poskusi', 'wi_ai_besedila', 'wi_ai_zahteve', 'wi_ai_zahteve_datoteke',
    'wi_ai_poraba', 'wi_ai_nastavitve'
  ] loop
    execute format('drop trigger if exists %I on %I', t || '_updated_at', t);
    execute format(
      'create trigger %I before update on %I for each row execute function wi_set_updated_at()',
      t || '_updated_at', t);
  end loop;
end;
$$;

-- ---------------------------------------------------------------------
-- RLS - branje: prijavljeni; pisanje: admini. Brez DELETE (visible = false).
-- ---------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array[
    'wi_ai_modeli', 'wi_ai_poskusi', 'wi_ai_besedila', 'wi_ai_zahteve', 'wi_ai_zahteve_datoteke',
    'wi_ai_poraba', 'wi_ai_nastavitve'
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

-- Zahtevo lahko odda vsak prijavljen uporabnik (razvojnik) - samo kot sebe in s statusom 'oddano'.
drop policy if exists wi_ai_zahteve_insert on wi_ai_zahteve;
create policy wi_ai_zahteve_insert on wi_ai_zahteve for insert to authenticated
  with check (
    wi_je_admin()
    or (status = 'oddano' and lower(oddal) = lower(coalesce(auth.jwt() ->> 'email', '')))
  );

-- Datoteke doda samo tisti, ki je oddal zahtevo (ali admin).
drop policy if exists wi_ai_zahteve_datoteke_insert on wi_ai_zahteve_datoteke;
create policy wi_ai_zahteve_datoteke_insert on wi_ai_zahteve_datoteke for insert to authenticated
  with check (
    wi_je_admin()
    or exists (
      select 1 from wi_ai_zahteve z
      where z.id = zahteva_id and lower(z.oddal) = lower(coalesce(auth.jwt() ->> 'email', ''))
    )
  );

-- ---------------------------------------------------------------------
-- STORAGE
--  wi_trening: videi in predogledi objavljenih poskusov (branje prijavljeni, pisanje admini)
--  wi_ai_vhod: datoteke zahtev (STEP, kosovnice, slike) - nalaga prijavljen uporabnik,
--              bere admin ali tisti, ki je datoteko naložil
-- Omejitev 50 MB na datoteko (največ na brezplačnem Supabase paketu).
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('wi_trening', 'wi_trening', false, 52428800, array['video/mp4', 'video/webm', 'image/png', 'image/jpeg'])
on conflict (id) do update
set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('wi_ai_vhod', 'wi_ai_vhod', false, 52428800, null)
on conflict (id) do update
set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = null;

drop policy if exists "wi_trening_select" on storage.objects;
drop policy if exists "wi_trening_insert" on storage.objects;
drop policy if exists "wi_trening_update" on storage.objects;
drop policy if exists "wi_trening_delete" on storage.objects;
create policy "wi_trening_select" on storage.objects
  for select to authenticated using (bucket_id = 'wi_trening');
create policy "wi_trening_insert" on storage.objects
  for insert to authenticated with check (bucket_id = 'wi_trening' and wi_je_admin());
create policy "wi_trening_update" on storage.objects
  for update to authenticated using (bucket_id = 'wi_trening' and wi_je_admin());
create policy "wi_trening_delete" on storage.objects
  for delete to authenticated using (bucket_id = 'wi_trening' and wi_je_admin());

drop policy if exists "wi_ai_vhod_select" on storage.objects;
drop policy if exists "wi_ai_vhod_insert" on storage.objects;
drop policy if exists "wi_ai_vhod_delete" on storage.objects;
create policy "wi_ai_vhod_select" on storage.objects
  for select to authenticated using (bucket_id = 'wi_ai_vhod' and (wi_je_admin() or owner = auth.uid()));
create policy "wi_ai_vhod_insert" on storage.objects
  for insert to authenticated with check (bucket_id = 'wi_ai_vhod');
create policy "wi_ai_vhod_delete" on storage.objects
  for delete to authenticated using (bucket_id = 'wi_ai_vhod' and wi_je_admin());
