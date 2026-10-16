// Podatki navodil: sekcije, podsekcije, programi, koraki, slike, povezave na idente.
import { compressImage } from "./images";
import { SLIKE_BUCKET, db, fetchAll, napaka } from "./supabase";

export const MAX_SLIK = 6;

export type Sekcija = { id: number; koda: string; naziv: string; opis: string | null; vrstni_red: number; visible: boolean };
export type Podsekcija = {
  id: number;
  sekcija_id: number;
  koda: string;
  naziv: string;
  opis: string | null;
  vrstni_red: number;
  visible: boolean;
};
export type Druzina = { id: number; koda: string; naziv: string | null };

export type Sifranti = { sekcije: Sekcija[]; podsekcije: Podsekcija[]; druzine: Druzina[] };

export type Program = {
  id: number;
  interni_id: string;
  naziv: string;
  opis: string | null;
  zaporedna: number;
  updated_at: string;
  /** Pot končne slike proizvoda v bucketu (null = ni slike). */
  koncna_slika: string | null;
  /** Podpisan URL končne slike. */
  koncnaUrl?: string;
  druzine: number[];
  podsekcije: number[];
  stKorakov: number;
};

export type Slika = { id: number; korak_id: number; pot: string; opis: string | null; vrstni_red: number; url?: string };
export type Korak = { id: number; program_id: number; vrstni_red: number; naziv: string; opis: string | null; slike: Slika[] };

const poRedu = <T extends { vrstni_red: number; id: number }>(a: T, b: T) => a.vrstni_red - b.vrstni_red || a.id - b.id;

// =====================================================================
// ŠIFRANTI
// =====================================================================

export async function naloziSifrante(vse = false): Promise<Sifranti> {
  const sb = db();
  let qs = sb.from("wi_sekcije").select("id, koda, naziv, opis, vrstni_red, visible");
  let qp = sb.from("wi_podsekcije").select("id, sekcija_id, koda, naziv, opis, vrstni_red, visible");
  if (!vse) {
    qs = qs.eq("visible", true);
    qp = qp.eq("visible", true);
  }
  const [s, p, d] = await Promise.all([
    qs,
    qp,
    sb.from("spl_druzine").select("id, koda, naziv").eq("visible", true).order("koda"),
  ]);
  napaka(s.error);
  napaka(p.error);
  napaka(d.error);
  // izbirni seznami: sekcije po abecedi, znotraj sekcije podsekcije po abecedi
  const abc = (a: string, b: string) => a.localeCompare(b, "sl", { sensitivity: "base" });
  const sekcije = ((s.data ?? []) as Sekcija[]).sort((a, b) => abc(a.naziv, b.naziv) || a.id - b.id);
  const red = new Map(sekcije.map((x, i) => [x.id, i]));
  return {
    sekcije,
    podsekcije: ((p.data ?? []) as Podsekcija[]).sort(
      (a, b) => (red.get(a.sekcija_id) ?? 999) - (red.get(b.sekcija_id) ?? 999) || abc(a.naziv, b.naziv) || a.id - b.id,
    ),
    druzine: (d.data ?? []) as Druzina[],
  };
}

/** "Montaža · Varjenje" */
export function podsekcijaLabel(p: Podsekcija, sekcije: Sekcija[]) {
  const s = sekcije.find((x) => x.id === p.sekcija_id);
  return `${s?.naziv ?? "?"} · ${p.naziv}`;
}

export type SekcijaVnos = { id?: number; koda: string; naziv: string; opis: string | null; vrstni_red: number; visible: boolean };
export type PodsekcijaVnos = SekcijaVnos & { sekcija_id: number };

export async function shraniSekcije(vrstice: SekcijaVnos[]) {
  for (const v of vrstice) {
    const { id, ...podatki } = v;
    const q = id ? db().from("wi_sekcije").update(podatki).eq("id", id) : db().from("wi_sekcije").insert(podatki);
    const { error } = await q;
    napaka(error);
  }
}

export async function shraniPodsekcije(vrstice: PodsekcijaVnos[]) {
  for (const v of vrstice) {
    const { id, ...podatki } = v;
    const q = id ? db().from("wi_podsekcije").update(podatki).eq("id", id) : db().from("wi_podsekcije").insert(podatki);
    const { error } = await q;
    napaka(error);
  }
}

