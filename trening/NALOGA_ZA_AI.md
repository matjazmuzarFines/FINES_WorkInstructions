# Naloga za AI: 3D video navodilo za montažo iz STEP modela

To nalogo hkrati dobita dva AI-ja (GPT-6.2 Astra v Codexu in Claude Fable 5.2 v Claude Code), vsak v svojem chatu. Rezultata se primerjata drug ob drugem v aplikaciji (Admin → AI trening), zato **mora vsak poskus upoštevati spodnji format izhoda**.

Zagonski prompt ti pove tri stvari:
- **AI**: `astra` ali `fable` (to si ti),
- **Model**: mapa `trening/modeli/<model>/`,
- **Poskus**: številka, npr. `01`.

Pred začetkom preberi:
1. `trening/ZNANJE.md` - potrjena spoznanja in pravila iz prejšnjih poskusov (obeh AI-jev). Ta pravila veljajo in imajo prednost pred predlogi v tej nalogi.
2. `data/AI_proizvodna_video_navodila_zacetni_kontekst.txt` - ozadje projekta.
3. `trening/modeli/<model>/model.json` - opis modela.

---

## 0. To je training ground: razmišljaj, ne samo generiraj

Cilj ni en lep video, ampak **postopek, ki zanesljivo deluje na pravih CAD podatkih**. Od tebe se pričakuje, da razmišljaš kot inženir, ki mora problem rešiti, ne kot generator, ki poskuša znova:

- **Najprej razumi podatke in orodja**, šele nato izbiraj pristop. Primer: STEP ne vsebuje trikotnikov, ampak natančno B-Rep geometrijo. Za prikaz jo moraš z CAD jedrom (npr. OpenCascade) tesselirati, kakovost mreže pa je odvisna od nastavitev. Takšna dejstva preveri in zapiši.
- **Utemelji izbiro.** Za vsak ključni korak (uvoz STEP, pretvorba v mrežo, animacija, render) navedi vsaj dve možnosti, kaj si izbral in zakaj. Upoštevaj zanesljivost, ponovljivost, kakovost, hitrost in kasnejšo uporabo v aplikaciji (npr. interaktivni 3D prikaz).
- **Preverjaj rezultat sam.** Preden razglasiš uspeh, preglej svoj izhod: ali število delov ustreza STEP-u, ali so enote mm, ali se deli v videu prekrivajo, ali kamera kaže pravi del. Uporabi kontrolne izračune in sličice. Kar ni preverjeno, napiši kot nepreverjeno.
- **Ob slabi oceni poišči vzrok.** Ko komentar v `ocene.json` pove, da nekaj ni dobro, ne generiraj samo znova z drugačnimi parametri. Ugotovi vzrok (podatki, orodje, pristop, tvoja napačna predpostavka) in poišči boljšo rešitev: drugo knjižnico, dodatno orodje, drugačen postopek, kontrolo kakovosti. Če vzroka ne moreš odpraviti, napiši, kaj bi bilo potrebno (podatek, orodje, odločitev človeka).
- **Predlagaj izboljšave igrišča.** Če naloga, format izhoda ali vhodni podatki ovirajo dober rezultat, to napiši v `spoznanja.md`, ne obidi tiho.
- **Spoznanja zapiši za naslednjič.** Kar si se naučil (kaj deluje, kaj ne, pasti), predlagaj v `spoznanja.md`. Človek potrjena spoznanja prenese v `trening/ZNANJE.md`, ki ga bereta oba AI-ja.

---

## 1. Pravila igrišča (obvezno)

1. **Pišeš samo v svojo mapo poskusa:** `trening/modeli/<model>/<ai>/<poskus>/`.
   - Ne spreminjaj `vhod/`, `model.json`, `ocene.json`, `trening/ZNANJE.md` (predloge daj v svoj `spoznanja.md`), mape drugega AI-ja ali kode aplikacije (`src/`, `supabase/`, `package.json` ...).
   - Orodja in virtualna okolja (Python venv, prenesen Blender ...) daj v `trening/okolje/<ai>/`. Ta mapa ni v gitu in jo lahko uporabiš v vseh svojih poskusih.
