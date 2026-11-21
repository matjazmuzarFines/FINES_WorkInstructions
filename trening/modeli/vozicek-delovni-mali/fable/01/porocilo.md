# Poročilo – voziček delovni mali, Fable, poskus 01

Prvi poskus, zato diagnoze prejšnjega poskusa ni.

**Rezultat:** iz STEP-a sem prebral pravi sestav s 14 produkti in 28 pojavitvami delov. Izdelani so inventura s stabilnimi ID-ji `P001`–`P028`, GLB z ločenimi deli in predlog 11 montažnih korakov. Za vsak korak sem pot vstavljanja preveril na trke z B-Rep geometrijo. Video ima 61,7 s, 1920x1080, H.264 in 30 fps. **Vrstni red montaže je predlog in zahteva potrditev tehnologa.**

## 1. Kaj je v STEP

Datoteka: `vhod/MLU123069200 _1_.stp` (4 MB, AP214 `AUTOMOTIVE_DESIGN`, ST-Developer, izvor **Autodesk Inventor 2027**, Fines d.o.o., 22. 10. 2026). Opis datoteke: *Voziček proizvodni montažni 1000x500 h=890*.

- **Struktura je pravi sestav z drevesom, ne združena geometrija:**
  - 14 entitet `PRODUCT`: koren `MLU123069200`, podsestav `MLU124029200` *Ročaj voziček l-434 zvarjenec* in 12 listnih produktov;
  - 29 entitet `NEXT_ASSEMBLY_USAGE_OCCURRENCE` (pojavitev): 26 v korenu in 3 v podsestavu ročaja;
  - 28 listnih pojavitev, iz katerih nastane 28 delov v `deli.json`.
- **Imena:** šifre (npr. `MTC324009902`) in opisi (npr. *Cev 30x30x1,5 l=993*) so ohranjeni v `PRODUCT`. Imena pojavitev imajo obliko `šifra:n` (npr. `MTC324009902:1`), kot v Inventorju. Kolo je kupljen del z imenom `kolo_fi80_z zavoro TENTE`.
- **Materiali in gostote** so v `PROPERTY_DEFINITION`. Med njimi so *Steel, Mild* 7,85; *Iveral* 0,72 (police); *Stainless Steel AISI 304* 8,0 (ročaj) in *Generic* 1,0 (kolo). Gostota kolesa (1,0) ni realna, zato je izračunana masa kolesa nezanesljiva.
- **Barve:** 1473 entitet `STYLED_ITEM` na ploskvah. Uporabil sem najpogostejšo barvo ploskev vsakega produkta.
- **Telesa:** v STEP je 28 entitet `MANIFOLD_SOLID_BREP`. Od tega ima 11 produktov po 1 telo, kolo pa 17 teles (11 + 17 = 28). Kolo ostane en del, ker je kupljen sestavni del.
- **Enote:** v STEP je `SI_UNIT(.MILLI.,.METRE.)`. Dimenzije se ujemajo z imeni: cev `l=993` meri v bbox 993,0 mm, `l=730` meri 730,0 mm, polica `993x493x18` meri 993x493x18. Višina sestava je 891,9 mm (opis pravi `h=890`; razlika je verjetno zaokrožitev kolesa).
- **Pritrdilnega materiala** (vijaki, matice) v STEP **ni**.

**Kako sem to preveril:** STEP sem prebral na dva neodvisna načina in rezultata primerjal.
1. Lasten razčlenjevalnik besedila STEP (ISO 10303-21) prešteje entitete in razbere `PRODUCT`, `NAUO` in materiale.
2. OpenCascade XCAF (`STEPCAFControl_Reader`) prebere drevo, lokacije in oblike.

Ujemanje je v `izvoz/struktura.json → kontrole`: 14 produktov, 29 NAUO, 28 listnih pojavitev, 28 delov v XCAF in 28 vozlišč v GLB. Tudi ID-ji v GLB se ujemajo z `deli.json` (`glb_id_ujemanje: true`).

## 2. Odločitve

