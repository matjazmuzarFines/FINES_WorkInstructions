// AI trening (training ground) - skupni tipi za brskalnik in strežnik.
// Podatki so v mapi `trening/` v repozitoriju; bere jih samo lokalni strežnik (glej trening/README.md).

/** AI, ki ju primerjamo. Ime mape poskusa = koda. */
export const AI_JI = [
  { koda: "astra", naziv: "GPT-6.2 Astra", orodje: "Codex v VS Code" },
  { koda: "fable", naziv: "Claude Fable 5.2", orodje: "Claude Code v VS Code" },
] as const;

export type AiKoda = (typeof AI_JI)[number]["koda"];

export const jeAiKoda = (v: unknown): v is AiKoda => AI_JI.some((a) => a.koda === v);

/** Kriteriji ocenjevanja (1-5) - izhajajo iz merila uspeha v NALOGA_ZA_AI.md. */
export const KRITERIJI = [
  { koda: "uvoz", naziv: "Uvoz geometrije", opis: "Pravi deli, ločeni, prave enote in položaji" },
  { koda: "sledljivost", naziv: "Sledljivost delov", opis: "Isti ID dela od uvoza do videa" },
  { koda: "animacija", naziv: "Animacija", opis: "Programsko krmiljena, gibi smiselni, brez napak" },
  { koda: "razumljivost", naziv: "Razumljivost za monterja", opis: "Kamera, oznake, tempo, opisi korakov" },
  { koda: "postenost", naziv: "Poštenost poročila", opis: "Neznanke označene, nič izmišljenega" },
  { koda: "ponovljivost", naziv: "Ponovljivost", opis: "Skripte se zaženejo znova z istim rezultatom" },
] as const;

export type KriterijKoda = (typeof KRITERIJI)[number]["koda"];

export type Ocena = {
  kriteriji: Partial<Record<KriterijKoda, number>>;
  komentar: string;
  datum: string;
};

/** Ključ ocene v ocene.json: "astra/01". */
export const kljucOcene = (ai: AiKoda, poskus: string) => `${ai}/${poskus}`;

export type Datoteka = { pot: string; ime: string; velikost: number; cas: string };

/** meta.json poskusa (piše AI). Vsa polja so neobvezna - aplikacija pokaže, kar je. */
export type PoskusMeta = {
  ai_model?: string;
  zacetek?: string;
  konec?: string;
  status?: "uspeh" | "delno" | "neuspeh" | string;
  povzetek?: string;
  orodja?: string[];
  tezave?: string[];
};

export type Del = {
  id: string;
  ime?: string;
  tip?: string;
  stars?: string | null;
  kolicina?: number;
  bbox_mm?: { min: number[]; max: number[] };
  volumen_mm3?: number;
  opomba?: string;
};

export type Korak = {
  st: number;
  naslov?: string;
  opis?: string;
  deli?: string[];
  gibanje?: { tip?: string; trajanje_s?: number; [k: string]: unknown };
  kamera?: unknown;
  opozorila?: string[];
  potrditev?: string;
};

/** Prebrana JSON datoteka: podatki ali opis napake (AI je morda zapisal neveljaven JSON). */
export type Json<T> = { podatki: T } | { napaka: string } | null;

export type Poskus = {
  ai: AiKoda;
  poskus: string;
  meta: Json<PoskusMeta>;
  deli: Json<Del[]>;
  koraki: Json<Korak[]>;
  porocilo: string | null;
  spoznanja: string | null;
  video: string | null;
  predogled: string | null;
  datoteke: Datoteka[];
};

export type ModelInfo = {
  naziv?: string;
  opis?: string;
  opombe?: string;
  ustvarjen?: string;
};

export type TreningModel = {
  id: string;
  info: Json<ModelInfo>;
  vhod: Datoteka[];
  poskusi: Record<AiKoda, Poskus[]>;
  ocene: Record<string, Ocena>;
};

export type TreningIndeks =
  | { omogoceno: true; koren: string; modeli: TreningModel[]; znanje: string | null }
  | { omogoceno: false; razlog: string };

/** Naslednja številka poskusa ("01", "02" ...). */
export function naslednjiPoskus(poskusi: Poskus[]): string {
  const max = poskusi.reduce((m, p) => Math.max(m, Number.parseInt(p.poskus, 10) || 0), 0);
  return String(max + 1).padStart(2, "0");
}

/** Povprečna ocena (samo vpisani kriteriji), null če ni nobene. */
export function povprecje(o: Ocena | undefined): number | null {
  const v = Object.values(o?.kriteriji ?? {}).filter((x): x is number => typeof x === "number");
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}

/** Zagonski prompt, ki ga prilepiš v chat AI-ja (enak za oba, razlikuje se samo koda). */
export function zagonskiPrompt(ai: AiKoda, modelId: string, poskus: string): string {
  const vrstice = [
    `Preberi trening/NALOGA_ZA_AI.md in trening/ZNANJE.md ter izvedi nalogo.`,
    `Ti si AI: ${ai}`,
    `Model: trening/modeli/${modelId}`,
    `Poskus: ${poskus}`,
    `Vse izhode zapiši samo v trening/modeli/${modelId}/${ai}/${poskus}/.`,
  ];
  if (poskus !== "01") {
    vrstice.push(
      "Najprej preberi svoje prejšnje poskuse in mojo oceno v ocene.json. Za vsako pripombo ugotovi vzrok in poišči boljšo rešitev (orodje, postopek, kontrola), ne samo drugačno generiranje. Diagnozo zapiši na začetek porocilo.md.",
    );
  }
  return vrstice.join("\n");
}