// =====================================================================
// PROGRAMI
// =====================================================================

type ProgramVrstica = Omit<Program, "druzine" | "podsekcije" | "stKorakov" | "koncnaUrl">;
type Povezava = { program_id: number; druzina_id?: number; podsekcija_id?: number };

export async function naloziPrograme(): Promise<Program[]> {
  const sb = db();
  const [programi, druzine, podsekcije, koraki] = await Promise.all([
    fetchAll<ProgramVrstica>((a, b) =>
      sb.from("wi_programi").select("id, interni_id, naziv, opis, zaporedna, updated_at, koncna_slika").eq("visible", true).order("interni_id").range(a, b),
    ),
    fetchAll<Povezava>((a, b) =>
      sb.from("ln_wi_programi_druzine").select("program_id, druzina_id").eq("visible", true).order("id").range(a, b),
    ),
    fetchAll<Povezava>((a, b) =>
      sb.from("ln_wi_programi_podsekcije").select("program_id, podsekcija_id").eq("visible", true).order("id").range(a, b),
    ),
    fetchAll<{ program_id: number }>((a, b) =>
      sb.from("wi_koraki").select("program_id").eq("visible", true).order("id").range(a, b),
    ),
  ]);
  const urlji = await podpisaniUrlji(programi.map((p) => p.koncna_slika).filter((x): x is string => !!x));
  return programi.map((p) => ({
    ...p,
    koncnaUrl: p.koncna_slika ? urlji.get(p.koncna_slika) : undefined,
    druzine: druzine.filter((d) => d.program_id === p.id).map((d) => d.druzina_id!),
    podsekcije: podsekcije.filter((d) => d.program_id === p.id).map((d) => d.podsekcija_id!),
    stKorakov: koraki.filter((k) => k.program_id === p.id).length,
  }));
}

export async function naloziProgram(id: number): Promise<Program | null> {
  const vsi = await naloziPrograme();
  return vsi.find((p) => p.id === id) ?? null;
}

/** Predpona internega ID iz prve izbrane podsekcije, npr. "PR-VAR". */
export function predponaId(podsekcijaId: number | undefined, s: Sifranti): string {
  const p = s.podsekcije.find((x) => x.id === podsekcijaId);
  const sek = p && s.sekcije.find((x) => x.id === p.sekcija_id);
  return p && sek ? `${sek.koda}-${p.koda}` : "WI";
}

/** Naslednja prosta zaporedna številka za predpono (upošteva tudi skrite programe). */
async function naslednjiId(predpona: string): Promise<{ interni_id: string; zaporedna: number }> {
  const { data, error } = await db().from("wi_programi").select("interni_id").like("interni_id", `${predpona}-%`);
  napaka(error);
  const max = Math.max(
    0,
    ...(data ?? []).map((r) => Number(String(r.interni_id).slice(predpona.length + 1)) || 0),
  );
  const zaporedna = max + 1;
  return { interni_id: `${predpona}-${String(zaporedna).padStart(3, "0")}`, zaporedna };
}

export type ProgramVnos = { naziv: string; opis: string; druzine: number[]; podsekcije: number[] };

/** Uskladi povezovalno tabelo: izbrane vidne, ostale skrite (ne brišemo). */
async function uskladiPovezave(tabela: string, stolpec: string, programId: number, izbrani: number[]) {
  const { data, error } = await db().from(tabela).select(`id, ${stolpec}, visible`).eq("program_id", programId);
  napaka(error);
  const obstojeci = (data ?? []) as unknown as ({ id: number; visible: boolean } & Record<string, number>)[];
  const skrij = obstojeci.filter((r) => r.visible && !izbrani.includes(r[stolpec])).map((r) => r.id);
  if (skrij.length) napaka((await db().from(tabela).update({ visible: false }).in("id", skrij)).error);
  if (izbrani.length) {
    const { error: e2 } = await db()
      .from(tabela)
      .upsert(
        izbrani.map((v) => ({ program_id: programId, [stolpec]: v, visible: true })),
        { onConflict: `program_id,${stolpec}` },
      );
    napaka(e2);
  }
}

