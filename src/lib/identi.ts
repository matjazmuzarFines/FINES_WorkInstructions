// Uvoz šifranta artiklov (izvoz "sifre.xls") v tabelo spl_identi.
import { parseNum } from "./stevila";
import { db, kosi, napaka } from "./supabase";

type Tip = "text" | "bool" | "num" | "cas" | "datum";

/** Stolpec v Excelu (glava v 2. vrstici) -> stolpec v bazi. */
const STOLPCI: [string, string, Tip][] = [
  ["Vrsta", "vrsta", "text"],
  ["RD", "rd", "bool"],
  ["RDP", "rdp", "bool"],
  ["PM", "pm", "bool"],
  ["Proizvodna šifra", "sifra", "text"],
  ["VK", "vk", "bool"],
  ["Naziv", "naziv", "text"],
  ["Urejenost tehnične dokumentacije", "urejenost_teh_dok", "bool"],
  ["Urejenost nabavnih parametrov", "urejenost_nab_param", "bool"],
  ["Vgradnja", "vgradnja", "text"],
  ["Status", "status", "text"],
  ["Kataloška št.", "kataloska_st", "text"],
  ["EM", "em", "text"],
  ["Klasifikacija", "klasifikacija", "text"],
  ["Tip materiala", "tip_materiala", "text"],
  ["Pripadnost", "pripadnost", "text"],
  ["Dobavitelj", "dobavitelj", "text"],
  ["Proizvajalec", "proizvajalec", "text"],
  ["Material", "material", "text"],
  ["Standard", "standard", "text"],
  ["Faktor 1", "faktor_1", "num"],
  ["Faktor 2", "faktor_2", "num"],
  ["Neakt.", "neaktiven", "bool"],
  ["Oznaka dokumenta", "oznaka_dokumenta", "text"],
  ["Dodatni naziv", "dodatni_naziv", "text"],
  ["Poreklo", "poreklo", "text"],
  ["Rabatna skupina", "rabatna_skupina", "text"],
  ["Bruto teža", "bruto_teza", "num"],
  ["Neto teža", "neto_teza", "num"],
  ["Tarifna številka", "tarifna_stevilka", "text"],
  ["Naziv ANG", "naziv_ang", "text"],
  ["Kratica", "kratica", "text"],
  ["Družina", "druzina", "text"],
  ["Karakteristično število", "karakteristicno_stevilo", "text"],
  ["Odpiranje", "odpiranje", "text"],
  ["Upravljanje", "upravljanje", "text"],
  ["Partner", "partner", "text"],
  ["Model", "model", "text"],
  ["Uporabnik (KREIRAL)", "kreiral_uporabnik", "text"],
  ["Datum/ura (KREIRAL)", "kreiral_cas", "cas"],
  ["Uporabnik (AŽURIRAL)", "azuriral_uporabnik", "text"],
  ["Datum/ura (AŽURIRAL)", "azuriral_cas", "cas"],
  ["Prodajna cena", "prodajna_cena", "num"],
  ["Nabavna cena", "nabavna_cena", "num"],
  ["Cena v kooperaciji", "cena_kooperacija", "num"],
  ["Povprečna cena", "povprecna_cena", "num"],
  ["Cena zadnjega prevzema", "cena_zadnjega_prevzema", "num"],
  ["Datum zad. prevzema", "datum_zad_prevzema", "datum"],
  ["Faktor vrednosti", "faktor_vrednosti", "num"],
  ["Planirana lastna cena", "planirana_lastna_cena", "num"],
  ["Planirana prodajna cena", "planirana_prodajna_cena", "num"],
  ["Prodajna cena indeks (%)", "prodajna_cena_indeks", "num"],
];

const norm = (s: unknown) => String(s ?? "").trim().toLowerCase();

function tekst(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s === "" ? null : s;
}

