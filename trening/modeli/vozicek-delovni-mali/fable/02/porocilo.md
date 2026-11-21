# Poročilo – voziček delovni mali, Fable, poskus 02

**Rezultat:** način spajanja je zdaj razbran iz geometrije STEP (luknje in stiki) in prikazan v vsakem koraku. Skripta je našla 52 spojev: 34 varjenih, 10 vijačnih in 8 „polica položena + privijačena". Vijačnega materiala v STEP ni, zato je 52 kosov generiranih kot predpostavka iz lukenj. Video ima 13 korakov, 129,7 s, 1920x1080. **Zaporedje, način spajanja in vijačni material so predlog in zahtevajo potrditev tehnologa.**

## 1. Diagnoza ocene poskusa 01

Ocena fable/01: uvoz 4, sledljivost 5, animacija 5, razumljivost 4, poštenost 4. Pripombe so bile tri. Prebral sem tudi komentar pri astra/01 v `ocene.json` (ne mape drugega AI), ker opisuje ista pričakovanja glede vijakov.

| Pripomba | Vzrok | Kaj sem spremenil |
|---|---|---|
| **Pri vsaki animaciji manjka način montaže** (kolesa se vijačijo, cevi/okvir/pločevina se varijo, plošča se položi) | V poskusu 01 sem iz STEP bral samo položaje in volumne delov. **Lukenj in stikov med deli nisem analiziral**, čeprav je podatek o spajanju prav tam. Način spajanja sem zato označil kot „ni znano". | Nova skripta `02_spoji.py` prebere vse luknje (krog, šestkotnik, utor) in stične ploskve ter po pravilih določi način spajanja (razdelek 3). Vsak korak ima značko VARJENJE / VIJAČENJE / POLAGANJE + VIJAČENJE in detajlni pogled spoja: zvar zasveti po obodu stika, vijaki se privijejo v prave luknje. |
| **Vijaki morajo biti prikazani, tudi če jih ni v modelu** (komentar pri astra/01; v fable/01 sem samo zapisal, da jih ni) | Manjkajoč podatek sem obravnaval kot konec poti, namesto da bi ga sklepal iz lukenj. | Vijačni material se generira parametrično na pravih mestih in v pravih smereh: 16x M8 (kolesa), 8x M6 + 8x šestkotna zakovična matica M6 (vmesni povezavi, ročaj), 20x lesni vijak 4 mm (police). Vsak kos ima v `spoji.json` dokaz (katera luknja, katera mera) in oznako „predpostavka". |
| **Kakovost komponent** (predpostaviti les, železo, pločevino, vijačni material in izboljšati videz) | Trije vzroki: (1) ena barva na del in preprosto senčenje brez materialov, (2) groba mreža (0,1 mm / 0,3 rad), (3) barve iz STEP za prikaz niso primerne (police skoraj črne, kolo v celoti modro). | Razred materiala se določi iz dveh neodvisnih virov (ime v STEP in geometrija) in preslika v PBR material: kovina z odsevi okolja, tekstura lesa, pocinkan vijačni material. Dodano: okoljska osvetlitev, SSAO, robovi, mehka senca, barve kolesa po ploskvah, 3x finejša mreža, nadvzorčenje 1,5x. |
| **Oznake P… niso jasne** (monter si mora zapomniti številko in gledati v kot) | Oznaka ob delu je nosila samo ID, ime je bilo ločeno v kotu zaslona. | Ob delu je zdaj napis z **imenom in količino** (npr. „4x Kolo fi80 gibljivo z zavoro") in vodilno črto do vsakega kosa. Šifra in ID sta drobno v drugi vrstici samo za sledljivost. Navodilo koraka je stavek na dnu zaslona. |

**Česa nisem mogel odpraviti:** render je še vedno VTK, ne Blender. Prenos Blenderja je bil zavrnjen že v poskusu 01; tokrat sem poskusil `pip install bpy` in varnostni klasifikator Claude Code je zavrnil tudi to. Tretjič nisem poskušal. Kakovost sem zato izboljšal znotraj VTK. Za fotorealističen render (prave sence, globalna osvetlitev) je potreben Blender, ki ga mora namestiti ali dovoliti človek.

## 2. Kaj je v STEP

Struktura je enaka kot v poskusu 01 in je ponovno preverjena: 14 produktov, 29 pojavitev, 28 listnih delov, enote mm, imena, materiali in barve ohranjeni.

Nove ugotovitve iz analize lukenj in stikov:

- **Noge** (MTC324010102) imajo po 22 **šestkotnih lukenj z zevom 9,1 mm** (88 na vseh štirih nogah). To je standardni izrez za šestkotno zakovično matico M6. Uporabljenih je 8 lukenj, ostalih 80 je prostih (*domneva:* nastavitev višine police).
- **Vmesni povezavi** (MTC324011201) sta Z-profil 3 mm z utorom 6,5x12 na vsakem koncu. Utori so soosni s šestkotnimi luknjami nog, reža je 0,5 mm (ravno za prirobnico zakovične matice).
- **Nosilca ročaja** imata po dve luknji Ø6,4, soosni s šestkotnimi luknjami nog. V CAD je ročaj nesimetričen: reža do noge je 0,6 mm na eni in 1,4 mm na drugi strani.
- **Spodnji vzdolžni cevi** imata po 3 pare lukenj: Ø12 v spodnji steni (dostop) in Ø4,5 v zgornji (prehod). Vijak gre torej od spodaj skozi cev v polico.
- **Povezave** imajo luknje Ø5 v vodoravnem kraku pod polico (vijaki od spodaj v les).
- **Kolo** ima v pritrdilni plošči 4 utore 9,2x10,7 mm (razmik 78,5 x 60 mm), kar ustreza M8. **Plošča kolesa P013–P016 nima modeliranih lukenj.**
- **Neuporabljene luknje**, katerih namen ni znan: Ø4 v navpičnem robu povezav (28 kosov) in šestkotne z zevom 7,1 mm v zgornjih povezavah 1000 (10 kosov; mera ustreza zakovični matici M5).
- Med cevmi okvirja, nogami, ploščami koles in zgornjimi povezavami **ni nobenega para soosnih lukenj**, ravnih stičnih ploskev pa je 32. To se ujema z vašo pripombo, da se varijo.

## 3. Odločitve

| Korak | Možnosti | Izbira in razlog |
|---|---|---|
| Uvoz, mreža | kot v 01 (OCP / OpenCascade XCAF) | Ista pot, ker je bila ocenjena dobro. Mreža je finejša: 0,03 mm / 0,12 rad (prej 0,1 / 0,3). |
| Zaznava lukenj | (a) valjaste ploskve; (b) **notranje zanke na ravnih ploskvah** | (b), ker zajame tudi šestkotne luknje in utore, ki niso valji. Prav šestkotne luknje so tu ključne. |
| Način spajanja | (a) ugibanje iz imen; (b) LLM presoja slike; (c) **pravila nad geometrijo + pripombe človeka** | (c), ker je ponovljivo in ima vsak spoj zapisan dokaz. Pravila: soosni luknji dveh delov → vijačni spoj; šestkotni izrez 9,1 → zakovična matica M6; luknja s polnim lesom za njo → lesni vijak; kupljeno kolo s pritrdilnimi utori → vijaki (vaše pravilo „kolesa se vedno vijačijo"); stik jeklo–jeklo brez vijakov → varjenje; les na jeklu → polaganje. |
| Linija zvara | (a) ročno; (b) **obod stične ploskve** (presek soležnih ravnih ploskev); (c) presek teles | (b), z (c) kot rezervo. Obod pove, **kje** se dela stikata. Ne pove vrste, debeline in dolžine zvara. |
| Vijačni material | (a) samo besedilo; (b) knjižnica standardnih delov; (c) **parametrična poenostavljena geometrija** | (c): glava, steblo in podložka brez navoja, mere po ISO iz premera luknje. Knjižnica (b) bi bila boljša, ko bo znana kosovnica. |
| Material za prikaz | (a) barva iz STEP; (b) **razred iz imena v STEP + neodvisno iz geometrije** | (b), ker ste opozorili, da material v STEP ne bo vedno zapisan. Geometrijska ocena (poln kvader 18 mm → les; ekvivalentna debelina stene ≤ 4 mm → jeklo; več teles → kupljen del) se z imenom v STEP ujema pri 11 od 12 produktov. Inoxa od jekla se iz oblike ne da ločiti. |
| Render | Blender (zavrnjen dvakrat); **VTK s PBR** | VTK: PBR materiali, okoljska osvetlitev, SSAO, robovi, tekstura lesa, nadvzorčenje 1,5x. |
| Zaporedje | kot v 01 (kos za kosom); **po sklopih** | Po sklopih, kot izhaja iz spojev: A. zvarjenec okvirja (16 delov, samo varjenje), B. končna montaža (vijačenje, polaganje), C. podsestav ročaja (v STEP označen kot zvarjenec). |

## 4. Postopek

1. `01_analiza_in_izvoz.py`: STEP → `deli.json`, mreže, GLB; razred materiala; barve po ploskvah.
2. `02_spoji.py`: luknje, stiki, pravila → `spoji.json`. Generira vijačni material (`izvoz/vijaki.npz`), ga doda v `deli.json` kot V01–V09 in v GLB kot 52 vozlišč.
3. `03_koraki.py`: 13 korakov. Spoji in vijaki se korakom dodelijo samodejno: spoj pripada koraku, v katerem je nameščen drugi od obeh delov. Pot vsakega dela je preverjena na trke.
4. `04_render.py`: video, predogled in kontrolne sličice. Vsak korak ima štiri faze:
   - prihod delov z napisi (ime, količina);
   - premik po preverjeni poti;
   - detajlni pogled spoja (zvar zasveti po obodu stika, vijaki se privijejo, zakovične matice se vstavijo);
   - prehod v pravi material.

Koraki: 1 spodnji okvir, 2 plošče koles, 3 noge, 4 zgornje povezave (vse varjenje), 5 zakovične matice M6, 6 kolesa (16x M8), 7 spodnja polica (6 vijakov skozi cevi), 8 zadnja vmesna povezava (2x M6), 9 vmesna polica (3 vijaki), 10 sprednja vmesna povezava (2x M6 + 3 vijaki), 11 zgornja polica (8 vijakov), 12 zvarjenec ročaja, 13 montaža ročaja (4x M6).

## 5. Samokontrola

**Preverjeno:**
- **Števila:** 28 delov iz STEP = 28 vozlišč P v GLB; 52 kosov vijačnega materiala = 52 vozlišč V v GLB. Vsi spoji (52/52) in vsi vijaki (52/52) so dodeljeni natanko enemu koraku (assert v skripti). Vsi deli končajo v končnem položaju (assert).
- **Mreža:** volumen mreže odstopa od B-Rep za največ 0,06 % (prej 0,37 %). Ena ploskev kolesa pri finejši mreži ni dobila trikotnikov (1 od ~1450); na sliki tega nisem opazil.
- **Zaznava spojev – napake, ki sem jih našel in odpravil:**
  1. Kolo je bilo razvrščeno kot les, ker niz „več teles" vsebuje „les". Posledica je bil napačen tip spoja.
  2. Nosilca ročaja nista bila zaznana. Najprej sem napačno sklepal, da sta osi zamaknjeni. Preverjanje je pokazalo, da sta osi poravnani in da je bil vzrok prag bližine delov (reža 0,6 mm in 1,4 mm). Popravil sem prag, ne tolerance osi.
  3. Dostopne luknje Ø12 so bile med neuporabljenimi.
- **Trki:** vseh 12 korakov s premikom ima pot brez trkov. Detektor je zavrnil vmesno polico od zgoraj (16 trkov), ker so zgornje povezave v tem zaporedju že privarjene, in izbral vstavljanje s sprednje strani. Zaporedje „zadnja povezava → polica → sprednja povezava" je torej geometrijsko izvedljivo.
- **Sličice:** pregledal sem kontrolne sličice vseh faz (`izvoz/slicice/`) in kadre iz videa. Našel in odpravil sem: pasove na tleh (SSAO na veliki ravnini; zdaj je samo mehka senca), premajhen sestav v kadru, premalo približan detajl spoja, prekrivanje napisov z geometrijo in predolgo vrstico opisa.
- **Video:** `ffprobe` pokaže h264 High, 1920x1080, 30 fps, 3891 sličic, 129,7 s.
- **Ponovljivost:** celoten poskus sem ponovno zagnal z `zazeni_vse.sh` (exit 0, ~10 min, video spet 3891 sličic). `deli.json` in `koraki.json` sta bila enaka (md5), `spoji.json` pa ne. Vzrok je bilo polje s časom izvajanja; odstranil sem ga in z dvema zaporednima zagonoma `02_spoji.py` potrdil, da je datoteka zdaj enaka. Po tem popravku sem ponovno zagnal samo skripti 02 in 03 (video se ni spremenil, ker se vsebina spojev ni spremenila). Bajtne enakosti MP4 nisem preverjal.

**Nepreverjeno:**
- Ali je vrstni red tehnološko pravilen in ali se zvarjenec pred montažo barva.
- Vrsta in mera vijakov, ali so v nogah res zakovične matice, in kako so kolesa pritrjena v ploščo brez lukenj (navoj, matica).
- Ali se GLB pravilno odpre v three.js (preverjena sta samo zgradba datoteke in ponovno branje s trimesh).

## 6. Kako ponoviti

Iz korena repozitorija v Git Bash:

```bash
bash trening/modeli/vozicek-delovni-mali/fable/02/skripte/00_okolje.sh     # enkrat (isto okolje kot poskus 01)
bash trening/modeli/vozicek-delovni-mali/fable/02/skripte/zazeni_vse.sh    # ~10 min, od tega render ~9 min
```

Samo kontrolne sličice brez videa (~40 s): `04_render.py --slicice`.

Popravki: zaporedje in poti so v seznamu `KORAKI` v `03_koraki.py`; pravila spajanja in mere vijakov so v `02_spoji.py`.

## 7. Kaj je zanesljivo, kaj ne

- **Zanesljivo** (izmerjeno v STEP): položaji, oblike in mere lukenj, soosnost, stične ploskve, poti brez trkov.
- **Utemeljena predpostavka:**
  - Varjenje okvirja: ni lukenj, obstajajo stične ploskve, potrjuje vaša pripomba.
  - Vijačenje koles: utori v plošči kolesa in vaše pravilo.
  - Zakovične matice M6: šestkotni izrez 9,1 mm in prehodna luknja 6,4–6,5 mm kažeta isto mero.
- **Šibka predpostavka:**
  - Lesni vijak 4 mm (iz lukenj Ø4,5 in Ø5; dolžina neznana) ter oblika glave in podložke pri vseh vijakih.
  - Linija zvara je obod stika, ne dejanski zvar.
  - Videz lesa: STEP pravi material „Iveral" in skoraj črno barvo, ime dela pa „polica lesena". Prikazal sem lesni dekor; pravi dekor ni znan.
  - Modro barvo kolesa iz STEP sem prikazal kot pocinkano jeklo.
- **Ni znano:** momenti, orodje, vrsta zvarov, površinska zaščita, namen prostih lukenj.

## 8. Naslednji poskus

1. **Potrditev pravil spajanja** od človeka, da gredo v `ZNANJE.md`: šestkotna luknja 9,1 → zakovična matica M6; kateri vijak za police; kako so pritrjena kolesa.
2. **Blender**, če ga človek namesti ali dovoli (za sence in fotorealizem).
3. **Knjižnica standardnega vijačnega materiala** (ISO geometrija z navojem) namesto poenostavljenih valjev; prikaz orodja (ključ, vijačnik, klešče za zakovične matice), ko bo znano.
4. **Kosovnica:** vijačni material iz `spoji.json` primerjati s kosovnico (količine po merah) kot kontrolo zaznave.
5. **Preizkus pravil na drugem modelu**, ker so bila razvita na enem samem.
