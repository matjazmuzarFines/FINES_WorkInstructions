from datetime import datetime
from importlib.metadata import version
import platform
import subprocess
from osnova import OUT, EXPORT, SOURCE, read, save
import imageio_ffmpeg


def publish(start):
    cad=read(EXPORT/"kontrola_cad.json")
    glb=read(EXPORT/"kontrola_glb.json")
    vid=read(EXPORT/"kontrola_videa.json")
    parts=read(OUT/"deli.json")
    hits=cad["poti"]["P117"]["dejanski_preseki_mm3_po_odmiku_mm"]["0"]
    limits=cad["bbox_mm"]
    dims=" × ".join(f"{b-a:.2f}".replace(".",",") for a,b in zip(limits["min"],limits["max"]))
    margin=min(glb["robovi_pogleda_px"]["sestav"])
    pid_sections=", ".join(f"{pid} ({v:.2f} mm³)".replace(".",",") for pid,v in hits.items())
    issues=["Zaporedje, podpiranje vozička, pritrditev in dovoljene tolerance zahtevajo potrditev.",
            "V končni legi P117 ima CAD majhen prostorninski presek s štirimi zgornjimi povezavami.",
            "ID-ji pojavitev so vezani na to revizijo datoteke STEP."]
    packages=["cadquery-ocp-novtk","numpy","Pillow","moderngl","glcontext","imageio-ffmpeg"]
    ff=subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(),"-version"]).decode().splitlines()[0].split()[2]
    tools=["Python "+platform.python_version()]+[f"{p} {version(p)}" for p in packages]+["FFmpeg "+ff]
    report=f"""# Mali delovni voziček · Astra 01

Posnetek prikazuje dva neodvisna premika. Kolo z zavoro P123 se dvigne za 105 mm do plošče P113. Zgornja polica P117 se spusti za 145 mm v lego iz modela. Obe animaciji trajata po 3,2 s. Pri polici končna lega zahteva pregled konstruktorja.

## Kaj je v datoteki STEP

- Vir je **{SOURCE.name}**, AP214, izvoz iz Autodesk Inventor 2027. Kontrolna vsota SHA-256 je zapisana v __BT__izvoz/kontrola_cad.json__BT__.
- Datoteka vsebuje {cad['product']} zapisov PRODUCT. Od tega je en korenski sestav MLU123069200, en podsestav ročaja MLU124029200 in {cad['razlicni_listi']} različnih izdelkov na listih drevesa. Preštel sem {cad['nauo']} povezav NEXT_ASSEMBLY_USAGE_OCCURRENCE. Ena od njih vodi v podsestav s tremi deli.
- Inventura ima **{len(parts)} pojavitev delov**. V datoteki je {cad['manifold_solid_brep']} definicij MANIFOLD_SOLID_BREP. Štetje vseh postavljenih teles v korenu Open CASCADE da **{cad['telesa_korena']} teles**. Štiri kolesa prispevajo po 17 teles, ostalih 24 pojavitev po eno. Posamezno kolo je v drevesu en izdelek.
- Dolžinska enota iz STEPControl je milimeter. Mere celotnega sestava v izvornih oseh X × Y × Z so **{dims} mm**. Skrajne točke vključujejo ročaj in obrnjena kolesa. Z je navzgor. Ohranjen je izvorni koordinatni začetek.
- __BT__deli.json__BT__ hrani šifro in opis PRODUCT, pot do pojava, številki PRODUCT in NAUO, točno omejitveno škatlo B-Rep ter prostornino v mm³. P123 izhaja iz pojava #123. Pri ponovnem izvozu iz Inventorja se številke entitet lahko spremenijo. Za primerjavo revizij sta uporabnejši šifra in pot.

## Izbira postopka

| Korak | Obravnavani možnosti | Izbira in razlog |
|---|---|---|
| Uvoz | Običajni STEPControl ali STEPCAFControl z XCAF | XCAF ohrani pojav, referenčno obliko in njeno transformacijo. Iz izvirnih zapisov PRODUCT in NAUO dopolnim opise in preverim starševstvo. |
| Mreža | STL za vsak pojav ali indeksirana mreža Open CASCADE v GLB | GLB ohrani imena, transformacije, normale in dve animaciji. Enako geometrijo več pojavitev shrani enkrat. |
| Animacija | Ročno postavljanje ključev v Blenderju ali premik iz podatkov koraka | Gladka kubična interpolacija med odmikom in CAD-lego omogoča ponovitev in spremembo giba. V GLB imata dela ločena animacijska posnetka. |
| Render | Blender ali lokalni ModernGL, Pillow in FFmpeg | ModernGL lahko neposredno prebere isti izpisani GLB. Globinski medpomnilnik določa zakrivanje. Pillow doda oznake, FFmpeg izdela H.264. |

CAD-jedro tesselira vsako referenčno obliko pri absolutnem odstopanju 0,12 mm in kotu 0,20 rad. Na dveh ploskvah kolesa osnovna nastavitev ni vrnila trikotnikov. Skripta ločeno tesselira kopijo take ploskve z manjšim odstopanjem, dokler ima vsaka ploskev mrežo. Prvotna oblika za izmere ostane dostopna. Izris celotnega sestava uporabi {cad['trikotniki']:,} trikotnikov. GLB pretvori CAD (X, Y, Z) v (X, Z, −Y) in milimetre v metre. Skupina ročaja ohrani hierarhijo. Njeni otroci imajo transformacije glede na skupino z identitetno matriko. Barve so izbrane za prikaz.

## Samokontrola

| Preizkus | Rezultat |
|---|---|
| Drevo in telesa | Vseh {cad['nauo']} zvez iz surovega STEP-a se ujema z obiskom pojavitev. Vsota teles v inventuri se ujema s številom v oblikovanem korenu. |
| Ponovno branje GLB | Vsi ID-ji so dosegljivi v drevesu scene, obe animaciji ciljata pravi ID ter imata pravilen začetni odmik in končno lego. Največja razlika med šestimi mejami mreže in B-Rep na kateremkoli delu je {glb['najvecja_razlika_bbox_mm']:.3f} mm. |
| Kolo P123 | Omejitvena škatla kolesa vzdolž celotnega dviga nima prostorninskega prekrivanja z drugimi deli pri pragu 0,0001 mm. Zgornja meja kolesa in spodnja meja P113 v končni legi sta pri Z = 567 mm. |
| Polica P117 | Preseki B-Rep v končni legi so {pid_sections}. Pri navpičnih odmikih 0,5, 2, 8, 16 in 25 mm so vsi štirje izračunani preseki ničelni. To so vzorčene lege. Konstruktor mora potrditi naleganje in tolerance. |
| Kamera | Projekcija vseh oglišč celega sestava pusti na vsaki strani vsaj {margin:.0f} px prostora. Pri podrobnih pogledih sta preverjeni obe skrajni legi aktivnega dela. Oranžna označuje izbrani del, ločen pogled levo kaže njegovo obliko. |
| Zapis videa | FFmpeg je dekodiral vseh {vid['dekodirane_slike']} slik. H.264, 1280 × 720, 25 slik/s, 24,6 s. Devet kadrov iz končnega MP4 je v __BT__izvoz/kontrolni_kadri.jpg__BT__. |

Presek je geometrijski rezultat iz te revizije. Meritve, dovoljene tolerance, dejanska zračnost, pritrditev, nosilnost, podpiranje in vrstni red montaže so **ni znano / zahteva potrditev**. Prikazana odmika sta izbrana za preglednost gibanja. Stolpci inventure in kote kamer je mogoče preveriti brez videa v datotekah JSON.

## Ponovitev

Ukazi so za PowerShell v korenu repozitorija na Windows z OpenGL 3.3 in pisavami Segoe UI ter Consolas. Prvi blok pripravi namensko okolje s CPython 3.12 x64. Na tem računalniku je ta različica tudi v lokalnem okolju Codex. Za namestitev paketov je potreben dostop do PyPI. Obdelava STEP-a poteka lokalno.

__FENCE__powershell
$poskus = 'trening/modeli/vozicek-delovni-mali/astra/01'
$okolje = 'trening/okolje/astra/venv-vozicek-312'
$osnovniPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $osnovniPython -m venv $okolje
& "$okolje/Scripts/python.exe" -m pip install -r "$poskus/skripte/requirements.txt"
__FENCE__

Pri vsaki izdelavi nato izvedi naslednja ukaza iz korena repozitorija.

__FENCE__powershell
$poskus = 'trening/modeli/vozicek-delovni-mali/astra/01'
& 'trening/okolje/astra/venv-vozicek-312/Scripts/python.exe' -B -X utf8 "$poskus/skripte/ponovi.py"
__FENCE__

__BT__ponovi.py__BT__ izdela vse rezultate v mapi poskusa. Nastavitve korakov in kamer določa funkcija __BT__steps()__BT__ v __BT__izvoz.py__BT__. Za spremembo časovnice in napisov je pristojna __BT__film.py__BT__. Preizkusi, ki zaznajo neskladje pri uvozu, mejah, kadriranju ali dekodiranju, ustavijo izdelavo pred zapisom uspešnega statusa.

## Naslednji poskus

Konstruktor naj preveri štiri naležne robove P117 in poda dovoljene tolerance. Tehnolog naj potrdi način podpiranja vozička pri montaži kolesa in pošlje kosovnico ter vrstni red pritrjevanja. Nato bo mogoče prikaz pripraviti kot proizvodno navodilo in navesti dejanske kontrolne mere.
""".replace("__BT__",chr(96)).replace("__FENCE__",chr(96)*3)
    (OUT/"porocilo.md").write_text(report,encoding="utf-8")
    lessons="""# Predlogi za skupno znanje

- [CAD uvoz] Pri tem sestavu 28 definicij MANIFOLD_SOLID_BREP, 28 pojavitev izdelkov in 92 postavljenih teles opisuje tri različna štetja. Vsako od štirih koles združuje 17 teles. Korenski pregled in seštevek po pojavih sta oba dala 92.
- [Identifikacija delov] V tem izvozu je ime PRODUCT šifra, opis izdelka pa je v tretjem besedilnem polju. Združitev fizičnih vrstic in dekodiranje STEP X2 sta obnovila opisa »Plošča kolesa« in »Nosilec ročaja«.
- [Mreža] Uspešno zaključen BRepMesh ne zagotavlja mreže vsake ploskve. Dve ploskvi kolesa po prvem prehodu nista imeli trikotnikov. Tesseliranje posamezne kopije ploskve z manjšim odstopanjem je uspelo pri obeh.
- [Montaža] Pri P117 bi samo pregled slike spregledal presek s štirimi povezavami. Presek B-Rep v končni legi je znašal približno 2,64–5,31 mm³ na povezavo, pri odmiku 0,5 mm pa nič.
- [Animacija] Enako definirana premika je bilo mogoče zapisati kot ločeni animaciji glTF in uporabiti za video. Ponovno branje glTF je preverilo ciljni ID, odmik in končno lego obeh delov.
- [Igrišče] Predlog za model.json je polje za dovoljene konstrukcijske tolerance in revizijo. Ta poskus lahko izmeri stik P117 s povezavami, podatek za presojo sprejemljivosti pa manjka.
"""
    (OUT/"spoznanja.md").write_text(lessons,encoding="utf-8")
    save(OUT/"meta.json",dict(ai_model="gpt-6.2-astra",zacetek=start.isoformat(timespec="seconds"),
        konec=datetime.now().astimezone().isoformat(timespec="seconds"),status="uspeh",
        povzetek="28 pojavitev, 92 teles in dve animaciji v GLB. Video prikazuje dvig kolesa in spust zgornje police. Pri polici so v CAD-legi izmerjeni majhni preseki.",
        orodja=tools,tezave=issues))

