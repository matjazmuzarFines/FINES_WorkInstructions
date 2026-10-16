// Zgodovina verzij - prikazana v "i" popupu (desni zgornji kot).
// Pravilo: male spremembe 1.01 -> 1.02, večje spremembe / nova funkcija / podstran -> 2.01.

export type ChangelogEntry = {
  verzija: string;
  datum: string;
  spremembe: string[];
};

export const CHANGELOG: ChangelogEntry[] = [
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
