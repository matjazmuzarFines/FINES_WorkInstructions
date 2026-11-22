// AI video creation - zahteve razvojnikov (Supabase: wi_ai_zahteve, wi_ai_zahteve_datoteke, bucket wi_ai_vhod)
// in poraba API kreditov (wi_ai_poraba, wi_ai_nastavitve).
import { useEffect, useState } from "react";
import { db, fetchAll, napaka } from "./supabase";

export const BUCKET_VHOD = "wi_ai_vhod";
/** Omejitev bucketa (brezplačen Supabase paket). */
export const MAX_DATOTEKA = 50 * 1024 * 1024;

export type ZahtevaStatus = "oddano" | "v_delu" | "koncano" | "zavrnjeno";
export type VrstaDatoteke = "step" | "kosovnica" | "slika" | "drugo";

export const STATUSI: Record<ZahtevaStatus, { label: string; cls: string }> = {
  oddano: { label: "Oddano", cls: "bg-warn-50 text-warn-700" },
  v_delu: { label: "V delu", cls: "bg-sync-50 text-sync-600" },
  koncano: { label: "Končano", cls: "bg-ok-50 text-ok-600" },
  zavrnjeno: { label: "Zavrnjeno", cls: "bg-nok-50 text-nok-600" },
};

export type ZahtevaDatoteka = { id: number; vrsta: VrstaDatoteke; ime: string; pot: string; velikost: number | null };

export type Zahteva = {
  id: number;
  naziv: string;
  opis: string | null;
  status: ZahtevaStatus;
  oddal: string;
  nacin: "lokalno" | "api";
  model_koda: string | null;
  opomba: string | null;
  created_at: string;
  updated_at: string;
  datoteke: ZahtevaDatoteka[];
};

/** Dogodek ob spremembi zahtev - značka v meniju se osveži takoj. */
const DOGODEK = "wi-ai-zahteve";
export const obvestiZahteve = () => window.dispatchEvent(new Event(DOGODEK));

export async function naloziZahteve(): Promise<Zahteva[]> {
  const zahteve = await fetchAll<Omit<Zahteva, "datoteke">>((from, to) =>
    db()
      .from("wi_ai_zahteve")
      .select("id, naziv, opis, status, oddal, nacin, model_koda, opomba, created_at, updated_at")
      .eq("visible", true)
      .order("created_at", { ascending: false })
      .range(from, to),
  );
  const datoteke = await fetchAll<ZahtevaDatoteka & { zahteva_id: number }>((from, to) =>
    db().from("wi_ai_zahteve_datoteke").select("id, zahteva_id, vrsta, ime, pot, velikost").eq("visible", true).order("id").range(from, to),
  );
  return zahteve.map((z) => ({ ...z, datoteke: datoteke.filter((d) => d.zahteva_id === z.id) }));
}

const varnoIme = (ime: string) => ime.replace(/[^\w.\- ]/g, "_").slice(-120);

/** Odda zahtevo: vrstica v wi_ai_zahteve, datoteke v bucket wi_ai_vhod/<id>/<vrsta>/<ime>. */
export async function oddajZahtevo(
  naziv: string,
  opis: string,
  datoteke: { vrsta: VrstaDatoteke; file: File }[],
  onNapredek?: (opravljeno: number, vse: number) => void,
): Promise<number> {
  const sb = db();
  const { data, error } = await sb.from("wi_ai_zahteve").insert({ naziv, opis: opis || null }).select("id").single();
  napaka(error);
  const id = (data as { id: number }).id;
  let n = 0;
  for (const { vrsta, file } of datoteke) {
    const pot = `${id}/${vrsta}/${varnoIme(file.name)}`;
    const { error: e1 } = await sb.storage.from(BUCKET_VHOD).upload(pot, file, { upsert: true, contentType: file.type || "application/octet-stream" });
    if (e1) throw new Error(`Nalaganje ${file.name}: ${e1.message}`);
    const { error: e2 } = await sb.from("wi_ai_zahteve_datoteke").insert({ zahteva_id: id, vrsta, ime: file.name, pot, velikost: file.size });
    napaka(e2);
    onNapredek?.(++n, datoteke.length);
  }
  obvestiZahteve();
  return id;
}

