# Mali delovni voziček · Astra 01

Posnetek prikazuje dva neodvisna premika. Kolo z zavoro P123 se dvigne za 105 mm do plošče P113. Zgornja polica P117 se spusti za 145 mm v lego iz modela. Obe animaciji trajata po 3,2 s. Pri polici končna lega zahteva pregled konstruktorja.

## Kaj je v datoteki STEP

- Vir je **MLU123069200 _1_.stp**, AP214, izvoz iz Autodesk Inventor 2027. Kontrolna vsota SHA-256 je zapisana v `izvoz/kontrola_cad.json`.
- Datoteka vsebuje 14 zapisov PRODUCT. Od tega je en korenski sestav MLU123069200, en podsestav ročaja MLU124029200 in 12 različnih izdelkov na listih drevesa. Preštel sem 29 povezav NEXT_ASSEMBLY_USAGE_OCCURRENCE. Ena od njih vodi v podsestav s tremi deli.
- Inventura ima **28 pojavitev delov**. V datoteki je 28 definicij MANIFOLD_SOLID_BREP. Štetje vseh postavljenih teles v korenu Open CASCADE da **92 teles**. Štiri kolesa prispevajo po 17 teles, ostalih 24 pojavitev po eno. Posamezno kolo je v drevesu en izdelek.
- Dolžinska enota iz STEPControl je milimeter. Mere celotnega sestava v izvornih oseh X × Y × Z so **1138,81 × 506,00 × 891,89 mm**. Skrajne točke vključujejo ročaj in obrnjena kolesa. Z je navzgor. Ohranjen je izvorni koordinatni začetek.
- `deli.json` hrani šifro in opis PRODUCT, pot do pojava, številki PRODUCT in NAUO, točno omejitveno škatlo B-Rep ter prostornino v mm³. P123 izhaja iz pojava #123. Pri ponovnem izvozu iz Inventorja se številke entitet lahko spremenijo. Za primerjavo revizij sta uporabnejši šifra in pot.

## Izbira postopka

| Korak | Obravnavani možnosti | Izbira in razlog |
|---|---|---|
| Uvoz | Običajni STEPControl ali STEPCAFControl z XCAF | XCAF ohrani pojav, referenčno obliko in njeno transformacijo. Iz izvirnih zapisov PRODUCT in NAUO dopolnim opise in preverim starševstvo. |
| Mreža | STL za vsak pojav ali indeksirana mreža Open CASCADE v GLB | GLB ohrani imena, transformacije, normale in dve animaciji. Enako geometrijo več pojavitev shrani enkrat. |
| Animacija | Ročno postavljanje ključev v Blenderju ali premik iz podatkov koraka | Gladka kubična interpolacija med odmikom in CAD-lego omogoča ponovitev in spremembo giba. V GLB imata dela ločena animacijska posnetka. |
| Render | Blender ali lokalni ModernGL, Pillow in FFmpeg | ModernGL lahko neposredno prebere isti izpisani GLB. Globinski medpomnilnik določa zakrivanje. Pillow doda oznake, FFmpeg izdela H.264. |

CAD-jedro tesselira vsako referenčno obliko pri absolutnem odstopanju 0,12 mm in kotu 0,20 rad. Na dveh ploskvah kolesa osnovna nastavitev ni vrnila trikotnikov. Skripta ločeno tesselira kopijo take ploskve z manjšim odstopanjem, dokler ima vsaka ploskev mrežo. Prvotna oblika za izmere ostane dostopna. Izris celotnega sestava uporabi 671,548 trikotnikov. GLB pretvori CAD (X, Y, Z) v (X, Z, −Y) in milimetre v metre. Skupina ročaja ohrani hierarhijo. Njeni otroci imajo transformacije glede na skupino z identitetno matriko. Barve so izbrane za prikaz.

## Samokontrola

