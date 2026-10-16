# FINES_WorkInstructions

Navodila za delo v proizvodnji in montaži (Fines - Work Instructions). Next.js + Supabase (ista baza in prijava kot FINES_Production).

## Zagon

1. `.env.local` (glej `.env.example`) - URL in publishable ključ Supabase.
2. `npm install`, nato `npm run dev` -> http://localhost:3000

## Baza

1. Supabase -> Authentication -> Users -> Add user: admin uporabnik (Auto Confirm). Gesla se ne pišejo v kodo ali git.
2. Supabase -> SQL Editor: zaženi migracije po vrsti (`supabase/migrations/001_schema.sql`, `002_priprava.sql`, `003_koncna_slika.sql`; idempotentno).
3. V aplikaciji: admin dostop (ikona ščita) -> Admin -> Nastavitve -> Uvoz šifer -> `sifre.xls`.

Tabele: `wi_` (projekt), `ln_wi_` (povezovalne), `spl_identi` (šifrant artiklov, skupna tabela).
Pisanje v `wi_` tabele in bucket `wi_slike` je dovoljeno samo uporabnikom iz tabele `wi_admini`.

## Struktura

- `/` - skeniranje delovnega naloga ali identa (navodila se odprejo sama)
- `/navodila/[id]` - prikaz navodila
- `/proizvodnja/navodila` - pregled vseh navodil
- `/admin/programi`, `/admin/povezave`, `/admin/nastavitve` - urejanje (samo admin)