export async function ustvariProgram(vnos: ProgramVnos, s: Sifranti, kopirajIz?: number): Promise<number> {
  const id = await naslednjiId(predponaId(vnos.podsekcije[0], s));
  const { data, error } = await db()
    .from("wi_programi")
    .insert({ ...id, naziv: vnos.naziv.trim(), opis: vnos.opis.trim() || null })
    .select("id")
    .single();
  napaka(error);
  const novId = (data as { id: number }).id;
  await uskladiPovezave("ln_wi_programi_druzine", "druzina_id", novId, vnos.druzine);
  await uskladiPovezave("ln_wi_programi_podsekcije", "podsekcija_id", novId, vnos.podsekcije);
  if (kopirajIz) await kopirajKorake(kopirajIz, novId);
  return novId;
}

export async function posodobiProgram(id: number, vnos: ProgramVnos) {
  napaka(
    (await db().from("wi_programi").update({ naziv: vnos.naziv.trim(), opis: vnos.opis.trim() || null }).eq("id", id)).error,
  );
  await uskladiPovezave("ln_wi_programi_druzine", "druzina_id", id, vnos.druzine);
  await uskladiPovezave("ln_wi_programi_podsekcije", "podsekcija_id", id, vnos.podsekcije);
}

/** Odstrani program (skrije ga - podatki ostanejo v bazi). */
export async function odstraniProgram(id: number) {
  napaka((await db().from("wi_programi").update({ visible: false }).eq("id", id)).error);
}

// =====================================================================
// KORAKI IN SLIKE
// =====================================================================

/** Podpisani URL-ji za poti v bucketu (bucket je zaseben). */
async function podpisaniUrlji(poti: string[]): Promise<Map<string, string>> {
  const m = new Map<string, string>();
  for (let i = 0; i < poti.length; i += 500) {
    const { data, error } = await db().storage.from(SLIKE_BUCKET).createSignedUrls(poti.slice(i, i + 500), 60 * 60);
    napaka(error);
    for (const d of data ?? []) if (d.path && d.signedUrl) m.set(d.path, d.signedUrl);
  }
  return m;
}

/** Naloži / zamenja končno sliko proizvoda; stara datoteka se izbriše. */
export async function nastaviKoncnoSliko(program: Program, blob: Blob): Promise<Program> {
  const pot = `programi/${program.id}/koncna-${Date.now()}.jpg`;
  await naloziDatoteko(pot, blob);
  napaka((await db().from("wi_programi").update({ koncna_slika: pot }).eq("id", program.id)).error);
  if (program.koncna_slika) await db().storage.from(SLIKE_BUCKET).remove([program.koncna_slika]);
  return { ...program, koncna_slika: pot, koncnaUrl: (await podpisaniUrlji([pot])).get(pot) };
}

export async function odstraniKoncnoSliko(program: Program): Promise<Program> {
  napaka((await db().from("wi_programi").update({ koncna_slika: null }).eq("id", program.id)).error);
  if (program.koncna_slika) await db().storage.from(SLIKE_BUCKET).remove([program.koncna_slika]);
  return { ...program, koncna_slika: null, koncnaUrl: undefined };
}

export async function prenesiKoncnoSliko(program: Program): Promise<Blob> {
  const { data, error } = await db().storage.from(SLIKE_BUCKET).download(program.koncna_slika!);
  napaka(error);
  return data!;
}

/** Podpisani URL-ji slik (bucket je zaseben). */
async function dodajUrlje(slike: Slika[]): Promise<Slika[]> {
  if (!slike.length) return slike;
  const { data, error } = await db().storage.from(SLIKE_BUCKET).createSignedUrls(slike.map((s) => s.pot), 60 * 60);
  napaka(error);
  return slike.map((s) => ({ ...s, url: data?.find((d) => d.path === s.pot)?.signedUrl ?? undefined }));
}