2. **Ne beri map drugega AI-ja.** Primerjava mora biti neodvisna. Svoje prejšnje poskuse (npr. `01`, ko delaš `02`) in ocene v `ocene.json` lahko bereš.
3. **Zaupnost:** STEP model in izpeljani podatki so interni konstrukcijski podatki. Ničesar ne pošiljaj zunanjim storitvam (spletni pretvorniki, API-ji, upload). Vse obdelaj lokalno. Prenos odprtokodnih orodij in paketov (pip, Blender, FreeCAD) je dovoljen.
4. **Poštenost:** ne trdi, da si nekaj analiziral ali izdelal, če nisi. Česar ne veš (vrstni red montaže, orodje, momenti, varnost), označi kot `ni znano / zahteva potrditev`. Ne prikrij težave z lepo animacijo.
5. **Ponovljivost:** vse, kar izdelaš, mora nastati iz skript v `skripte/`. Človek mora poskus ponoviti z ukazom iz `porocilo.md`.
6. **Brez plačljivih storitev** in brez dodatnih API ključev.

Okolje (preverjeno 21. 11. 2026): Windows 11, Python 3.15, ffmpeg 9.0, Node 24. **Blender in FreeCAD nista nameščena.** Preveri sam in po potrebi namesti v `trening/okolje/<ai>/`.

---

## 2. Kaj narediš (MVP)

Merilo uspeha ni tehnološko pravilen vrstni red montaže. Meri se, ali **zanesljivo uvoziš pravo 3D geometrijo, ohraniš sledljivost delov in izdelaš programsko krmiljeno animacijo, ki jo je mogoče ponoviti in popraviti.**

1. Preberi in analiziraj dejansko strukturo STEP datoteke v `vhod/` (sestav / telesa / združena geometrija). Ne izmišljaj si razčlenitve, ki je ni.
2. Izdelaj inventuro delov s stabilnimi ID-ji (`deli.json`).
3. Model izvozi v animacijsko okolje z ločenimi deli (npr. glTF/GLB). Pazi na enote (mm), koordinatni sistem in orientacijo.
4. Predlagaj montažne korake (`koraki.json`). Vsak korak se sklicuje na ID-je delov iz `deli.json`.
5. Izdelaj video `video.mp4`: vsaj en demonstracijski korak (izolacija dela, premik v / iz končnega položaja, poudarek dela, smiseln pogled kamere). Več korakov je bolje, če so pravilni.
6. Izdelaj predogled `predogled.png` (en kader celega sestava).
7. Napiši `porocilo.md`, `spoznanja.md` in `meta.json`.

Če v tem poskusu česa ne moreš izdelati (npr. videa), naredi, kar gre. Status v `meta.json` nastavi na `delno` ali `neuspeh` in v poročilu napiši, kaj manjka in zakaj.

---

## 3. Format izhoda (obvezno)

```
trening/modeli/<model>/<ai>/<poskus>/
  meta.json        obvezno - podatki o poskusu
  porocilo.md      obvezno - kaj si naredil, kako ponoviti, tveganja
  spoznanja.md     obvezno - predlogi za skupno znanje (ZNANJE.md)
  deli.json        inventura delov
  koraki.json      montažni koraki
  video.mp4        video navodilo (H.264, 1920x1080 ali 1280x720, 25-30 fps)
  predogled.png    kader celega sestava (16:9)
  skripte/         vse skripte, s katerimi je poskus nastal
  izvoz/           vmesne datoteke (glb, obj ...) - neobvezno
```

Aplikacija prikaže, kar obstaja. Datoteke z drugimi imeni vidi samo v zavihku Datoteke.

### meta.json

```json
{
  "ai_model": "claude-fable-5-2",
  "zacetek": "2026-11-21T20:15:00+01:00",
  "konec": "2026-11-21T21:02:00+01:00",
  "status": "uspeh",
  "povzetek": "STEP vsebuje sestav z 14 telesi; izvoz v GLB z ločenimi deli; video 3 korakov (42 s).",
  "orodja": ["Python 3.12", "cadquery 2.5", "Blender 4.4"],
  "tezave": [
    "Imena delov v STEP manjkajo - ID-ji so iz vrstnega reda teles.",
    "Vrstni red montaže ni znan - zahteva potrditev tehnologa."
  ]
}
```

