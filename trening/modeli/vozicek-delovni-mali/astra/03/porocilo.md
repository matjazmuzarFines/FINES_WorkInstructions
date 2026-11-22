# Diagnoza pripomb k poskusoma 01 in 02

V 02 je razumljivost ostala pri 2/5. Uvoz, sledljivost, animacija, poštenost in ponovljivost so dobili po 4/5. Pregled prejšnjih skript in kontrolnih slik je pokazal, kje je programsko pravilen prikaz izgubil pomen za monterja.

| Pripomba | Vzrok | Popravek in kontrola v 03 |
|---|---|---|
| 02 • Glava, noga, stransko besedilo in podatki o številu teles odvračajo pozornost. Videz ni v slogu FINES. | Skripta je omejila 3D na pravokotnik znotraj strani velikosti 1920 × 1080. Na vsaki strani je ponovila spremne podatke. Znak FINES je bil izpisan s pisavo. | Model zavzema cel kader. Ob njem sta kratek naziv in po potrebi ena opomba o izvedbi. Pri detajlu majhen pregled označuje mesto na vozičku. Vir znaka je slika iz repozitorija `public/fines-logo.png`. |
| 02 • Vijačenje in varjenje sta težko prepoznavna. | Vijak se je premikal in vrtel brez orodja. Zvar je bil črta na sliki. | Pri dostopnem prikazanem mestu se nastavek približa glavi, jo spremlja med vrtenjem in se umakne. Gorilnik s šobo sledi izmerjenemu robu. Za konico ostane prostorska sled. Orodje, vijak in zvar prestanejo isti preizkus globine kot jeklo. |
| 02 • Obe zgornji sledi pri 02/12 sta videti skriti ali napačni. | Izbran je bil najdaljši rob vsakega para. Fiksni zorni kot ni upošteval drugih delov ogrodja. Projekcija črte je obšla zakrivanje. | Za vsak par primerjam robove preseka B-Rep iz 40 smeri. Izberem neprekinjen viden odsek z dovolj dolgo projekcijo. Pri stebru je odsek dolg 19,0 mm, pri vogalu 26,9 mm. Zapis točk in smeri je v `izvoz/pogledi.json`. To sta primera možne lege zvara, obseg določi varilna risba. |
| 02 • Oznake P… niso imena za operaterja. | Identifikator vozlišča se je izpisoval tudi v naslovu kadra. | Glavni posnetek uporablja nazive, kot so »Nosilca ročaja«, »Spodnja polica« in »Plošča kolesa«. ID-ji ostanejo v inventuri, GLB in časovno vezanih podatkih koraka. |
| 02 • Pri 04/12 kolesa niso vidna, že sestavljeni deli izginjajo. | Filter za prirobnico je zavrgel 16 od 17 teles kolesa. Vsak kader je gradil lasten seznam delov. | Stanje sestava se prenaša med koraki. Pri kolesu ostanejo tekalna površina, vilice, zavora in plošča. Kamera vključi kolo tudi med vijačenjem. Preverjanje primerja množice predhodno uvedenih delov in loči zadržane vijake. |
| 02 • Pri 07–10/12 je izgubljena lega na vozičku. | Prikaz se je začel neposredno pri nosilcu ali izvrtini. Lokalne ploščice so imele različne smeri. | Vsaka skupina začne s celoto in približanjem. Med delom kazalec na vedno enako obrnjenem vozičku pokaže pravo stran in višino. Zaporedna mesta na istem robu so razvrščena po koordinatah. |
| 01 • Groba geometrija in nejasen material. Uvoz 3/5. | Kolo je imelo en videz za več teles, materialne lastnosti izdelkov so bile spregledane. | Ponovljena sta uvoz XCAF z materialnimi lastnostmi in ločevanje mreže po telesih ter barvnih območjih. Preizkus ponovno prebere merilo, objekte in mejne mere GLB. |
| 01 • Premik kosa ne pojasni pritrjevanja, manjkajo ponovitve in pritrdila. Animacija 3/5, razumljivost in poštenost 2/5. | Poskus 01 je pokazal le eno kolo in polico do končne lege. Manjkalo je preverjanje obeh strani spoja. | Za vsako odprtino obstajajo par, os in vir sklepa. Kolesa imajo 16 mest. Za ročaj, povezavi in police je še 56 kandidatov. Predlagani vijaki in vložki imajo lasten izvor. Polna plošča ali ovira za orodje je razlog za zaustavitev prikaza. |