export async function nastaviStatus(id: number, status: ZahtevaStatus, opomba?: string) {
  const sprememba: Record<string, unknown> = { status };
  if (opomba !== undefined) sprememba.opomba = opomba || null;
  const { error } = await db().from("wi_ai_zahteve").update(sprememba).eq("id", id);
  napaka(error);
  obvestiZahteve();
}

/** Prenos datoteke zahteve (podpisan URL, velja 10 min). */
export async function urlDatotekeZahteve(pot: string): Promise<string> {
  const { data, error } = await db().storage.from(BUCKET_VHOD).createSignedUrl(pot, 600, { download: true });
  if (error || !data) throw new Error(error?.message ?? "Datoteke ni mogoče prenesti.");
  return data.signedUrl;
}

/** Število oddanih (še neobdelanih) zahtev - značka v meniju. Osveži se vsako minuto in ob spremembi. */
export function useStevecZahtev(aktiven: boolean): number {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!aktiven) return;
    let preklicano = false;
    const preberi = async () => {
      const { count, error } = await db()
        .from("wi_ai_zahteve")
        .select("id", { count: "exact", head: true })
        .eq("visible", true)
        .eq("status", "oddano");
      if (!preklicano && !error) setN(count ?? 0);
    };
    preberi();
    const t = window.setInterval(preberi, 60_000);
    window.addEventListener(DOGODEK, preberi);
    return () => {
      preklicano = true;
      window.clearInterval(t);
      window.removeEventListener(DOGODEK, preberi);
    };
  }, [aktiven]);
  return aktiven ? n : 0;
}

// ---------- poraba API kreditov ----------

export type Proracun = { mesecni_usd: number; dan_obnove: number; api_vklopljen: boolean };

export type Poraba = {
  proracun: Proracun;
  porabljeno: number;
  zahtevkov: number;
  vhodni: number;
  izhodni: number;
  od: Date;
  obnova: Date;
};

/** Začetek trenutnega obračunskega obdobja in naslednja obnova kreditov. */
export function obdobje(danObnove: number, zdaj = new Date()): { od: Date; obnova: Date } {
  const dan = Math.min(Math.max(Math.round(danObnove) || 1, 1), 28);
  let od = new Date(zdaj.getFullYear(), zdaj.getMonth(), dan);
  if (od > zdaj) od = new Date(zdaj.getFullYear(), zdaj.getMonth() - 1, dan);
  return { od, obnova: new Date(od.getFullYear(), od.getMonth() + 1, dan) };
}

export async function naloziPorabo(): Promise<Poraba> {
  const { data, error } = await db().from("wi_ai_nastavitve").select("vrednost").eq("kljuc", "proracun").maybeSingle();
  napaka(error);
  const proracun: Proracun = { mesecni_usd: 100, dan_obnove: 1, api_vklopljen: false, ...((data?.vrednost as Partial<Proracun>) ?? {}) };
  const { od, obnova } = obdobje(proracun.dan_obnove);
  const vrstice = await fetchAll<{ cena_usd: number | string; vhodni_zetoni: number; izhodni_zetoni: number }>((from, to) =>
    db()
      .from("wi_ai_poraba")
      .select("cena_usd, vhodni_zetoni, izhodni_zetoni")
      .eq("visible", true)
      .gte("created_at", od.toISOString())
      .range(from, to),
  );
  return {
    proracun,
    porabljeno: vrstice.reduce((s, v) => s + Number(v.cena_usd), 0),
    zahtevkov: vrstice.length,
    vhodni: vrstice.reduce((s, v) => s + Number(v.vhodni_zetoni), 0),
    izhodni: vrstice.reduce((s, v) => s + Number(v.izhodni_zetoni), 0),
    od,
    obnova,
  };
}

export async function shraniProracun(p: Proracun) {
  const { error } = await db().from("wi_ai_nastavitve").update({ vrednost: p }).eq("kljuc", "proracun");
  napaka(error);
}
