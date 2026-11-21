# Znanje training grounda

Potrjena spoznanja in pravila za izdelavo 3D video navodil. Bereta ga **oba AI-ja** pred vsakim poskusom. Pravila tukaj imajo prednost pred predlogi v `NALOGA_ZA_AI.md`.

Kako se dopolnjuje:
- AI predloge zapiše v `spoznanja.md` svojega poskusa (v aplikaciji: zavihek **Spoznanja**).
- Človek predlog preveri in ga prenese sem. AI-ja te datoteke ne spreminjata.
- Vsaka točka ima vir (model / poskus ali odločitev človeka), da se ve, od kod je.

Oznake: **PRAVILO** = obvezno upoštevaj · **DEJSTVO** = preverjeno · **DOMNEVA** = še ni potrjeno, preveri.

---

## Proces montaže (polizdelki in končni izdelki)

> V pripravi. Montaža sledi procesu izdelave polizdelkov in končnih izdelkov, ki iz kosovnice ni (v celoti) razviden. Tukaj bodo navodila, kateri sklopi so polizdelki, kateri končni izdelki in v kakšnem zaporedju nastajajo.

- PRAVILO: Zaporedja montaže in delitve na polizdelke ne sklepaj samo iz kosovnice ali oblike. Kar ni določeno tukaj ali v `model.json`, označi kot `ni znano / zahteva potrditev`. (vir: odločitev, 21. 11. 2026)

## CAD uvoz (STEP)

- DEJSTVO: STEP vsebuje natančno B-Rep geometrijo (ploskve, robovi), ne trikotnikov. Za prikaz / animacijo jo je treba z CAD jedrom (npr. OpenCascade) tesselirati v mrežo. (vir: splošno znanje, 21. 11. 2026)
- PRAVILO: Ne predpostavljaj, da STEP ohrani drevo sestava, imena ali podatke iz izvornega CAD-a (Inventor). Preveri na dejanski datoteki. (vir: začetni kontekst)

## Mreža (tesselacija)

## Identifikacija delov

## Montaža

## Animacija

## Render / video

## Orodja in okolje

- DEJSTVO: Na delovnem računalniku so Windows 11, Python 3.15, ffmpeg 9.0, Node 24; Blender in FreeCAD nista nameščena. (vir: preverjeno 21. 11. 2026)
- DOMNEVA: CAD paketi za Python (`cadquery`, `OCP`) morda še nimajo izdaje za Python 3.15. V tem primeru uporabi starejši Python v `trening/okolje/<ai>/`. (vir: 21. 11. 2026, ni preverjeno)

## Ocenjevanje (kaj človek pričakuje)

- PRAVILO: Ob slabi oceni se pričakuje diagnoza vzroka in boljša rešitev (orodje, postopek, kontrola), ne samo ponovno generiranje z drugimi parametri. (vir: odločitev, 21. 11. 2026)
