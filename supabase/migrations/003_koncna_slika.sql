-- =====================================================================
-- FINES - Work Instructions | 003: končna slika proizvoda
-- Slika zaključenega proizvoda programa (prikaz na karticah navodil).
-- Datoteka je v bucketu wi_slike (programi/{id}/koncna-....jpg).
-- Zaženi PO 002_priprava.sql. Idempotentno.
-- =====================================================================

alter table wi_programi add column if not exists koncna_slika text;