export async function naloziKorake(programId: number): Promise<Korak[]> {
  const { data: k, error } = await db()
    .from("wi_koraki")
    .select("id, program_id, vrstni_red, naziv, opis")
    .eq("program_id", programId)
    .eq("visible", true);
  napaka(error);
  const koraki = ((k ?? []) as Omit<Korak, "slike">[]).sort(poRedu);
  if (!koraki.length) return [];
  const { data: sl, error: e2 } = await db()
    .from("wi_slike")
    .select("id, korak_id, pot, opis, vrstni_red")
    .in("korak_id", koraki.map((x) => x.id));
  napaka(e2);
  const slike = await dodajUrlje(((sl ?? []) as Slika[]).sort(poRedu));
  return koraki.map((x) => ({ ...x, slike: slike.filter((s) => s.korak_id === x.id) }));
}

export async function dodajKorak(programId: number, vrstniRed: number): Promise<Korak> {
  const { data, error } = await db()
    .from("wi_koraki")
    .insert({ program_id: programId, vrstni_red: vrstniRed, naziv: "", opis: null })
    .select("id, program_id, vrstni_red, naziv, opis")
    .single();
  napaka(error);
  return { ...(data as Omit<Korak, "slike">), slike: [] };
}

export async function shraniKorak(id: number, naziv: string, opis: string) {
  napaka((await db().from("wi_koraki").update({ naziv: naziv.trim(), opis: opis.trim() || null }).eq("id", id)).error);
}

export async function shraniOpisSlike(id: number, opis: string) {
  napaka((await db().from("wi_slike").update({ opis: opis.trim() || null }).eq("id", id)).error);
}

/** Odstrani korak (skrije ga). Slike koraka se izbrišejo (prostor). */
export async function odstraniKorak(korak: Korak) {
  for (const s of korak.slike) await izbrisiSliko(s);
  napaka((await db().from("wi_koraki").update({ visible: false }).eq("id", korak.id)).error);
}

/** Zapiše nov vrstni red korakov (1, 2, 3 ...). */
export async function prerazporediKorake(idji: number[]) {
  for (const [i, id] of idji.entries()) {
    napaka((await db().from("wi_koraki").update({ vrstni_red: i + 1 }).eq("id", id)).error);
  }
}

/** Zapiše nov vrstni red slik koraka (1, 2, 3 ...). */
export async function prerazporediSlike(idji: number[]) {
  for (const [i, id] of idji.entries()) {
    napaka((await db().from("wi_slike").update({ vrstni_red: i + 1 }).eq("id", id)).error);
  }
}

const novaPot = (programId: number, korakId: number) =>
  `programi/${programId}/${korakId}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.jpg`;

async function naloziDatoteko(pot: string, blob: Blob) {
  const stisnjena = await compressImage(blob);
  const { error } = await db().storage.from(SLIKE_BUCKET).upload(pot, stisnjena, { contentType: "image/jpeg" });
  napaka(error);
}

export async function dodajSliko(korak: Korak, datoteka: Blob): Promise<Slika> {
  const pot = novaPot(korak.program_id, korak.id);
  await naloziDatoteko(pot, datoteka);
  const vrstniRed = Math.max(0, ...korak.slike.map((s) => s.vrstni_red)) + 1;
  const { data, error } = await db()
    .from("wi_slike")
    .insert({ korak_id: korak.id, pot, opis: null, vrstni_red: vrstniRed })
    .select("id, korak_id, pot, opis, vrstni_red")
    .single();
  if (error) await db().storage.from(SLIKE_BUCKET).remove([pot]);
  napaka(error);
  return (await dodajUrlje([data as Slika]))[0];
}

/** Zamenja datoteko slike (npr. po urejanju v slikarju); stara datoteka se izbriše. */
export async function zamenjajSliko(slika: Slika, programId: number, blob: Blob): Promise<Slika> {
  const pot = novaPot(programId, slika.korak_id);
  await naloziDatoteko(pot, blob);
  napaka((await db().from("wi_slike").update({ pot }).eq("id", slika.id)).error);
  await db().storage.from(SLIKE_BUCKET).remove([slika.pot]);
  return (await dodajUrlje([{ ...slika, pot }]))[0];
}

export async function izbrisiSliko(slika: Slika) {
  await db().storage.from(SLIKE_BUCKET).remove([slika.pot]);
  napaka((await db().from("wi_slike").delete().eq("id", slika.id)).error);
}