- `status`: `uspeh` | `delno` | `neuspeh`.
- `zacetek` / `konec`: ISO čas z časovnim pasom. Iz njiju aplikacija izračuna čas izdelave.
- `ai_model`: točen model, ki je delal (npr. `gpt-6.2-astra-high`, `claude-fable-5-2`).

### deli.json

Seznam (ali objekt `{ "deli": [...] }`):

```json
[
  {
    "id": "P001",
    "ime": "Stranica leva",
    "tip": "solid",
    "stars": "SESTAV",
    "kolicina": 1,
    "bbox_mm": { "min": [0, 0, 0], "max": [600, 20, 850] },
    "volumen_mm3": 10200000,
    "opomba": "Ime iz STEP (PRODUCT)."
  }
]
```

- `id` je **stabilen**: isti del ima isti ID v GLB (ime objekta), v `koraki.json` in v videu (oznaka). Uporabi `P001`, `P002` ... ali ime iz STEP, če je enolično.
- `ime`: ime iz STEP, če obstaja. Sicer ga pusti prazno ali napiši opis z oznako `(predlog)`.
- `bbox_mm` v milimetrih, v koordinatah sestava.

### koraki.json

Seznam (ali objekt `{ "koraki": [...] }`):

```json
[
  {
    "st": 1,
    "naslov": "Namesti levo stranico na dno",
    "opis": "Stranico P001 postavi pravokotno na dno P003, robova poravnana.",
    "deli": ["P001"],
    "gibanje": { "tip": "premik", "od_mm": [0, -400, 0], "do_mm": [0, 0, 0], "trajanje_s": 3 },
    "kamera": { "pogled": "izometrija spredaj-levo" },
    "opozorila": ["Orodje in pritrdilni material nista znana."],
    "potrditev": "ni znano / zahteva potrditev"
  }
]
```

### porocilo.md

Kratko in konkretno, v slovenščini:

1. **Diagnoza** (samo od poskusa `02` naprej): kaj je bilo v prejšnjem poskusu ocenjeno slabo, kaj je bil **vzrok** in kaj si spremenil, da ga odpraviš. Ne samo "drugačni parametri".
2. **Kaj je v STEP**: struktura, število teles, imena, enote. Kako si to preveril.
3. **Odločitve**: za vsak ključni korak (uvoz, mreža, animacija, render) obravnavane možnosti, izbira in razlog.
4. **Postopek**: orodja, pretvorbe, nastavitve.
5. **Samokontrola**: kaj si preveril in kako (števila, sličice, izračuni). Kaj ostaja nepreverjeno.
6. **Kako ponoviti**: točni ukazi (od `trening/okolje/...` do `video.mp4`).
7. **Kaj je zanesljivo, kaj ni**: kje bi se lahko zmotil (izguba drevesa sestava, napačna identifikacija, STEP → mesh).
8. **Kaj bi naredil v naslednjem poskusu** in kaj bi za to potreboval (orodje, podatek, odločitev človeka).

### spoznanja.md

Predlogi za `trening/ZNANJE.md`. Vsak predlog je kratka alineja s kategorijo in dokazom:

```markdown
- [CAD uvoz] STEP iz Inventorja ohrani imena delov v PRODUCT entitetah - preverjeno na modelu omara-fbm (14/14 imen).
- [Animacija] ... 
- [Igrišče] Predlog: v model.json dodati polje "enote", ker ...
```

Kategorije: `CAD uvoz`, `Mreža`, `Identifikacija delov`, `Montaža`, `Animacija`, `Render / video`, `Orodja`, `Igrišče`. Piši samo, kar je preverjeno ali jasno označeno kot domneva. Ne ponavljaj, kar že piše v `ZNANJE.md`.

---

## 4. Naslednji poskusi

Ko dobiš nov poskus (`02`, `03` ...):

1. Preberi svoje prejšnje poskuse tega modela in oceno v `ocene.json` (ključ `<ai>/<poskus>`, ocene 1-5 in komentar).
2. Ponovno preberi `trening/ZNANJE.md`, ker je morda dopolnjen.
3. Za vsako slabo oceno ali pripombo ugotovi vzrok in poišči boljšo rešitev (glej razdelek 0). Če je pripomba nejasna, napiši, kako si jo razumel.
4. Diagnozo zapiši na začetek `porocilo.md`.

Nov poskus vedno zapiši v novo mapo, prejšnjih ne prepisuj.
