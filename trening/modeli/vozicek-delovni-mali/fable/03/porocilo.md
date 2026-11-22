# Poročilo – voziček delovni mali, Fable, poskus 03

**Rezultat:** kamera pri vsakem spoju je zdaj izbrana z meritvijo vidnosti, ne po občutku. V vseh štirih trenutkih, ki ste jih označili (1:03, 1:21, 1:41, 2:00), se vijak zdaj vidi s strani, s katere se vstavi. Napisi so postavljeni tako, da ne prekrivajo gibanja ali spoja (izmerjeno: 0 px pri vseh 39 napisih). Glava in noga sta v slogu FINES in skupaj zasedata 124 px namesto 360 px. Video ima 13 korakov, 182,2 s, 1920x1080.

Geometrija, deli, spoji in zaporedje so enaki kot v poskusu 02 (`deli.json` in `spoji.json` sta bajtno enaka). **Zaporedje, način spajanja in vijačni material so še vedno predlog in zahtevajo potrditev tehnologa** – to zdaj piše v `koraki.json`, `spoji.json` in tukaj, ne več v videu.

## 1. Diagnoza ocene poskusa 02

Ocena fable/02: vse 5. Pripombe so bile štiri. Čase iz komentarja sem preslikal v korake z `fable/02/izvoz/video_casovnica.json`. Prebral sem tudi komentar pri astra/02 v `ocene.json` (ne mape drugega AI), ker opisuje ista pričakovanja glede sloga in lokacije detajla.

| Pripomba | Vzrok | Kaj sem spremenil |
|---|---|---|
| **[1:03] [1:21] [1:41] [2:00] ne vidi se, kam pridejo vijaki** (koraki 7, 9, 11, 13) | Detajl spoja je uporabil **isto smer kamere kot celoten korak** in se samo približal. Smer je bila izbrana za premik dela (od zgoraj spredaj), vijaki pa pridejo od spodaj ali z notranje strani. Skripta **ni nikjer preverila, ali se spoj sploh vidi**. | Nova „maskirna scena" (ID slika) izmeri, koliko pikslov vsakega vijaka kamera dejansko vidi. Za vsak spoj skripta preizkusi do 144 smeri in izbere najboljšo na strani dostopa, poševno na os vijaka. Pred detajlom je dodan pregled celega izdelka z obroči na vseh mestih vijakov. Ko je kamera pod izdelkom, je na sliki oznaka „POGLED OD SPODAJ". |
| **Glava in noga sta preveliki in nista v slogu FINES; operaterja ne zanimajo podatki o STEP in predpostavke** | Sloj z besedilom sem v 02 sestavil za ocenjevalca (sledljivost, poštenost), ne za operaterja. Standarda FINES (`FINES_Standardi/app_instructions.md`) nisem prebral. | Glava: bel trak 64 px z logom FINES, številko koraka, naslovom in načinom spajanja, pod njim oranžna črta 4 px (`#ca5010`). Noga: temno siv trak 56 px z enim stavkom navodila in trakom napredka. Pisava Inter (ista kot v aplikaciji). Odstranjeno: vir STEP, „vijačnega materiala ni v STEP", „predpostavka", opozorilo o potrditvi. |
| **Beli kvadratki prekrivajo gibanje in pomembne elemente** | Napis se je postavil „stran od središča prizora" glede na en trenutek. Postavitev ni vedela, kje bo del med premikom in kje so vijaki. | Napis se postavi z masko: unija ID slik gibajočih delov / vijakov / zvarov **čez celo fazo** + varnostni rob 14 px. Izbrano je mesto z najmanjšo ceno. Kontrola `izvoz/kontrola_napisov.json` zapiše prekrite piksle za vsak napis. |
| **V kvadratku so kode MTC… in P…; besedilo je čisto ob robu** | Kode sem v 02 pustil „drobno za sledljivost". Okvir besedila v VTK nima notranjega odmika, zato je besedilo ob robu. | V napisu sta samo ime in količina, pri vijakih še od kod se vstavi („od spodaj skozi cev"). Napisi so izrisani s PIL: zaobljen okvir, odmik 16 x 11 px, oranžna črta levo, senca. |

**Meritev potrjuje vzrok.** Vidnost vijaka v detajlu (delež vidnih pikslov; 1,00 = cel viden):

| Korak (čas v 02) | Pogled 02: izvlečen / na pol / privit | Pogled 03: izvlečen / na pol / privit |
|---|---|---|
| 7 Spodnja polica (1:03) | 1,00 / 0,12 / 0,00 | 1,00 / 0,92 / 0,00 → cev je med vijačenjem prosojna |
| 9 Vmesna polica (1:21) | 0,00 / 0,00 / 0,00 | 1,00 / 1,00 / 0,49 |
| 11 Zgornja polica (1:41) | 1,00 / 0,91 / 0,00 | 1,00 / 1,00 / 0,53 |
| 13 Montaža ročaja (2:00) | 0,78 / 0,45 / 0,00 | 1,00 / 1,00 / 0,78 |