export async function prenesiSliko(slika: Slika): Promise<Blob> {
  const { data, error } = await db().storage.from(SLIKE_BUCKET).download(slika.pot);
  napaka(error);
  return data!;
}

// =====================================================================
// PRIPRAVA DELOVNEGA MESTA (alineje dodatne opreme)
// =====================================================================

export type PripravaTip = "oprema" | "orodje";
export type Priprava = { id: number; program_id: number; tip: PripravaTip; naziv: string; vrstni_red: number };

export async function naloziPripravo(programId: number): Promise<Priprava[]> {
  const { data, error } = await db()
    .from("wi_priprava")
    .select("id, program_id, tip, naziv, vrstni_red")
    .eq("program_id", programId)
    .eq("visible", true);
  napaka(error);
  return ((data ?? []) as Priprava[]).sort(poRedu);
}

/** Doda postavke na konec seznama (več vrstic naenkrat, npr. prilepljen seznam). */
export async function dodajPripravo(programId: number, nazivi: string[], odReda: number, tip: PripravaTip = "oprema"): Promise<Priprava[]> {
  const { data, error } = await db()
    .from("wi_priprava")
    .insert(nazivi.map((naziv, i) => ({ program_id: programId, tip, naziv, vrstni_red: odReda + i })))
    .select("id, program_id, tip, naziv, vrstni_red");
  napaka(error);
  return ((data ?? []) as Priprava[]).sort(poRedu);
}

export async function shraniPripravo(id: number, naziv: string) {
  napaka((await db().from("wi_priprava").update({ naziv: naziv.trim() }).eq("id", id)).error);
}

/** Odstrani postavko (skrije jo). */
export async function odstraniPripravo(id: number) {
  napaka((await db().from("wi_priprava").update({ visible: false }).eq("id", id)).error);
}

export async function prerazporediPripravo(idji: number[]) {
  for (const [i, id] of idji.entries()) {
    napaka((await db().from("wi_priprava").update({ vrstni_red: i + 1 }).eq("id", id)).error);
  }
}

/** Kopira pripravo delovnega mesta, korake in slike programa v drug program. */
async function kopirajKorake(izId: number, vId: number) {
  const priprava = await naloziPripravo(izId);
  if (priprava.length) {
    napaka(
      (
        await db()
          .from("wi_priprava")
          .insert(priprava.map((p) => ({ program_id: vId, tip: p.tip, naziv: p.naziv, vrstni_red: p.vrstni_red })))
      ).error,
    );
  }
  const koraki = await naloziKorake(izId);
  for (const k of koraki) {
    const { data, error } = await db()
      .from("wi_koraki")
      .insert({ program_id: vId, vrstni_red: k.vrstni_red, naziv: k.naziv, opis: k.opis })
      .select("id")
      .single();
    napaka(error);
    const novKorak = (data as { id: number }).id;
    for (const s of k.slike) {
      const pot = novaPot(vId, novKorak);
      napaka((await db().storage.from(SLIKE_BUCKET).copy(s.pot, pot)).error);
      napaka(
        (await db().from("wi_slike").insert({ korak_id: novKorak, pot, opis: s.opis, vrstni_red: s.vrstni_red })).error,
      );
    }
  }
}

// =====================================================================
// POVEZAVE PROGRAM - IDENT
// =====================================================================

export type Ident = { sifra: string; naziv: string | null; klasifikat: string | null; status: string | null; tip_materiala: string | null };
export type PovezavaIdent = {
  id: number;
  program_id: number;
  ident: string;
  created_at: string;
  /** Iz šifranta (null, če identa ni v šifrantu). */
  naziv: string | null;
  klasifikat: string | null;
  status: string | null;
};
type PovezavaVrstica = Omit<PovezavaIdent, "naziv" | "klasifikat" | "status">;
type IdentPodatki = Pick<Ident, "naziv" | "klasifikat" | "status">;

