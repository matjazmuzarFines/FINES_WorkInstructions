// Zgodovina verzij - prikazana v "i" popupu (desni zgornji kot).
// Pravilo: male spremembe 1.01 -> 1.02, večje spremembe / nova funkcija / podstran -> 2.01.

export type ChangelogEntry = {
  verzija: string;
  datum: string;
  spremembe: string[];
};

export const CHANGELOG: ChangelogEntry[] = [
  {
    verzija: "5.05",
    datum: "22. 11. 2026",
    spremembe: [
      "AI trening: primerjava modela ima svoj naslov (/admin/trening/<model>) - gumb Nazaj v brskalniku in v aplikaciji vrne na Pregled treningov, povezavo do modela lahko deliš.",
      "Vrstica v Pregledu treningov je povezava (odpre se lahko tudi v novem zavihku); izbran poskus ostane, ko se vrneš na isti model.",
    ],
  },
  {
    verzija: "5.04",
    datum: "22. 11. 2026",
    spremembe: [
      "AI trening - Pregled treningov: v stolpcu Model je sličica sestava, izrisana iz STEP (izometrični pogled, barve iz CAD); klik odpre primerjavo.",
      "Primerjava: večja sličica modela; lokalno gumb Sličica iz STEP / Nova sličica izriše sličico znova.",
      "Sličica se izriše sama ob novem modelu in ob prenosu zahteve v trening; ob objavi gre na produkcijo.",
    ],
  },
  {
    verzija: "5.03",
    datum: "22. 11. 2026",
    spremembe: [
      "AI trening - Pregled treningov: stolpci so združeni v skupini Astra in Fable z logotipom ChatGPT / Claude, imenom AI-ja in orodjem; skupine ločuje navpična črta.",
      "Logotipa ChatGPT in Claude sta tudi v glavi panela poskusa in v tabeli Primerjava (namesto črk A / F).",
    ],
  },
  {
    verzija: "5.02",
    datum: "22. 11. 2026",
    spremembe: [
      "AI trening: zavihka Pregled in Primerjava sta povezana s kartico pod njima (po standardu); filtri so pod zavihki, skupno znanje je v zavihku Pregled.",
      "Pregled treningov po standardu tabel: razvrščanje po vseh stolpcih, filtri Iskanje in Ocena (Vsi / Ocenjeni / Neocenjeni), izvoz v Excel, številke desno, temna vrstica Skupaj.",
      "AI video creation - tabela zahtev: razvrščanje, filtri Iskanje, Status in Oddal, izvoz v Excel.",
      "Tabela delov poskusa ima razvrščanje in stolpec Kos; primerjava je v standardnem okvirju tabele.",
      "Usklajene standardne komponente s FINES_Production: glava tabel (navadne črke, ločila med stolpci, oranžna črta), filtri, izvoz in okna (gumbi v nogi okna, na telefonu cel zaslon).",
    ],
  },
  {
    verzija: "5.01",
    datum: "22. 11. 2026",
    spremembe: [
      "Meni Admin → Orodja se zdaj imenuje AI orodja.",
      "AI trening: nov zavihek Pregled (prva stran) - tabela vseh treningov s številom poskusov Astre in Fable, najboljšo oceno, časom generiranja in vrstico Skupaj; klik na model odpre primerjavo.",
      "AI trening na produkciji: gumb Objavi na produkcijo (samo lokalno) prenese poskuse, ocene, poročila, ZNANJE.md, videe in predoglede v Supabase; produkcija jih prikaže samo za branje (brez prompta in ocenjevanja).",
      "Nova stran AI orodja → AI video creation: razvojnik naloži STEP, kosovnico (Excel), slike in pojasnila; zahteva gre v vrsto.",
      "Značka v meniju pokaže število zahtev, ki čakajo na obdelavo. Lokalno gumb V trening prenese datoteke zahteve v nov model AI treninga; zahtevo lahko označiš kot končano ali zavrneš z razlogom.",
      "Poraba API kreditov: vrstica porabe mesečnih kreditov (privzeto 100 $), obnova in število žetonov; generiranje prek API je pripravljeno, a še izklopljeno.",
    ],
  },
  {
    verzija: "4.03",
    datum: "21. 11. 2026",
    spremembe: [
      "AI trening: gumb Oceni ob videu odpre velik video z obrazcem za oceno v istem oknu (na širokem zaslonu drug ob drugem, sicer video zgoraj in ostane viden med pisanjem).",
      "Video v oknu nadaljuje, kjer je bil ustavljen; gumb Vstavi čas doda trenutni čas videa (npr. [1:23]) v komentar.",
      "Ob zapiranju okna z neshranjeno oceno aplikacija vpraša za potrditev.",
    ],
  },
  {
    verzija: "4.02",
    datum: "21. 11. 2026",
    spremembe: [
      "AI trening: AI mora kritično razmišljati - utemeljiti izbiro orodij, sam preveriti rezultat, ob slabi oceni poiskati vzrok in boljšo rešitev (ne samo ponovno generirati).",
      "Skupno znanje trening/ZNANJE.md (pravila in spoznanja, bereta ga oba AI-ja) - prikazano na vrhu strani.",
      "Nov zavihek Spoznanja: predlogi AI-ja za skupno znanje (spoznanja.md v poskusu).",
      "Prompt za poskus 02 in naprej zahteva diagnozo prejšnjega poskusa na začetku poročila.",
    ],
  },
  {
    verzija: "4.01",
    datum: "21. 11. 2026",
    spremembe: [
      "Nova stran Admin → Orodja → AI trening: training ground za AI-generirana 3D video navodila iz STEP modelov.",
      "Isti model obdelata GPT-6.2 Astra (Codex) in Claude Fable 5.2 (Claude Code) v VS Code; stran pokaže oba poskusa drug ob drugem (video, predogled, poročilo, koraki, deli, datoteke).",
      "Gumb Predvajaj oba zažene oba videa hkrati; primerjalna tabela pokaže število delov, korakov, dolžino videa, čas izdelave in ocene (boljša zeleno).",
      "Ocenjevanje poskusov po 6 kriterijih (1-5) s komentarjem; ocene se shranijo v trening/modeli/<model>/ocene.json.",
      "Nov model: naziv, opis in STEP datoteke - aplikacija ustvari mapo trening/modeli/<id>/. Gumb Prompt kopira zagonski prompt za naslednji poskus.",
      "Podatki ostanejo samo na tem računalniku: stran deluje le na lokalnem strežniku, z admin prijavo; na Vercelu je izklopljena.",
    ],
  },
  {
    verzija: "3.02",
    datum: "16. 10. 2026",
    spremembe: [
      "Navodila: oznaka podsekcije je ozek oranžen navpičen trak z obrnjenim napisom ob levem robu kartic (čez celo višino podsekcije).",
      "Na telefonu je podsekcija naslov z oranžno črto (kot razdelki v meniju).",
    ],
  },
  {
    verzija: "3.01",
    datum: "16. 10. 2026",
    spremembe: [
      "Po skeniranju se odpre stran Navodila (/proizvodnja/navodila): na vrhu skeniran nalog / ident, spodaj navodila po sekcijah. Eno samo navodilo se odpre takoj.",
      "Navodila so razvrščena po sekcijah (temen naslov, vizualno ločene) in podsekcijah (oznaka razdelka levo, kartice desno); hitri skok na sekcijo na vrhu.",
      "Nova funkcija: končna slika proizvoda - v Programih desno od priprave delovnega mesta (naloži, zamenjaj, uredi v slikarju, izbriši).",
      "Končna slika je prikazana na karticah navodil in v glavi navodila (klik jo poveča).",
      "Baza: stolpec wi_programi.koncna_slika (migracija 003_koncna_slika.sql).",
    ],
  },
  {
    verzija: "2.04",
    datum: "16. 10. 2026",
    spremembe: [
      "Povezave: tabela povezanih identov ima stolpca Klasifikat in Status ter razvrščanje po vseh stolpcih.",
      "Povezave: nad tabelo enaki filtri kot v oknu Dodaj povezavo (iskanje, ident, naziv, klasifikat, status); privzeto so prikazane vse povezave.",
    ],
  },
  {
    verzija: "2.03",
    datum: "16. 10. 2026",
    spremembe: [
      "Delno iskanje besedila v vseh iskalnih poljih: vpisane besede se iščejo v poljubnem vrstnem redu in kjerkoli v nazivu (\"fbm cl\" najde \"Peč konvekcijska FBM-40S CL\").",
      "Iskanje ne loči velikih črk in šumnikov (\"pec\" najde \"Peč\").",
    ],
  },
  {
    verzija: "2.02",
    datum: "16. 10. 2026",
    spremembe: [
      "Povezave: desno ostane samo tabela povezanih identov z gumbom \"Dodaj povezavo\".",
      "Novo okno Dodaj povezavo: tabela šifranta (checkbox, ident, naziv, klasifikat, status) z razvrščanjem in filtri za vse stolpce.",
      "Privzeto so prikazani klasifikati 096-111 brez statusov NEAKTIVEN in IZLOČEN; filtre lahko spremeniš ali ponastaviš.",
      "Že povezani identi so pokljukani; odkljukan ident se ob shranjevanju odstrani. Pokljukaj vse prikazane z enim klikom v glavi tabele.",
    ],
  },
  {
    verzija: "2.01",
    datum: "16. 10. 2026",
    spremembe: [
      "Nova funkcija: Priprava delovnega mesta - na vrhu programa seznam (alineje) dodatne opreme in materiala, ki ga delavec pripravi pred delom.",
      "Postavke se dodajo z Enter; prilepljen seznam z več vrsticami doda več postavk naenkrat. Vrstni red se spremeni s povleci in spusti.",
      "Priprava se kopira pri \"Kopiraj iz obstoječega\" in je prikazana na vrhu navodila za delavca.",
      "Baza: nova tabela wi_priprava (migracija 002_priprava.sql) - pripravljena tudi za kasnejša orodja.",
    ],
  },
  {
    verzija: "1.04",
    datum: "16. 10. 2026",
    spremembe: [
      "Slikar: lepša puščica - črta se konča v konici in ne gleda več čez njo; konica je večja pri debelejših črtah.",
      "Slikar: dodana 4. debelina črte (zelo debela, 25 % debelejša od debele).",
      "Koraki: vrstni red slik se spremeni s povleci in spusti; vsaka slika ima oznako zaporedne številke.",
    ],
  },
  {
    verzija: "1.03",
    datum: "16. 10. 2026",
    spremembe: [
      "Izbirni seznami sekcij in podsekcij so razvrščeni po abecedi: najprej sekcije, znotraj sekcije podsekcije.",
      "Programi: vrstica za shranjevanje korakov ostane v širini desnega dela in ne prekriva več seznama programov (enako v Nastavitvah).",
    ],
  },
  {
    verzija: "1.02",
    datum: "16. 10. 2026",
    spremembe: [
      "Prijava z admin uporabnikom (admin@fines.si) takoj odklene admin dostop in meni - dodatna admin prijava ni več potrebna.",
      "Prenovljena domača stran za skeniranje: večje polje s čitalnikom, stanje pripravljenosti, jasnejša obvestila in izbira navodila.",
      "Skeniranje deluje tudi, ko polje ni izbrano (znaki čitalnika gredo samodejno v polje).",
    ],
  },
  {
    verzija: "1.01",
    datum: "16. 10. 2026",
    spremembe: [
      "Prva verzija aplikacije Fines - Work Instructions (ista prijava in baza kot Fines - Production).",
      "Domača stran: skeniranje delovnega naloga ali identa - navodila se odprejo samodejno, pri več navodilih izbira v mreži.",
      "Admin dostop (ikona ščita desno zgoraj): ločena prijava admina, nato se pokaže meni Proizvodnja / Admin.",
      "Programi: seznam s filtri, dodaj / uredi / odstrani, kopiraj iz obstoječega programa (s koraki in slikami), družine in podsekcije, interni ID {sekcija}-{podsekcija}-{zaporedna}.",
      "Koraki programa: bloki z imenom, opisom in do 6 slikami z opisom; urejanje slike v slikarju (risanje po sliki).",
      "Povezave: povezovanje programov z identi (iskanje po šifrantu).",
      "Nastavitve: urejanje sekcij in podsekcij, uvoz šifranta artiklov (sifre.xls) v tabelo spl_identi.",
      "Proizvodnja - Navodila: pregled vseh navodil.",
    ],
  },
];

export const APP_VERSION = CHANGELOG[0].verzija;
