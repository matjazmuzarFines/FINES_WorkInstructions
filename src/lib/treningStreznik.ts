// AI trening - samo strežnik (Node). Bere in piše mapo `trening/` v repozitoriju.
import { promises as fs } from "node:fs";
import path from "node:path";
import { createClient } from "@supabase/supabase-js";
import {
  AI_JI,
  type AiKoda,
  type Datoteka,
  type Json,
  type ModelInfo,
  type Ocena,
  type Poskus,
  type TreningIndeks,
  type TreningModel,
  kljucOcene,
} from "./trening";

export const KOREN = path.join(process.cwd(), "trening");
const MODELI = path.join(KOREN, "modeli");

/** Na Vercelu mape ni - training ground deluje samo na lokalnem strežniku. */
export function razlogIzklopa(): string | null {
  if (process.env.VERCEL) return "AI trening deluje samo na lokalnem strežniku (ne na Vercelu).";
  return null;
}

// ---------- dostop ----------

const URL_SB = process.env.NEXT_PUBLIC_SUPABASE_URL;
const KLJUC_SB = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const preverjeni = new Map<string, number>();

/**
 * Preveri, da je zahteva od prijavljenega admina (Supabase žeton + tabela wi_admini).
 * Žeton pride v glavi Authorization ali v parametru `t` (za <video> in <img>, ki ne pošiljata glav).
 * Strežnik teče na 0.0.0.0, zato brez tega preverjanja CAD podatke vidi vsak v omrežju.
 */