„Pogled 02" je ponovno izmerjen v tej skripti (ista smer kot glavni pogled koraka, isti izrez). Ni izmerjen na videu poskusa 02; gruča vijakov je lahko druga, ker 03 za detajl vzame srednji vijak.

Pri privitem vijaku vrednost 1,00 ni dosegljiva, ker je steblo v materialu; vidna je samo glava (pri lesnem vijaku približno polovica površine).

**Dodatna napaka, ki sem jo našel sam:** v koraku 10 sta dve vrsti vijakov (2x M6 in 3x lesni vijak). Poskus 02 je pokazal detajl samo ene. Zdaj ima vsaka vrsta svoj detajl.

**Česa nisem odpravil:**
- Render je še vedno VTK, ne Blender (prenos je bil v poskusih 01 in 02 zavrnjen; tokrat nisem poskušal znova).
- Pregled mest vijakov v koraku 6 (kolesa) je pogled vzdolž vozička od spodaj. Poševni pogledi so imeli pod 75 % najboljše vidnosti, ker vijake zakrivajo kolesa.
- Lesni vijak 4 mm je v detajlu majhen (izrez je širok približno 300 mm, da ostane vidna okolica).

## 2. Kaj je v STEP

Nespremenjeno in ponovno izvedeno: 14 produktov, 29 pojavitev, 28 listnih delov, enote mm, imena, materiali in barve ohranjeni. 52 spojev (34 varjenih, 10 vijačnih, 8 „polica + vijaki"), 52 kosov vijačnega materiala generiranih iz lukenj (ni v STEP). Podrobnosti so v poročilu poskusa 02.

## 3. Odločitve

| Korak | Možnosti | Izbira in razlog |
|---|---|---|
| Uvoz, mreža, spoji, zaporedje | kot v 02 | Brez sprememb; ocenjeno s 5. |
| Kontrola vidnosti spoja | (a) ročno določen pogled za vsak korak; (b) žarki iz kamere do vijaka (ray casting); (c) **ID slika v drugi sceni VTK** | (c): meri dejansko vidno površino, ne samo ene točke, in uporablja isto geometrijo kot render. (a) ne deluje na naslednjem modelu. (b) bi zahteval dodatno knjižnico in vzorčenje površine. |
| Izbira smeri kamere | (a) vedno v osi vijaka; (b) **iskanje po 144 smereh z oceno** | (b). Ocena = izmerjena vidnost v treh legah vijaka × faktor za kot ~50° na os vijaka × faktor za zmerno elevacijo + manjši zasuk kamere. Pogled v osi (a) skrije gibanje vijaka. |
| Zakrit privit vijak | (a) prerez; (b) **prosojen zakrivajoči del**; (c) nič | (b): del, ki zakriva vijak, se najde iz ID slike. Prerez (a) v VTK zahteva rezanje mreže in zapiranje ploskev. |
| Lokacija detajla | (a) mala slika celote v kotu; (b) **pregled celote pred detajlom** | (b): brez dodatnega okna, ki bi spet zakrivalo sliko. Kamera gre zvezno iz pregleda v detajl. |
| Postavitev napisov | (a) hevristika kot v 02; (b) **maska + iskanje mesta z najmanjšo ceno** | (b), ker je preverljivo s številko. |
| Besedilo in glava | (a) besedilo VTK; (b) **PIL čez izrisano sliko** | (b): logo, Inter, zaobljeni okvirji, odmiki. Cena je približno 2x daljši render. |
| Ročni popravek | – | Če človek v korak vpiše `kamera.detajl_smer_rocno` (v `03_koraki.py`: `detajl_smer=[x, y, z]`), ima prednost pred iskanjem. |

## 4. Postopek

1. `01_analiza_in_izvoz.py`, `02_spoji.py`: kot v 02.
2. `03_koraki.py`: dodano polje `navodilo` (en stavek za operaterja, brez šifer); `opis` ostane za tehnologa.
3. `04_render.py`, za vsak korak:
   - prihod delov, napis z imenom in količino na mestu, ki ga premik ne prečka;
   - premik po preverjeni poti;
   - **varjenje:** detajl iz smeri z največjo izmerjeno vidnostjo stika, zvar zasveti po obodu;
   - **vijaki:** pregled celega izdelka s strani dostopa (obroči na vseh mestih), nato za vsako vrsto vijaka detajl srednjega vijaka; vsi vijaki te vrste se privijejo hkrati;
   - vrnitev v glavni pogled.
4. Izbrane kamere se zapišejo nazaj v `koraki.json` (`kamera.pregled_spojev`, `kamera.detajli`).

## 5. Samokontrola

**Preverjeno:**
- **Maskirna scena:** assert, da ID slika vsebuje samo znane ID-je (brez mešanja barv).
- **Vidnost:** 7831 maskirnih izrisov. Vseh 9 detajlov vijačenja ima vidnost izvlečenega vijaka ≥ 0,82 (prag opozorila 0,6); pod pragom ni nobenega. Vse meritve so v `izvoz/kontrola_vidnosti.json`.
- **Napisi:** 39 napisov, pri vseh prekrivanje pomembnega = 0 px, tudi z varnostnim robom. Največji delež napisa na ostali geometriji je 8,6 %.
- **Števila:** kot v 02 – 28 delov, 52 spojev in 52 vijakov, vsi dodeljeni natanko enemu koraku (assert).
- **Slike:** pregledal sem približno 30 od 49 kontrolnih sličic in 7 kadrov, izrezanih iz končnega videa (med njimi vsi štirje označeni trenutki). Po pregledu sem popravil: pregled v tlorisu (izdelek je bil videti kot stolp), detajl ob kolesu namesto na sredini, pregled od spodaj pri vodoravnih vijakih.
- **Video:** `ffprobe` pokaže h264 High, 1920x1080, 30 fps, 5466 sličic, 182,2 s.
- **Ponovljivost:** končni video je nastal z enim zagonom `zazeni_vse.sh` od STEP do MP4 (exit 0, približno 23 min). `deli.json` in `spoji.json` sta enaka kot v poskusu 02 (md5).

**Nepreverjeno:**
- Videa nisem pregledal v celoti. Prehodi kamere med pogledi niso preverjeni sličico za sličico; kontrola napisov velja za faze, ko kamera miruje.
- Celotnega postopka nisem zagnal dvakrat, zato enakost kamer med dvema polnima zagonoma ni potrjena.
- Vidnost zvarov je nizka po naravi (0,40–1,00): zvar teče po obodu stika in zadnja stran je vedno zakrita. Ali je prikaz zvara dovolj jasen, mora presoditi človek.
- Vse, kar je bilo nepreverjeno v 02 (vrstni red, vrsta vijakov, zakovične matice, pritrditev koles, GLB v three.js).

## 6. Kako ponoviti

Iz korena repozitorija v Git Bash:

```bash
bash trening/modeli/vozicek-delovni-mali/fable/03/skripte/00_okolje.sh     # enkrat (doda pillow in pisavo Inter)
bash trening/modeli/vozicek-delovni-mali/fable/03/skripte/zazeni_vse.sh    # ~23 min, od tega render ~22 min
```

Samo kontrolne sličice in obe kontroli brez videa (~2,5 min): `04_render.py --slicice`.

Popravki: navodila in zaporedje v `03_koraki.py` (`KORAKI`); pravila izbire kamere v `04_render.py` (`search_view`); slog v `build_chrome` in `make_box`.

## 7. Kaj je zanesljivo, kaj ne

- **Zanesljivo (izmerjeno):** vijak je v detajlu viden; napisi ne prekrivajo gibajočih delov, vijakov in zvarov v fazah z mirujočo kamero.
- **Odvisno od presoje:** uteži v oceni smeri (kot 50°, prag 75 % za pregled, omejitev elevacije 45°) sem nastavil na tem enem modelu po pregledu sličic. Na drugem modelu lahko dajo slabši pogled.
- **Slog FINES:** barve in logo so iz aplikacije (`globals.css`, `public/fines-logo.png`), postavitev glave in noge pa je moj predlog. Standard za video ne obstaja.
- **Tveganje, o katerem mora odločiti človek:** iz videa je na vašo zahtevo odstranjeno opozorilo, da je navodilo predlog. Video sam zdaj ne pove, da ni potrjen. Predlagam, da stanje (predlog / potrjeno) nosi aplikacija ob videu.
- Vse negotovosti glede spajanja in vijakov iz poskusa 02 ostajajo.

## 8. Naslednji poskus

1. **Potrditev sloga** glave, noge in napisov; po potrditvi pravila v `ZNANJE.md`.
2. **Preizkus na drugem modelu:** pravila za spoje (02) in za kamero (03) so razvita na enem samem.
3. **Prikaz orodja** (vijačnik, ključ, varilni gorilnik) in večji vijak v detajlu (tesnejši izrez ali povečava v krogu), ko bo znano orodje.
4. **Potrditev pravil spajanja** in kosovnica (kot v 02).
5. **Blender**, če ga človek namesti ali dovoli.