| Korak | Možnosti | Izbira in razlog |
|---|---|---|
| Uvoz STEP | FreeCAD (ni nameščen, velik); CadQuery (ovoj nad OCP); **OCP / OpenCascade XCAF neposredno**; spletni pretvorniki (prepovedano) | **OCP XCAF**, ker neposredno da drevo sestava, imena (`TDataStd_Name`), lokacije pojavitev in barve. Je pip paket, ki deluje brez GUI in ga bo mogoče uporabiti tudi v strežniški cevovod. Python 3.15 nima izdaje `cadquery-ocp`, zato sem z `uv` namestil Python 3.12. |
| Mreža | `BRepMesh_IncrementalMesh` (OCCT); izvoz STL/glTF iz FreeCAD; `RWGltf_CafWriter` (OCCT) | **BRepMesh** z linearnim odklonom 0,1 mm in kotnim 0,3 rad. Mrežo naredim enkrat na produkt (v lokalnih koordinatah) in jo nato postavim z matriko pojavitve. Kakovost je izmerjena (glej samokontrolo). |
| Izvoz | glTF/GLB, OBJ, STL po delih | **GLB** (glTF 2.0) za kasnejši interaktivni 3D prikaz v aplikaciji (three.js). Vozlišče se imenuje po ID-ju, enote so m in os Y kaže gor (standard glTF), koren je `MLU123069200`. Za render je mreža shranjena še v `izvoz/mreze.npz` v mm s koordinatami STEP (Z gor). |
| Montažni koraki | ročno iz geometrije; avtomatski razstavni algoritem; LLM brez preverjanja | **Zaporedje kot predlog iz geometrije** (okvir → noge → police in povezave od spodaj navzgor → kolesa → ročaj). **Smer vstavljanja izberem samodejno:** za vsak korak preizkusim kandidatne smeri in izberem prvo, pri kateri premikajoči del na vsej poti (vzorec vsakih 5 mm) nima preseka B-Rep > 1 mm³ z že nameščenimi deli. |
| Animacija in render | Blender + Python (priporočeno v kontekstu); VTK offscreen; pyrender/three.js headless | **VTK 9.6 offscreen + ffmpeg (pipe, libx264).** Blenderja nisem mogel uporabiti: prenos portabilnega Blenderja 5.2.4 je zavrnil varnostni klasifikator orodja (Claude Code), tega pa nisem obhajal. VTK je že nameščen (odvisnost `cadquery-ocp`), je determinističen, hiter (~90 s za 1851 sličic) in ne potrebuje GUI. Slabost: ni senc in ne fotorealističnega renderja. |

## 3. Postopek

1. `01_analiza_in_izvoz.py`: surova analiza STEP, branje v XCAF (`xstep.cascade.unit = MM`), rekurzija po drevesu in sestavljanje matrik pojavitev. Za vsak del izračuna B-Rep bbox, volumen, težišče, material in barvo, nato tesselira in izvozi `deli.json`, `izvoz/vozicek.glb`, `izvoz/mreze.npz` in `izvoz/struktura.json`.
2. `02_koraki_in_trki.py`: statična kontrola prekrivanja vseh parov delov v končnem položaju, definicija korakov, izbira smeri brez trkov ter izvoz `koraki.json` in `izvoz/kontrole_trkov.json`.
3. `03_render.py`: VTK scena (en aktor na ID), animacija samo iz `koraki.json`. Sledi `predogled.png`, `video.mp4`, `izvoz/slicice/korak_XX.png` in `izvoz/video_casovnica.json`.
   - Video: uvod z obhodom kamere (4 s), nato 11 korakov po 4,7 s, nato končni sestav v barvah iz STEP (6 s).
   - Pri vsakem koraku: prehod kamere, pojav dela v izhodiščnem položaju (oranžen poudarek z oznako ID), premik v končni položaj, zadržanje in prehod v nevtralno sivo.
   - Že nameščeni deli so sivi, prihodnji so skriti (izolacija).
   - Na zaslonu so ves čas napis koraka, ID, ime in šifra delov ter opozorilo, da zaporedje ni potrjeno.

## 4. Samokontrola

**Preverjeno:**
- **Število delov:** STEP 28 listnih NAUO = XCAF 28 = GLB 28 vozlišč z istimi ID-ji. Vsak del je v natanko enem koraku (assert v skripti).
- **Enote in mere:** bbox delov se ujema z merami v imenih (glej razdelek 1). Celoten sestav meri 1138,8 x 506 x 891,9 mm. Pri dolžini so všteti ročaj in vrtljiva kolesa, okvir sam pa meri 996 x 501 mm. GLB po ponovnem branju meri 1,139 x 0,892 x 0,506 m, torej je pretvorba v m in Y-gor pravilna.
- **Kakovost mreže:** mrežni volumen (trimesh) sem primerjal z volumnom B-Rep (OCCT GProp). Odstopanje je od −0,004 % do −0,37 % (največje pri inox cevi fi30), pri policah 0 %. Brez mreže ni ostala nobena ploskev. Vsi produkti z enim telesom so vodotesni. Kolo (17 teles) ni vodotesno kot celota, kar je pričakovano.
- **Prekrivanje v končnem položaju:** 26 parov delov ima prekrit bbox, toda samo 6 parov ima presek > 1 mm³. To so police z L-povezavami: P017 s P009–P012 (2,6–5,3 mm³) ter P021 s P019/P020 (4,9 mm³). Prekrivanja so zanemarljiva (nekaj mm³ na 1 m dolžine). *Domneva:* gre za notranji radij L-profila proti ostremu robu police v CAD; to ni napaka izvoza.
- **Trki na poti:** vseh 11 korakov ima pot brez trkov. **Detektor sem preveril z negativnim testom:**
  - spodnja polica P018, ki pride od spodaj, ima 34 trkov z okvirjem (presek 36 147 mm³);
  - P018, ki pride od zgoraj, ko sta vmesni povezavi P019/P020 že nameščeni, ima 16 trkov.

  Detektor torej trke zazna. Vrstni red „spodnja polica pred vmesnimi povezavami" je zato geometrijsko nujen in ni naključen.