Za hiter pregled popravkov odpri 00:13 za oba zgornja stika, 00:28 za prvo kolo in 00:36 za prvo zadržano mesto. Pri 01:34 se začne pritrditev nosilcev ročaja, pri 02:19 pritrditev spodnje police in pri 02:45 pritrditev srednje police. Vsa poglavja so tudi v `izvoz/casovnica.json`.

## Kaj vsebuje STEP

Datoteka `MLU123069200 _1_.stp` je izvoz Inventorja 2027, AP214. Surovo besedilo ima 14 zapisov PRODUCT, 29 povezav NAUO in 28 definicij MANIFOLD_SOLID_BREP. XCAF v korenu razširi 28 pojavitev iz 12 različnih listnih izdelkov. Štiri kolesa imajo po 17 teles, preostalih 24 pojavitev po eno. Seštevek se ujema z 92 telesi korenskega sestava. Ročaj je poimenovan podsestav s tremi pojavitvami. Opisi, poti in prostornine so v `deli.json`.

STEPControl vrne milimetre. Mere sestava po izvornih oseh X × Y × Z so 1138,81 × 506,00 × 891,89 mm. Materialna lastnost je prisotna pri vseh 12 šifrah. Sedem jih nosi oznako Steel, Mild, dve Stainless Steel AISI 304, dve Iveral, kolo pa Generic. Videz površin kolesa, lesni dekor in sijaj so ilustrativni.

## Odločitve in postopek

| Korak | Možnosti in izbira |
|---|---|
| Uvoz | STEPControl lahko odpre obliko. STEPCAFControl z XCAF ohrani še pojavitve, njihove lege in barve. Podatke primerjam z izvornimi PRODUCT/NAUO ter z vezjo do materialne lastnosti. |
| Mreža | STL na telo bi zahteval ločeno tabelo imen, materialov in transformacij. Indeksirani GLB deli mreže ponovljenih izdelkov. Open CASCADE uporablja odstopanje 0,055 mm in kot 0,15 rad. Prazno ploskev ponovno tesselira na kopiji. Pretvorba v metre in osi (X, Z, −Y) je na izvozni meji. |
| Operacije | Hkratni premik vseh vijakov je hiter, vendar oteži sledenje posamezni luknji. Tukaj ima vsako od 72 mest svoje tri sekunde in kamero. Približanje, obrat in umik so časovno ločeni. Za osem zadržanih mest se pokažeta odprtina in ločen vzorec vijaka. |
| Render | 2D oznaka omogoča preprosto grafiko. Globinski izris v ModernGL omogoča preverjanje zakritosti na celotnem sestavu. Orodje in sled sta geometrija v istem prizoru. 2D obroč se uporablja samo kot kazalec izmerjene odprtine. MP4 ima poglavja za preskok na želeno opravilo. |

Skripta za kamero pri vijakih primerja poglede z osmimi globinskimi sondami. Pri spodnji polici šest lokalnih prerezov odpre pogled v cev. Prerez velja samo za izris. Ročaj je pri prikazu zvarov odmaknjen 110 mm od mesta namestitve. Vse prikazane poti in vrstni red so demonstracijski.

## Kaj omejuje proizvodno uporabo

Kolesa se po uporabnikovi oceni privijajo. Na vseh 16 oseh je zgornja nosilna plošča polna pri globinah 0,1, 1,5 in 2,9 mm. Pri osmih mestih ravni osni žarek od glave proti kolesu zadene njegovo telo že po 49,43–49,45 mm. Tudi del obodnih sond zadene prej. Posnetek ta mesta označi in pokaže vijak ob strani. Na drugih osmih se konica ustavi na plošči. Dejanski način zategovanja, dostop z drugim orodjem ali zasukom kolesa ter izvedba izvrtin zahtevajo pregled.