| Preizkus | Rezultat |
|---|---|
| Drevo in telesa | Vseh 29 zvez iz surovega STEP-a se ujema z obiskom pojavitev. Vsota teles v inventuri se ujema s številom v oblikovanem korenu. |
| Ponovno branje GLB | Vsi ID-ji so dosegljivi v drevesu scene, obe animaciji ciljata pravi ID ter imata pravilen začetni odmik in končno lego. Največja razlika med šestimi mejami mreže in B-Rep na kateremkoli delu je 0.052 mm. |
| Kolo P123 | Omejitvena škatla kolesa vzdolž celotnega dviga nima prostorninskega prekrivanja z drugimi deli pri pragu 0,0001 mm. Zgornja meja kolesa in spodnja meja P113 v končni legi sta pri Z = 567 mm. |
| Polica P117 | Preseki B-Rep v končni legi so P109 (5,31 mm³), P110 (5,31 mm³), P111 (2,64 mm³), P112 (2,64 mm³). Pri navpičnih odmikih 0,5, 2, 8, 16 in 25 mm so vsi štirje izračunani preseki ničelni. To so vzorčene lege. Konstruktor mora potrditi naleganje in tolerance. |
| Kamera | Projekcija vseh oglišč celega sestava pusti na vsaki strani vsaj 67 px prostora. Pri podrobnih pogledih sta preverjeni obe skrajni legi aktivnega dela. Oranžna označuje izbrani del, ločen pogled levo kaže njegovo obliko. |
| Zapis videa | FFmpeg je dekodiral vseh 615 slik. H.264, 1280 × 720, 25 slik/s, 24,6 s. Devet kadrov iz končnega MP4 je v `izvoz/kontrolni_kadri.jpg`. |

Presek je geometrijski rezultat iz te revizije. Meritve, dovoljene tolerance, dejanska zračnost, pritrditev, nosilnost, podpiranje in vrstni red montaže so **ni znano / zahteva potrditev**. Prikazana odmika sta izbrana za preglednost gibanja. Stolpci inventure in kote kamer je mogoče preveriti brez videa v datotekah JSON.

## Ponovitev

Ukazi so za PowerShell v korenu repozitorija na Windows z OpenGL 3.3 in pisavami Segoe UI ter Consolas. Prvi blok pripravi namensko okolje s CPython 3.12 x64. Na tem računalniku je ta različica tudi v lokalnem okolju Codex. Za namestitev paketov je potreben dostop do PyPI. Obdelava STEP-a poteka lokalno.

```powershell
$poskus = 'trening/modeli/vozicek-delovni-mali/astra/01'
$okolje = 'trening/okolje/astra/venv-vozicek-312'
$osnovniPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $osnovniPython -m venv $okolje
& "$okolje/Scripts/python.exe" -m pip install -r "$poskus/skripte/requirements.txt"
```

Pri vsaki izdelavi nato izvedi naslednja ukaza iz korena repozitorija.

```powershell
$poskus = 'trening/modeli/vozicek-delovni-mali/astra/01'
& 'trening/okolje/astra/venv-vozicek-312/Scripts/python.exe' -B -X utf8 "$poskus/skripte/ponovi.py"
```

`ponovi.py` izdela vse rezultate v mapi poskusa. Nastavitve korakov in kamer določa funkcija `steps()` v `izvoz.py`. Za spremembo časovnice in napisov je pristojna `film.py`. Preizkusi, ki zaznajo neskladje pri uvozu, mejah, kadriranju ali dekodiranju, ustavijo izdelavo pred zapisom uspešnega statusa.

## Naslednji poskus

Konstruktor naj preveri štiri naležne robove P117 in poda dovoljene tolerance. Tehnolog naj potrdi način podpiranja vozička pri montaži kolesa in pošlje kosovnico ter vrstni red pritrjevanja. Nato bo mogoče prikaz pripraviti kot proizvodno navodilo in navesti dejanske kontrolne mere.