- **Sličice:** pregledal sem vse kontrolne sličice korakov (`izvoz/slicice/`). Pri tem sem našel in odpravil dve napaki:
  1. Pri pogledu od spodaj (koraka 3 in 10) so neprozorna tla zakrila dele, zato kamera ni kazala pravega dela. Vzrok: kamera je bila pod ravnino tal. Popravek: tla se skrijejo, ko je kamera pod njimi.
  2. Oznake ID so bile nad delom, zato so bile pri pogledu od spodaj skrite ali odrezane. Popravek: pri pogledu od spodaj so oznake pod delom in so vključene v kadriranje.
- **Video:** `ffprobe` pokaže h264 High, 1920x1080, 30 fps, yuv420p, 1851 sličic in 61,7 s.
- **Ponovljivost:** celoten poskus sem ponovno zagnal z `zazeni_vse.sh` (exit 0, ~2 min). Kontrolni vsoti (md5) `deli.json` in `koraki.json` sta enaki kot pred ponovitvijo (determinističen izhod). Video je bil ponovno ustvarjen z enakim številom sličic (1851); bajtne enakosti MP4 nisem preverjal.

**Nepreverjeno:**
- Ali je zaporedje tehnološko pravilno.
- Ali je okvir zvarjen ali vijačen. V STEP je samo ročaj označen kot „zvarjenec"; cevi in povezave so ločeni deli v korenu, kar *ne* pomeni nujno, da se vijačijo.
- Pritrditev koles in polic ter ali se voziček pri montaži obrne.
- Kateri del je „spredaj" (za poglede kamere sem dogovorno vzel stran −Y).
- Ali se GLB pravilno odpre v three.js ali Blenderju: preverjeno je samo ponovno branje s trimesh in pregled glTF JSON.

## 5. Kako ponoviti

Iz korena repozitorija v Git Bash (Windows):

```bash
bash trening/modeli/vozicek-delovni-mali/fable/01/skripte/00_okolje.sh     # enkrat: venv + Python 3.12 + OCP/VTK
bash trening/modeli/vozicek-delovni-mali/fable/01/skripte/zazeni_vse.sh    # ~2 min: vse izhode znova ustvari
```

`ffmpeg` mora biti v PATH.

Popravek korakov: uredi seznam `KORAKI` v `02_koraki_in_trki.py` (vrstni red, deli, kandidatne smeri, besedila) in ponovno zaženi `zazeni_vse.sh`. Za popravek samo časov ali kamere uredi `koraki.json` in zaženi le `03_render.py`.

## 6. Kaj je zanesljivo, kaj ne

- **Zanesljivo:**
  - drevo sestava, šifre, opisi, materiali, število in položaji delov (iz STEP, dvojno preverjeno);
  - mere v mm in sledljivost ID-jev med `deli.json`, `koraki.json`, GLB in videom.
- **Delno zanesljivo:**
  - Barve so ena barva na produkt (večinska), zato se izgubijo podrobnosti ploskev, npr. na kolesu.
  - V GLB je podsestav ročaja sploščen: P026–P028 so neposredno pod korenom, ne pod vozliščem `MLU124029200`. Pot iz drevesa je ohranjena v `deli.json → pot`.
  - V GLB so mreže ponovljenih produktov podvojene (28 mrež namesto 12), kar poveča velikost datoteke na 2,3 MB.
- **Nezanesljivo:**
  - Zaporedje montaže in delitev na polizdelke (verjetno je okvir varjen polizdelek in se ne sestavlja kos za kosom).
  - Masa kolesa (gostota *Generic* 1,0).
- **ID-ji** so iz vrstnega reda pojavitev v drevesu XCAF. To je stabilno za isto datoteko STEP, ne pa nujno po ponovnem izvozu iz Inventorja s spremenjenim sestavom. Zato je v `deli.json` za vsak del zapisana še `pojavitev` (`šifra:n`), ki je boljši trajni ključ.

## 7. Naslednji poskus

1. **Potrditev procesa od človeka:** ali je okvir (cevi, povezave, plošče koles) en zvarjen polizdelek, kako se pritrdijo police in kolesa, kaj je „spredaj". S temi podatki bi koraki postali npr. „1. zvarjenec okvirja, 2. kolesa, 3. police, 4. ročaj".
2. **Blender**, če človek dovoli prenos (prenos je bil v tem poskusu zavrnjen), za lepši render: sence, AO, materiali. VTK pot ostane kot hitra rezerva.
3. **GLB:** ohraniti hierarhijo podsestavov in deliti mreže med pojavitvami. Kot trajni ključ dodati `extras` z ID-jem, šifro in pojavitvijo. Preizkusiti tudi `RWGltf_CafWriter` iz OCCT.
4. **Kosovnica:** ko bo na voljo, jo povezati po `sifra` (ujemanje s šiframi MTC/MLU je neposredno možno).
5. **Kontrola trkov s pometanjem (sweep)** namesto vzorčenja vsakih 5 mm, ker bi tanki deli pri vzorčenju teoretično lahko „preskočili" oviro.