Osem šesterokotnih odprtin ustreza možnim vložkom pri ročaju in vmesnih povezavah. Oseminštirideset izvrtin v jeklu je usmerjenih v police. Ob končni legi ima zgornja polica z okvirjem štiri preseke po približno 5,31 ali 2,64 mm³. Pri odmiku 0,5 mm vsi štirje izračuni vrnejo nič. Število vijakov za naročilo, izbira nastavkov, momenti, varilni sloji, podpiranje, tolerance, sestava polizdelkov in zaporedje so **ni znano / zahteva potrditev**. Vidnost in osne sonde preverjajo prikaz. Celoten pometeni volumen orodja in vse poti sestavljanja ostajajo nepreverjeni.

## Samokontrola

- Isti STEP ima kontrolno vsoto SHA-256 `10d82de5a9a373bca00d874c5cfff4f3c21a6d607c9068c075d2a7a02ce092aa`. Vseh 28 poti in ID-jev se ujema s poskusom 02. CAD-mreža ima 1,080,096 trikotnikov. Največje odstopanje mej dela po ponovnem branju GLB znaša 0,021 mm.
- GLB ima tri scene. Prva vsebuje samo izvorni sestav, druga doda prikazane predloge, tretja omogoča pregled vseh kandidatov. Preizkus preveri članstvo vozlišč in tri časovne vzorce vsakega kanala v 13 animacijah. Gorilnik, nastavek, vidnost po fazah in kamere izdela filmska skripta.
- Kontrolni izris z vijakom in brez njega pokaže vsaj 1410 spremenjenih slikovnih pik za vsakega od 64 prikazanih vijakov. Kontrola vseh šestih sledi vrne najmanj 5022 spremenjenih pik. Primerjava vključuje senčenje. Osem zadržanih mest ima vsako preverjeno projekcijo odprtine.
- Predogled pusti vsaj 34,5 px roba okoli projektiranih gabaritov. FFmpeg je dekodiral 7625 sličic, H.264, 1280 × 720, 25 slik/s, 5 min 05 s. Pri 100 izbranih sličicah je najnižji PSNR 41,0 dB. `izvoz/kontrolni_kadri.jpg` vsebuje kadre iz končnega MP4. Razumljivost za monterja zahteva uporabniški preizkus.

## Kako ponoviti

PowerShell iz korena repozitorija, Windows x64, CPython 3.12, OpenGL 3.3, pisava Segoe UI Semibold in repozitorijski logotip FINES. Prvi ukaz za namestitev potrebuje dostop do PyPI. STEP in vse izpeljave se obdelajo lokalno.

```powershell
$poskus = 'trening/modeli/vozicek-delovni-mali/astra/03'
$python312 = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $python312 -B -m pip --isolated install --only-binary=:all: --no-cache-dir --no-compile --target "$poskus/.orodja" -r "$poskus/skripte/requirements.txt"
& $python312 -B -X utf8 "$poskus/skripte/ponovi.py"
```

`potek.py` določa dele in čase, `dostop.py` preveri prosti prostor na oseh koles, `kamera.py` izbere poglede, `film.py` izdela posnetek in poglavja. Podatki za pregled posameznega mesta so v `izvoz/pritrdilna_mesta.json`, `izvoz/pogledi.json` in `izvoz/dostop_koles.json`.

## Naslednji poskus

Konstruktor naj na risbi plošče kolesa pokaže izvedbo vseh štirih mest ene prirobnice. Monter naj na dejanskem kolesu pokaže dostop do obeh mest ob vilicah. S kosovnico pritrdil in varilno risbo bomo lahko shematske oblike zamenjali s potrjenimi ter nato na vozičku preverili, ali gledalec brez dodatne razlage prepozna mesto in izvede korak.
