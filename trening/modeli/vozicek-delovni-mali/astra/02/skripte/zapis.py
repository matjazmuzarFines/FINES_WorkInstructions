from datetime import datetime
from importlib.metadata import version
import platform
import subprocess
from osnova import OUT,EXPORT,read,save
import imageio_ffmpeg

def publish(started):
    cad=read(EXPORT/"kontrola_cad.json");g=read(EXPORT/"kontrola_glb.json");v=read(EXPORT/"kontrola_videa.json")
    mats=cad["materiali"];parts=read(OUT/"deli.json");steps=read(OUT/"koraki.json");sites=read(EXPORT/"pritrdilna_mesta.json")
    orig=read(OUT.parent/"01"/"deli.json")
    ids=lambda p:{a["id"]:a["pot"] for a in p if "pot" in a}
    assert ids(orig)==ids(parts) and len(ids(parts))==28
    lookup={p["id"] for p in parts}
    assert all(set(s["deli"]+s["referencni_deli"])<=lookup for s in steps)
    assert {s["id"] for s in sites}=={i for s in steps if s["gibanje"]["tip"]=="vijak" for i in s["deli"]}
    assert v["dekodirane_slike"]==1875
    psnr=min(v["psnr_kadrov_db"].values());nframes=len(v["psnr_kadrov_db"])
    ff=subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(),"-version"]).decode().split()[2]
    tools=["Python "+platform.python_version()]+[p+" "+version(p) for p in ("cadquery-ocp-novtk","numpy","moderngl","glcontext","Pillow","imageio-ffmpeg")]+["FFmpeg "+ff]
    report=f"""# Diagnoza poskusa 01

Ocene za Astra 01 so bile uvoz 3/5, sledljivost 4/5, animacija 3/5, razumljivost 2/5 in poštenost 2/5. V prvem posnetku je kolo prišlo do plošče, nato se je korak končal. Monter iz tega ni mogel razbrati, kako se dela pritrdita.

| Pripomba | Ugotovljeni vzrok v 01 | Sprememba in kontrola v 02 |
|---|---|---|
| Grob videz, izguba podrobnosti in nejasni materiali | Uvoz je prebral PRODUCT, spregledal pa zapise »material name«. Vseh 17 teles kolesa je dobilo en videz. | Sledim povezavi od materialne lastnosti do izdelka. Vseh {len(mats)} različnih listov ima zapis. Na kolesu ohranim razdelitev po telesih in barvnih območjih posameznih ploskev. Mrežo ponovno izmerim po izvozu. |
| Premik ne pojasni načina sestave | Korak je določal samo začetni odmik. Isti postopek je služil za polico in kolo. | V novem prikazu se kolesa poravnajo, vijaki se zavrtijo in napredujejo, sled na izbranih stikih pokaže možni zvar. Prerez razkrije razmere v spoju. |
| Manjkali so ponovljeni spoji in posamezna mesta vijačenja | V 01 je bil izbran en pojav kolesa. Pritrdilnih mest in sorodnih pojavov skripta ni iskala. | Na vseh štirih prirobnicah poiščem notranje zanke na stični ploskvi. Štirje lokalni pogledi hkrati prikažejo vseh 16 vijakov. Za ročaj, vmesni povezavi in police obstaja individualni zapis vsakega prikazanega mesta. |
| Pritrdila, matice ali druga izvedba so lahko odsotni iz STEP-a in kosovnice | Samo opozorilo »pritrditev neznana« je izpustilo uporabnikov podatek, da so kolesa privita, in dokaze v geometriji. | Uporabnikov podatek določa vrsto spoja kolesa. Meritev določa os, shematsko pritrdilo pa ima lasten ID in vir. Osem šesterokotnih odprtin, ki se ujemajo z nosilci, je prikazanih z možnostjo navojnega vložka. Izvedba ostaja za potrditev. |
| Monter potrebuje razumljivo in pošteno navodilo | Končna lega je delovala kot zaključen spoj. ID sam ne poda dejanja ali omejitve. | Vsak kader nosi naziv in dejanje. Bakreni vijaki ter turkizni vložki so predlogi. Poseben kader pokaže, zakaj se vijak kolesa ustavi. Potrebna izbira oziroma potrditev je izpisana ob prikazu. |

## Kaj vsebuje STEP

Autodesk Inventor 2027 je izvozil sestav AP214 v milimetrih. Surovi STEP vsebuje 14 izdelkov PRODUCT, 29 povezav pojavitev NAUO in 28 definicij MANIFOLD_SOLID_BREP. Open CASCADE razširi korenski sestav na 28 pojavitev delov in 92 teles. Štiri kolesa imajo po 17 teles. Preostali deli imajo po eno. Ročaj je podsestav iz cevi in dveh nosilcev. Skrajne mere so 1138,81 × 506,00 × 891,89 mm.

V tem izvozu se zapis materiala prek lastnosti in definicije izdelka poveže s šifro dela. Sedem različnih šifer ima zapis **Steel, Mild**, dve **Stainless Steel AISI 304**, dve **Iveral**, kolo pa **Generic**. Pri kolesu so barvna območja ploskev iz STEP-a podlaga za razlikovanje prikazanih površin. Guma oziroma polimer, sijaj, premaz in dekor iverala so vizualne predpostavke. Točna sestava teh površin zahteva podatke proizvajalca.

## Prikazani spoji

| Spoj | Geometrijski dokaz | Kaj gledalec vidi |
|---|---|---|
| Ogrodje in ročaj | Pri štirih izbranih parih delov je CAD-jedro našlo skupne robove. Opis ročaja vsebuje besedo »zvarjenec«. | Premikajoča se sled označi izbrani rob oziroma stik cevi z nosilcem. Lego in dolžino proizvodnega zvara določi varilna risba. |
| Štiri kolesa | Vsaka prirobnica ima štiri reže velikosti približno 10,70 × 9,20 mm. V vseh 16 središčih so točke pri 0,1, 1,5 in 2,9 mm nad stično ploskvijo znotraj jeklene nosilne plošče. | Vsa štiri kolesa se premaknejo do svojih plošč. Pri prikazu vijakov je ohranjena dejanska prirobnica, druga telesa kolesa so skrita. Konica se ustavi pri Z = 567 mm. Prerez pokaže neprekinjeno debelino plošče na tej osi. |
| Ročaj in vmesni povezavi | Štiri izvrtine Ø 6,4 mm in štiri reže 12 × 6,5 mm imajo nasproti odprtino v stebru z gabaritom 9,1 × 10,51 mm. | Štirje vijaki za ročaj ter štirje za povezavi. Možni vložki so vidni tudi ločeno od stebra. |
| Tri police | Os vsake izbrane odprtine v jeklu vstopi v telo iverala. Spodnja polica ima 6 mest, srednja 6 spodnjih + 10 bočnih, zgornja 8 spodnjih + 18 bočnih. | Vseh 48 kandidatov ima svoj vijak. Na shemi so razločeni spodnji in bočni položaji. Pri spodnji cevi prerez razkrije pot do notranje stene. |

Vseh **72 shematskih vijakov in 8 možnih vložkov** ima vir »predlog«. To število opisuje prikaz glede na odkrite odprtine. Dejanska količina za naročilo je neznana. Samostojne, rezervne in nastavljive luknje brez ujemajočega se dela ostanejo proste. Pri vijakih so dolžina, profil, število obratov in hitrost ilustrativni. Navoj, dostop orodja, momenti, podpiranje, varilni parametri in proizvodno zaporedje so **ni znano / zahteva potrditev**.

## Odločitve in ponovljiv postopek

| Korak | Obravnavani možnosti | Izbira |
|---|---|---|
| Uvoz | Geometrijski STEPControl ali XCAF z razreševanjem lastnosti iz izvorne datoteke | XCAF ohrani pojavitve in transformacije. Povezave PROPERTY_DEFINITION_REPRESENTATION omogočajo revizijo materiala pri vsaki šifri. |
| Mreža in izvoz | STL za vsako telo ali indeksirana mreža z več materiali v GLB | GLB ima deljene mreže ponovljenih kosov, ohranjene normale in imena. Tesselacija uporablja linearno odstopanje 0,055 mm in kot 0,15 rad. Če ploskev ostane prazna, jo skripta ponovno mreži kot ločeno kopijo. |
| Priprava operacij | Ručni vnos koordinat ali izračun iz stičnih ploskev, notranjih zank in testov vsebovanosti | Druga pot razlikuje ponovljeni rob iste odprtine od dveh mest. Vsako mesto nosi nosilni del, nasprotni del, smer in dokaz. Izbor skupin spojev je prilagojen temu modelu. |
| Animacija | Sam premik ali premik z vrtenjem na lokalni osi vsakega pritrdila | Ista funkcija stanja krmili ključne sličice GLB in izris videa. Vsak vijak ima svoje izhodišče in os. |
| Render | Enobarvno senčenje ali večmaterialni izris s studijskimi odsevi, sencami in lokalnimi pogledi | ModernGL izriše iz ponovno odprtega GLB. Štirikratno glajenje robov, senčni medpomnilnik in ločljivost Full HD ohranijo obrise rež in profil vijakov. Tekstura dekorja in studijska svetloba sta del video upodobitve. |

## Samokontrola

- Vseh **28/28 izvornih ID-jev in poti** se ujema s 01. Vsaka referenca koraka obstaja v inventuri. V GLB je osnovna scena samo sestav STEP, druga scena doda shematska pritrdila. Model pretvori (X, Y, Z) v (X, Z, −Y) in milimetre v metre.
- Izris celotnega CAD-sestava porabi {cad['trikotniki']:,} trikotnikov. Največja razlika šestih mej omejitvene škatle med B-Rep in ponovno odprtim GLB je **{g['najvecja_razlika_bbox_mm']:.3f} mm** (v 01 približno 0,052 mm). To je preizkus skrajnih mer. Lokalno natančnost niti in reže je treba presojati posebej.
- Preveril sem cilje in tri časovne vzorce vsakega translacijskega oziroma rotacijskega kanala osmih animacij GLB. Izračun smeri in konice ustavi vsak prikazani vijak kolesa ob polni plošči. Prostor za orodje pri fizični montaži ostaja nepreverjen.
- Ponovljeni izračun preseka zgornje police vrne 5,31 mm³ na vsaki daljši in 2,64 mm³ na vsaki krajši povezavi. Pri dvigu za 0,5 mm vsi štirje izračuni vrnejo nič.
- FFmpeg je dekodiral vseh **{v['dekodirane_slike']} slik**. Zapis je H.264, 1920 × 1080, 25 slik/s, 75 s. Primerjava {nframes} dekodiranih slik s programsko izrisanimi referencami da najnižji PSNR {psnr:.1f} dB. Iz vsakega poglavja je izbrana slika v __BT__izvoz/kontrolni_kadri.jpg__BT__. Vizualno so preverjeni celoten sestav, štiri kolesa, prerez, detajli vložkov in dostop skozi cev.

## Kako ponoviti

PowerShell, koren repozitorija, CPython 3.12 x64, OpenGL 3.3 in pisave Windows Segoe UI, Georgia ter Consolas. Prvi blok pripravi odprtokodna orodja v namenskem okolju za Astro. Vhodni model se obdeluje lokalno.

__FENCE__powershell
$poskus = 'trening/modeli/vozicek-delovni-mali/astra/02'
$okolje = 'trening/okolje/astra/venv-vozicek-312'
$python312 = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $python312 -m venv $okolje
& "$okolje/Scripts/python.exe" -m pip install -r "$poskus/skripte/requirements.txt"
__FENCE__

Za ponovno izdelavo vseh rezultatov iz STEP-a izvedi naslednji ukaz.

__FENCE__powershell
& 'trening/okolje/astra/venv-vozicek-312/Scripts/python.exe' -B -X utf8 'trening/modeli/vozicek-delovni-mali/astra/02/skripte/ponovi.py'
__FENCE__

__BT__priprava.py__BT__ določa pravila za pritrdilne točke, __BT__potek.py__BT__ korake in časovni potek, __BT__film.py__BT__ kamere in prereze. Za sledljivost preberi __BT__izvoz/pritrdilna_mesta.json__BT__, __BT__izvoz/vlozki.json__BT__ in __BT__izvoz/kontrola_cad.json__BT__. Kontrola primerjave s 01 uporablja njegovo inventuro samo za branje.

**Naslednji poskus.** Pridobiti je treba risbo plošče kolesa, kosovnico pritrdil in varilno risbo. Z njimi je mogoče potrditi izvedbo spojev in posamezen shematski element zamenjati z namenskim modelom. Za presojo uporabnosti naj monter na posnetku izbere ustrezen vijak in pokaže njegovo dejansko mesto.
""".replace("__BT__",chr(96)).replace("__FENCE__",chr(96)*3).replace("Ručni","Ročni")
    (OUT/"porocilo.md").write_text(report,encoding="utf-8")
    (OUT/"spoznanja.md").write_text("""# Predlogi za skupno znanje

- [CAD uvoz] Ta izvoz AP214 vsebuje material pri vseh 12 različnih listih. Sledenje od lastnosti »material name« do definicije izdelka in besedilnega podatka vrne Steel, Mild, Stainless Steel AISI 304, Iveral ali Generic. Barvni slog ploskve je ločen podatek.
- [Identifikacija delov] Pritrditev meri na pojav in njegovo lokalno os. Šestnajst mest na štirih enakih kolesih ima različna središča v koordinatah sestava.
- [Montaža] Preizkus obeh strani spoja je spremenil izid. Štiri reže na vsaki prirobnici so odprte, medtem ko tri sonde skozi nasprotno ploščo na vsaki od 16 osi zadenejo poln material.
- [Montaža] Šesterokotne odprtine v stebrih se ujemajo z osmimi odprtinami na nameščenih nosilcih. Vložek je možna izvedba. Šifro, tip in dimenzije lahko potrdi kosovnica.
- [Animacija] Za spodnjo polico sta odprtini Ø 12 in Ø 4,5 mm na isti osi v dveh stenah cevi. Prerez omogoča prikaz enega vijaka, ki gre skozi večjo odprtino do manjše.
- [Render / video] Na kolesu ima telo več barvnih območij. Delitev mreže po telesih in barvnih slogih omogoča ločen prikaz prirobnice in ohranitev prvotnega ID-ja izdelka.
- [Igrišče] Predlog za naslednje ocenjevanje je vrsta dokaza pri potrditvi spoja. Pri kolesu uporabnik potrjuje vijačenje, CAD določa os, za nasprotni navoj pa manjka risba. Te tri informacije potrebujejo ločena polja.
""",encoding="utf-8")
    save(OUT/"meta.json",dict(ai_model="gpt-6.2-astra",zacetek=started.isoformat(timespec="seconds"),konec=datetime.now().astimezone().isoformat(timespec="seconds"),
        status="uspeh",povzetek="12 prikazov v 75 s. Izvirnih 28 pojavitev in 92 teles. Štiri kolesa, 16 osi z nerazrešeno nasprotno ploščo ter 56 drugih mest za pregled.",
        orodja=tools,tezave=["Plošče okvirja so na 16 oseh koles polne.","72 vijakov in 8 vložkov so shematske ponazoritve brez kosovnice.",
        "Obseg varjenja, proizvodno zaporedje, momenti, tolerance in dostop orodja zahtevajo potrditev."]))

