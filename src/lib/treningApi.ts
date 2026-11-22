// AI trening - klici iz brskalnika na lokalni API (/api/trening). Vsak klic nosi žeton prijave.
import { db } from "./supabase";
import type { AiKoda, Ocena, TreningIndeks } from "./trening";

export async function zeton(): Promise<string> {
  const { data } = await db().auth.getSession();
  const t = data.session?.access_token;
  if (!t) throw new Error("Ni prijave.");
  return t;
}

async function odgovor<T>(r: Response): Promise<T> {
  const j = (await r.json().catch(() => ({}))) as T & { napaka?: string };
  if (!r.ok || j.napaka) throw new Error(j.napaka ?? `Napaka strežnika (${r.status}).`);
  return j;
}

export async function naloziIndeks(): Promise<{ indeks: TreningIndeks; zeton: string }> {
  const t = await zeton();
  const r = await fetch("/api/trening", { headers: { Authorization: `Bearer ${t}` }, cache: "no-store" });
  return { indeks: await odgovor<TreningIndeks>(r), zeton: t };
}

export async function shraniOceno(model: string, ai: AiKoda, poskus: string, ocena: Ocena) {
  const r = await fetch("/api/trening", {
    method: "POST",
    headers: { Authorization: `Bearer ${await zeton()}`, "Content-Type": "application/json" },
    body: JSON.stringify({ akcija: "ocena", model, ai, poskus, ocena }),
  });
  await odgovor(r);
}

export async function ustvariModel(id: string, naziv: string, opis: string, datoteke: File[]) {
  const f = new FormData();
  f.set("id", id);
  f.set("naziv", naziv);
  f.set("opis", opis);
  for (const d of datoteke) f.append("datoteke", d);
  const r = await fetch("/api/trening", { method: "POST", headers: { Authorization: `Bearer ${await zeton()}` }, body: f });
  await odgovor(r);
}

/** URL izhodne datoteke poskusa (video, slika, JSON ...). */
export const urlDatoteke = (pot: string, t: string) =>
  `/api/trening/datoteka?pot=${encodeURIComponent(pot)}&t=${encodeURIComponent(t)}`;

async function akcija<T>(telo: Record<string, unknown>): Promise<T> {
  const r = await fetch("/api/trening", {
    method: "POST",
    headers: { Authorization: `Bearer ${await zeton()}`, "Content-Type": "application/json" },
    body: JSON.stringify(telo),
  });
  return odgovor<T>(r);
}

/** Objavi trening na produkcijo (samo lokalni strežnik). */
export const objaviTrening = () => akcija<{ modelov: number; poskusov: number; datotek: number }>({ akcija: "objavi" });

/** Zahtevo AI video creation prenese v nov model treninga (samo lokalni strežnik). */
export const zahtevaVTrening = (id: number) => akcija<{ koda: string; datotek: number }>({ akcija: "zahteva", id });

/** Ali aplikacija teče na lokalnem strežniku (mapa trening/ in lokalne akcije). */
export async function jeLokalno(): Promise<boolean> {
  try {
    const r = await fetch("/api/trening?stanje=1", { cache: "no-store" });
    const j = (await r.json()) as { lokalno?: boolean };
    return !!j.lokalno;
  } catch {
    return false;
  }
}