export async function preveriAdmina(req: Request): Promise<string | null> {
  const glava = req.headers.get("authorization");
  const zeton = glava?.startsWith("Bearer ") ? glava.slice(7) : new URL(req.url).searchParams.get("t");
  if (!zeton) return "Ni prijave.";
  const velja = preverjeni.get(zeton);
  if (velja && velja > Date.now()) return null;
  if (!URL_SB || !KLJUC_SB) return "Supabase ni nastavljen (.env.local).";

  const sb = createClient(URL_SB, KLJUC_SB, {
    global: { headers: { Authorization: `Bearer ${zeton}` } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await sb.auth.getUser(zeton);
  const email = data.user?.email;
  if (error || !email) return "Prijava ni veljavna.";
  const { data: admini, error: e2 } = await sb
    .from("wi_admini")
    .select("id")
    .eq("visible", true)
    .ilike("email", email)
    .limit(1);
  if (e2 || !admini?.length) return "Potreben je admin dostop.";
  preverjeni.set(zeton, Date.now() + 5 * 60_000);
  return null;
}

// ---------- poti ----------

const VARNO_IME = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export const jeVarnoIme = (ime: string) => VARNO_IME.test(ime);

/** Relativna pot znotraj `trening/` -> absolutna; null, če bi ušla iz mape. */
export function varnaPot(relativna: string): string | null {
  const abs = path.resolve(KOREN, relativna);
  return abs.startsWith(KOREN + path.sep) ? abs : null;
}

const rel = (abs: string) => path.relative(KOREN, abs).split(path.sep).join("/");

async function obstaja(p: string) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function mape(p: string): Promise<string[]> {
  try {
    const vnosi = await fs.readdir(p, { withFileTypes: true });
    return vnosi.filter((v) => v.isDirectory() && !v.name.startsWith(".") && !v.name.startsWith("_")).map((v) => v.name).sort();
  } catch {
    return [];
  }
}

/** Vse datoteke v mapi (rekurzivno, največ `max`), brez skritih map in virtualnih okolij. */
async function datoteke(p: string, max = 300): Promise<Datoteka[]> {
  const out: Datoteka[] = [];
  const PRESKOCI = new Set(["node_modules", ".venv", "venv", "__pycache__", ".git"]);
  async function hodi(mapa: string) {
    let vnosi;
    try {
      vnosi = await fs.readdir(mapa, { withFileTypes: true });
    } catch {
      return;
    }
    for (const v of vnosi) {
      if (out.length >= max || v.name.startsWith(".") || PRESKOCI.has(v.name)) continue;
      const abs = path.join(mapa, v.name);
      if (v.isDirectory()) await hodi(abs);
      else if (v.isFile()) {
        const st = await fs.stat(abs);
        out.push({ pot: rel(abs), ime: path.relative(p, abs).split(path.sep).join("/"), velikost: st.size, cas: st.mtime.toISOString() });
      }
    }
  }
  await hodi(p);
  return out.sort((a, b) => a.ime.localeCompare(b.ime));
}

async function beriJson<T>(p: string): Promise<Json<T>> {
  let besedilo: string;
  try {
    besedilo = await fs.readFile(p, "utf8");
  } catch {
    return null;
  }
  try {
    return { podatki: JSON.parse(besedilo.replace(/^﻿/, "")) as T };
  } catch (e) {
    return { napaka: `Neveljaven JSON: ${(e as Error).message}` };
  }
}

/** deli.json / koraki.json sta lahko seznam ali objekt { deli: [...] } / { koraki: [...] }. */
function seznam<T>(j: Json<unknown>, kljuc: string): Json<T[]> {
  if (!j || "napaka" in j) return j as Json<T[]>;
  const d = j.podatki as Record<string, unknown>;
  const arr = Array.isArray(d) ? d : Array.isArray(d?.[kljuc]) ? d[kljuc] : null;
  return arr ? { podatki: arr as T[] } : { napaka: `Pričakovan seznam ali objekt s poljem "${kljuc}".` };
}

const MAX_BESEDILO = 200_000;

async function beriBesedilo(p: string): Promise<string | null> {
  try {
    return (await fs.readFile(p, "utf8")).slice(0, MAX_BESEDILO);
  } catch {
    return null;
  }
}

async function beriPoskus(ai: AiKoda, mapa: string, poskus: string): Promise<Poskus> {
  const p = path.join(mapa, poskus);
  const vse = await datoteke(p);
  const najdi = (...imena: string[]) => {
    for (const ime of imena) {
      const d = vse.find((x) => x.ime.toLowerCase() === ime);
      if (d) return d.pot;
    }
    return null;
  };
  return {
    ai,
    poskus,
    meta: await beriJson(path.join(p, "meta.json")),
    deli: seznam(await beriJson(path.join(p, "deli.json")), "deli"),
    koraki: seznam(await beriJson(path.join(p, "koraki.json")), "koraki"),
    porocilo: await beriBesedilo(path.join(p, "porocilo.md")),
    spoznanja: await beriBesedilo(path.join(p, "spoznanja.md")),
    video: najdi("video.mp4", "video.webm"),
    predogled: najdi("predogled.png", "predogled.jpg"),
    datoteke: vse,
  };
}

async function beriModel(id: string): Promise<TreningModel> {
  const m = path.join(MODELI, id);
  const poskusi = {} as Record<AiKoda, Poskus[]>;
  for (const { koda } of AI_JI) {
    const mapaAi = path.join(m, koda);
    poskusi[koda] = await Promise.all((await mape(mapaAi)).map((p) => beriPoskus(koda, mapaAi, p)));
  }
  const ocene = await beriJson<Record<string, Ocena>>(path.join(m, "ocene.json"));
  return {
    id,
    info: await beriJson<ModelInfo>(path.join(m, "model.json")),
    vhod: await datoteke(path.join(m, "vhod")),
    poskusi,
    ocene: ocene && "podatki" in ocene ? ocene.podatki : {},
  };
}

export async function beriIndeks(): Promise<TreningIndeks> {
  const razlog = razlogIzklopa();
  if (razlog) return { omogoceno: false, razlog };
  if (!(await obstaja(KOREN))) return { omogoceno: false, razlog: "Mapa trening/ ne obstaja v projektu." };
  const modeli = await Promise.all((await mape(MODELI)).map(beriModel));
  return { omogoceno: true, vir: "lokalno", koren: KOREN, modeli, znanje: await beriBesedilo(path.join(KOREN, "ZNANJE.md")) };
}

// ---------- pisanje (samo aplikacija: ocene in nov model) ----------

async function zapisiJson(p: string, podatki: unknown) {
  const zacasna = `${p}.${process.pid}.tmp`;
  await fs.writeFile(zacasna, `${JSON.stringify(podatki, null, 2)}\n`, "utf8");
  await fs.rename(zacasna, p);
}

export async function shraniOceno(model: string, kljuc: string, ocena: Ocena) {
  const p = path.join(MODELI, model, "ocene.json");
  const obstojece = await beriJson<Record<string, Ocena>>(p);
  if (obstojece && "napaka" in obstojece) throw new Error(`ocene.json: ${obstojece.napaka}`);
  await zapisiJson(p, { ...(obstojece?.podatki ?? {}), [kljuc]: ocena });
}

export type VhodnaDatoteka = { ime: string; podatki: Buffer };

/** Ustvari mapo modela (model.json, vhod/, astra/, fable/) in shrani datoteke v vhod/ (podmape dovoljene, npr. slike/x.png). */
export async function ustvariModel(id: string, info: ModelInfo, vhod: VhodnaDatoteka[]) {
  const m = path.join(MODELI, id);
  if (await obstaja(m)) throw new Error(`Model "${id}" že obstaja.`);
  await fs.mkdir(path.join(m, "vhod"), { recursive: true });
  for (const { koda } of AI_JI) await fs.mkdir(path.join(m, koda), { recursive: true });
  await zapisiJson(path.join(m, "model.json"), info);
  for (const f of vhod) {
    const deli = f.ime.split("/").map((d) => path.basename(d).replace(/[^\w.\- ]/g, "_")).filter((d) => d && d !== "." && d !== "..");
    if (!deli.length) continue;
    const cilj = path.join(m, "vhod", ...deli);
    await fs.mkdir(path.dirname(cilj), { recursive: true });
    await fs.writeFile(cilj, f.podatki);
  }
}

export async function izFile(f: File): Promise<VhodnaDatoteka> {
  return { ime: f.name, podatki: Buffer.from(await f.arrayBuffer()) };
}

// ---------- Supabase z žetonom prijavljenega admina (RLS velja kot v brskalniku) ----------

export function zetonIz(req: Request): string | null {
  const glava = req.headers.get("authorization");
  return glava?.startsWith("Bearer ") ? glava.slice(7) : new URL(req.url).searchParams.get("t");
}

function sbZa(zeton: string) {
  if (!URL_SB || !KLJUC_SB) throw new Error("Supabase ni nastavljen (.env.local).");
  return createClient(URL_SB, KLJUC_SB, {
    global: { headers: { Authorization: `Bearer ${zeton}` } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

const BUCKET_TRENING = "wi_trening";
const BUCKET_VHOD = "wi_ai_vhod";

function sbNapaka(e: { message: string; code?: string } | null, kje: string) {
  if (!e) return;
  if (e.code === "42P01" || /does not exist|schema cache/i.test(e.message)) {
    throw new Error("Tabele AI orodij ne obstajajo - zaženi migracijo supabase/migrations/004_ai_orodja.sql.");
  }
  throw new Error(`${kje}: ${e.message}`);
}

const VRSTA_VSEBINE: Record<string, string> = { ".mp4": "video/mp4", ".webm": "video/webm", ".png": "image/png", ".jpg": "image/jpeg" };

/**
 * Objavi trening na produkcijo: modeli, poskusi (meta, deli, koraki, poročila, ocene) in ZNANJE.md v tabele,
 * video in predogled v bucket wi_trening. Datoteke, ki so že naložene z isto velikostjo, preskoči.
 */
export async function objaviNaProdukcijo(zeton: string) {
  const sb = sbZa(zeton);
  const indeks = await beriIndeks();
  if (!indeks.omogoceno) throw new Error(indeks.razlog);
  const zdaj = new Date().toISOString();
  let poskusov = 0;
  let datotek = 0;

  for (const m of indeks.modeli) {
    const info = m.info && "podatki" in m.info ? m.info.podatki : null;
    const { data: vrstica, error } = await sb
      .from("wi_ai_modeli")
      .upsert(
        { koda: m.id, naziv: info?.naziv ?? m.id, opis: info?.opis ?? null, zahteva_id: info?.zahteva_id ?? null, objavljeno_at: zdaj, visible: true },
        { onConflict: "koda" },
      )
      .select("id")
      .single();
    sbNapaka(error, `Model ${m.id}`);
    const modelId = (vrstica as { id: number }).id;

    for (const { koda } of AI_JI) {
      for (const p of m.poskusi[koda]) {
        const mapa = `${m.id}/${koda}/${p.poskus}`;
        const { data: obstojece } = await sb.storage.from(BUCKET_TRENING).list(mapa);
        const velikosti = new Map((obstojece ?? []).map((o) => [o.name, Number(o.metadata?.size ?? -1)]));

        const nalozi = async (pot: string | null): Promise<{ pot: string; velikost: number } | null> => {
          if (!pot) return null;
          const abs = varnaPot(pot);
          if (!abs) return null;
          const ime = path.basename(abs);
          const cilj = `${mapa}/${ime}`;
          const st = await fs.stat(abs);
          if (velikosti.get(ime) !== st.size) {
            const { error: e } = await sb.storage
              .from(BUCKET_TRENING)
              .upload(cilj, await fs.readFile(abs), {
                upsert: true,
                contentType: VRSTA_VSEBINE[path.extname(ime).toLowerCase()] ?? "application/octet-stream",
              });
            sbNapaka(e, `Nalaganje ${cilj}`);
            datotek++;
          }
          return { pot: cilj, velikost: st.size };
        };

        const video = await nalozi(p.video);
        const predogled = await nalozi(p.predogled);
        const { error: e2 } = await sb.from("wi_ai_poskusi").upsert(
          {
            model_id: modelId,
            ai: koda,
            poskus: p.poskus,
            meta: p.meta && "podatki" in p.meta ? p.meta.podatki : null,
            deli: p.deli && "podatki" in p.deli ? p.deli.podatki : null,
            koraki: p.koraki && "podatki" in p.koraki ? p.koraki.podatki : null,
            porocilo: p.porocilo,
            spoznanja: p.spoznanja,
            video: video?.pot ?? null,
            video_velikost: video?.velikost ?? null,
            predogled: predogled?.pot ?? null,
            ocena: m.ocene[kljucOcene(koda, p.poskus)] ?? null,
            visible: true,
          },
          { onConflict: "model_id,ai,poskus" },
        );
        sbNapaka(e2, `Poskus ${mapa}`);
        poskusov++;
      }
    }
  }

  const { error: e3 } = await sb.from("wi_ai_besedila").upsert({ kljuc: "znanje", vsebina: indeks.znanje, visible: true }, { onConflict: "kljuc" });
  sbNapaka(e3, "ZNANJE.md");
  return { modelov: indeks.modeli.length, poskusov, datotek };
}

/** "Omara FBM-40S" -> "omara-fbm-40s" */
const vSlug = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);

/**
 * Zahteva AI video creation -> nov model v treningu: prenese datoteke iz bucketa wi_ai_vhod v
 * trening/modeli/<koda>/vhod/ (step/, kosovnica/, slike/), opis gre v model.json, zahteva dobi status v_delu.
 */
export async function zahtevaVTrening(zeton: string, zahtevaId: number) {
  const sb = sbZa(zeton);
  const { data: z, error } = await sb.from("wi_ai_zahteve").select("id, naziv, opis, oddal, model_koda").eq("id", zahtevaId).single();
  sbNapaka(error, "Zahteva");
  const zahteva = z as { id: number; naziv: string; opis: string | null; oddal: string; model_koda: string | null };
  if (zahteva.model_koda) throw new Error(`Zahteva je že v treningu (model ${zahteva.model_koda}).`);

  const { data: dat, error: e2 } = await sb
    .from("wi_ai_zahteve_datoteke")
    .select("vrsta, ime, pot")
    .eq("zahteva_id", zahtevaId)
    .eq("visible", true);
  sbNapaka(e2, "Datoteke zahteve");

  const MAPA: Record<string, string> = { step: "step", kosovnica: "kosovnica", slika: "slike", drugo: "drugo" };
  const vhod: VhodnaDatoteka[] = [];
  for (const d of (dat ?? []) as { vrsta: string; ime: string; pot: string }[]) {
    const { data: blob, error: e3 } = await sb.storage.from(BUCKET_VHOD).download(d.pot);
    sbNapaka(e3, `Prenos ${d.ime}`);
    vhod.push({ ime: `${MAPA[d.vrsta] ?? "drugo"}/${d.ime}`, podatki: Buffer.from(await blob!.arrayBuffer()) });
  }

  const koda = `z${zahteva.id}-${vSlug(zahteva.naziv) || "model"}`;
  await ustvariModel(
    koda,
    { naziv: zahteva.naziv, opis: zahteva.opis ?? "", ustvarjen: new Date().toISOString(), zahteva_id: zahteva.id, oddal: zahteva.oddal },
    vhod,
  );
  const { error: e4 } = await sb.from("wi_ai_zahteve").update({ status: "v_delu", model_koda: koda }).eq("id", zahtevaId);
  sbNapaka(e4, "Status zahteve");
  return { koda, datotek: vhod.length };
}
