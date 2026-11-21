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
  return { omogoceno: true, koren: KOREN, modeli, znanje: await beriBesedilo(path.join(KOREN, "ZNANJE.md")) };
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

/** Ustvari mapo modela (model.json, vhod/, astra/, fable/) in shrani naložene datoteke v vhod/. */
export async function ustvariModel(id: string, info: ModelInfo, vhod: File[]) {
  const m = path.join(MODELI, id);
  if (await obstaja(m)) throw new Error(`Model "${id}" že obstaja.`);
  await fs.mkdir(path.join(m, "vhod"), { recursive: true });
  for (const { koda } of AI_JI) await fs.mkdir(path.join(m, koda), { recursive: true });
  await zapisiJson(path.join(m, "model.json"), info);
  for (const f of vhod) {
    const ime = path.basename(f.name).replace(/[^\w.\- ]/g, "_");
    await fs.writeFile(path.join(m, "vhod", ime), Buffer.from(await f.arrayBuffer()));
  }
}
