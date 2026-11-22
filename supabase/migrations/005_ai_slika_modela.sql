-- =====================================================================
-- FINES - Work Instructions | 005: sličica modela v AI treningu
-- Sličica iz STEP (trening/modeli/<id>/slika.png) se ob objavi naloži v bucket wi_trening
-- (<koda>/slika.png); pot je v wi_ai_modeli.slika. Prikaz: stolpec Model v Pregledu treningov.
-- Zaženi PO 004_ai_orodja.sql. Idempotentno.
-- =====================================================================

alter table wi_ai_modeli add column if not exists slika text;