/** "15.10.2026 12:03:00" -> "2026-10-15T12:03:00" (brez časovnega pasu). */
function cas(v: unknown, samoDatum: boolean): string | null {
  if (v instanceof Date) {
    const iso = new Date(v.getTime() - v.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
    return samoDatum ? iso.slice(0, 10) : iso;
  }
  const m = String(v ?? "").trim().match(/^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (!m) return null;
  const d = `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  if (samoDatum) return d;
  return `${d}T${(m[4] ?? "0").padStart(2, "0")}:${m[5] ?? "00"}:${m[6] ?? "00"}`;
}

function pretvori(v: unknown, tip: Tip): string | number | boolean | null {
  switch (tip) {
    case "bool": {
      const s = norm(v);
      if (s === "true" || s === "1" || s === "da") return true;
      if (s === "false" || s === "0" || s === "ne") return false;
      return null;
    }
    case "num":
      return parseNum(v);
    case "cas":
      return cas(v, false);
    case "datum":
      return cas(v, true);
    default:
      return tekst(v);
  }
}

export type UvozIdentov = { vrstice: Record<string, unknown>[]; manjkajoci: string[]; podvojene: number; datoteka: string };

/** Prebere izvoz šifranta (xls je v kodni tabeli Windows-1250). */
export async function preberiSifre(file: File): Promise<UvozIdentov> {
  const XLSX = await import("xlsx");
  const cptable = await import("xlsx/dist/cpexcel.full.mjs");
  XLSX.set_cptable(cptable);
  const wb = XLSX.read(await file.arrayBuffer(), { codepage: 1250, cellDates: true });
  const rows = XLSX.utils.sheet_to_json<unknown[]>(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: null, raw: true });

  // vrstica z glavo: tista, ki vsebuje "Proizvodna šifra"
  const iGlava = rows.findIndex((r) => r.some((c) => norm(c) === "proizvodna šifra"));
  if (iGlava < 0) throw new Error('V datoteki ni stolpca "Proizvodna šifra".');
  const glava = rows[iGlava].map(norm);
  const indeksi = STOLPCI.map(([ime, stolpec, tip]) => ({ i: glava.indexOf(norm(ime)), stolpec, tip, ime }));
  const manjkajoci = indeksi.filter((x) => x.i < 0).map((x) => x.ime);

  const poSifri = new Map<string, Record<string, unknown>>();
  let podvojene = 0;
  for (const r of rows.slice(iGlava + 1)) {
    const zapis: Record<string, unknown> = { visible: true };
    for (const x of indeksi) if (x.i >= 0) zapis[x.stolpec] = pretvori(r[x.i], x.tip);
    const sifra = zapis.sifra as string | null;
    if (!sifra) continue;
    if (poSifri.has(sifra)) podvojene++;
    poSifri.set(sifra, zapis);
  }
  return { vrstice: [...poSifri.values()], manjkajoci, podvojene, datoteka: file.name };
}

/** Vpiše šifre (upsert po šifri) in zabeleži uvoz. */
export async function uvoziSifre(uvoz: UvozIdentov, napredek: (n: number) => void) {
  let n = 0;
  for (const kos of kosi(uvoz.vrstice, 500)) {
    napaka((await db().from("spl_identi").upsert(kos, { onConflict: "sifra" })).error);
    n += kos.length;
    napredek(n);
  }
  napaka((await db().from("wi_uvozi").insert({ tip: "identi", datoteka: uvoz.datoteka, stevilo: uvoz.vrstice.length })).error);
}

export type ZadnjiUvoz = { datoteka: string; stevilo: number; created_at: string };

export async function zadnjiUvozSifer(): Promise<{ uvoz: ZadnjiUvoz | null; stevilo: number }> {
  const [u, c] = await Promise.all([
    db().from("wi_uvozi").select("datoteka, stevilo, created_at").eq("tip", "identi").order("id", { ascending: false }).limit(1),
    db().from("spl_identi").select("id", { count: "exact", head: true }),
  ]);
  napaka(u.error);
  napaka(c.error);
  return { uvoz: (u.data?.[0] as ZadnjiUvoz) ?? null, stevilo: c.count ?? 0 };
}
