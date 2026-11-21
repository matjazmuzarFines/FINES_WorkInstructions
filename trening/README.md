# AI trening (training ground)

Igrišče za primerjavo dveh AI-jev pri izdelavi 3D video navodil za montažo iz STEP modela:

- **GPT-6.2 Astra** - chat v Codexu (VS Code),
- **Claude Fable 5.2** - chat v Claude Code (VS Code).

Oba dobita isti model in isto nalogo ([NALOGA_ZA_AI.md](NALOGA_ZA_AI.md)), vsak piše v svojo mapo. Rezultate primerjaš in oceniš v aplikaciji: **Admin → Orodja → AI trening** (`/admin/trening`).

API ključi niso potrebni: AI-ja delata v VS Code, aplikacija samo bere mapo z diska.

## Postopek

1. **Dodaj model**: v aplikaciji klikni *Nov model* (naziv, opis, STEP datoteka). Druga možnost je ročno: ustvari `modeli/<id>/model.json` in STEP daj v `modeli/<id>/vhod/`.
2. **Kopiraj prompt**: v aplikaciji na strani Astre klikni *Prompt 01* in ga prilepi v Codex, enako na strani Fable za Claude Code.
3. Počakaj, da oba končata, nato v aplikaciji klikni **Osveži**.
4. Primerjaj videa (*Predvajaj oba*), poročila, korake in dele. Vsak poskus oceni v zavihku **Ocena**.
5. Za izboljšavo kopiraj *Prompt 02*. AI prebere svojo oceno in komentar, poišče vzrok težav in boljšo rešitev ter naredi nov poskus. Diagnozo zapiše na začetek poročila.
6. **Znanje**: v zavihku *Spoznanja* AI predlaga, kaj se je naučil. Dobre predloge prenesi v [ZNANJE.md](ZNANJE.md) (ročno ali prosi enega od AI-jev). Ta datoteka velja za oba AI-ja in vse naslednje poskuse, zato vanjo sodijo tudi tvoja pravila (npr. kateri sklopi so polizdelki).

## Struktura

```
trening/
  NALOGA_ZA_AI.md          skupna naloga in format izhoda (enaka za oba AI-ja)
  ZNANJE.md                potrjena pravila in spoznanja (bereta oba, ureja človek)
  okolje/<ai>/             orodja in venv posameznega AI-ja (ni v gitu)
  modeli/<id>/
    model.json             naziv, opis
    vhod/                  STEP (kasneje BOM) - ni v gitu
    ocene.json             tvoje ocene (piše aplikacija)
    astra/01/, 02/ ...     poskusi Astre
    fable/01/, 02/ ...     poskusi Fable
```

## Git

V git **ne gredo** (`.gitignore`): `vhod/`, `okolje/`, STEP, video, GLB/OBJ in Blender datoteke. To so interni konstrukcijski podatki, poleg tega so datoteke velike. V git gredo `meta.json`, `porocilo.md`, `deli.json`, `koraki.json`, skripte in ocene, tako da ostane zgodovina primerjav.

## Varnost

Stran deluje samo na lokalnem strežniku (na Vercelu je izklopljena) in samo za admine (`wi_admini`). Lokalni strežnik teče na `0.0.0.0`, zato API preveri prijavo za vsako datoteko. Vhodnih STEP datotek API ne vrača.