export async function naloziPovezave(): Promise<PovezavaIdent[]> {
  const vrstice = await fetchAll<PovezavaVrstica>((a, b) =>
    db().from("ln_wi_programi_identi").select("id, program_id, ident, created_at").eq("visible", true).order("ident").range(a, b),
  );
  const podatki = new Map<string, IdentPodatki>();
  const sifre = [...new Set(vrstice.map((v) => v.ident))];
  for (let i = 0; i < sifre.length; i += 200) {
    const { data, error } = await db()
      .from("spl_identi")
      .select("sifra, naziv, klasifikat, status")
      .in("sifra", sifre.slice(i, i + 200));
    napaka(error);
    for (const r of data ?? []) podatki.set(r.sifra, { naziv: r.naziv, klasifikat: r.klasifikat, status: r.status });
  }
  // ident, ki ga ni v šifrantu: klasifikat iz šifre (npr. 100-601 -> 100)
  return vrstice.map((v) => {
    const p = podatki.get(v.ident);
    return { ...v, naziv: p?.naziv ?? null, klasifikat: p?.klasifikat ?? v.ident.split("-")[0], status: p?.status ?? null };
  });
}

export async function poveziIdente(programId: number, identi: string[]) {
  const { error } = await db()
    .from("ln_wi_programi_identi")
    .upsert(
      identi.map((ident) => ({ program_id: programId, ident, visible: true })),
      { onConflict: "program_id,ident" },
    );
  napaka(error);
}

export async function odstraniPovezavo(id: number) {
  napaka((await db().from("ln_wi_programi_identi").update({ visible: false }).eq("id", id)).error);
}

/** Odstrani več povezav naenkrat (skrije jih). */
export async function odstraniPovezave(idji: number[]) {
  for (let i = 0; i < idji.length; i += 200) {
    napaka((await db().from("ln_wi_programi_identi").update({ visible: false }).in("id", idji.slice(i, i + 200))).error);
  }
}

/** Celoten šifrant (stolpci za izbiro identov pri povezavah). */
export async function naloziVseIdente(): Promise<Ident[]> {
  return fetchAll<Ident>((a, b) =>
    db().from("spl_identi").select("sifra, naziv, klasifikat, status, tip_materiala").eq("visible", true).order("sifra").range(a, b),
  );
}

// =====================================================================
// SKENIRANJE: delovni nalog ali ident -> navodila
// =====================================================================

export type Zadetek = {
  koda: string;
  ident: string | null;
  naziv: string | null;
  /** Številka naloga, če je bil skeniran nalog. */
  nalog: string | null;
  programi: Program[];
};

export async function poisciNavodila(vnos: string): Promise<Zadetek> {
  const koda = vnos.trim();
  let ident: string | null = null;
  let naziv: string | null = null;
  let nalog: string | null = null;

  // 1. delovni nalog (zadnji uvoz nalogov iz FINES_Production)
  const n = await db()
    .from("fp_zas_nalogi")
    .select("st_naloga, koda_artikla, naziv_artikla")
    .eq("st_naloga", koda)
    .order("id", { ascending: false })
    .limit(1);
  if (!n.error && n.data?.length) {
    nalog = n.data[0].st_naloga;
    ident = n.data[0].koda_artikla;
    naziv = n.data[0].naziv_artikla;
  }

  // 2. ident (šifra artikla)
  if (!ident) {
    const i = await db().from("spl_identi").select("sifra, naziv").eq("sifra", koda).limit(1);
    if (!i.error && i.data?.length) {
      ident = i.data[0].sifra;
      naziv = i.data[0].naziv;
    } else {
      const p = await db().from("ln_wi_programi_identi").select("ident").eq("ident", koda).eq("visible", true).limit(1);
      if (!p.error && p.data?.length) ident = koda;
    }
  }
  if (!ident) return { koda, ident: null, naziv: null, nalog: null, programi: [] };

  const { data, error } = await db().from("ln_wi_programi_identi").select("program_id").eq("ident", ident).eq("visible", true);
  napaka(error);
  const idji = new Set((data ?? []).map((r) => r.program_id as number));
  const programi = idji.size ? (await naloziPrograme()).filter((p) => idji.has(p.id)) : [];
  if (!naziv) {
    const i = await db().from("spl_identi").select("naziv").eq("sifra", ident).limit(1);
    naziv = i.data?.[0]?.naziv ?? null;
  }
  return { koda, ident, naziv, nalog, programi };
}
