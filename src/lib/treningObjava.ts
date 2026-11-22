// AI trening na produkciji: bere objavljeno kopijo iz Supabase (tabele wi_ai_*, bucket wi_trening).
// Objavo naredi gumb "Objavi na produkcijo" na lokalnem strežniku.
import { db, napaka } from "./supabase";
import {
  AI_JI,
  kljucOcene,
  type AiKoda,
  type Datoteka,
  type Del,
  type Korak,
  type ModelInfo,
  type Ocena,
  type Poskus,
  type PoskusMeta,
  type TreningIndeks,
  type TreningModel,
} from "./trening";

const BUCKET = "wi_trening";
/** Podpisani URL-ji veljajo 6 ur (stran je odprta na sestanku). */
const VELJAVNOST_S = 6 * 3600;

type ModelVrstica = { id: number; koda: string; naziv: string; opis: string | null; zahteva_id: number | null; objavljeno_at: string | null };
type PoskusVrstica = {
  model_id: number;
  ai: string;
  poskus: string;
  meta: PoskusMeta | null;
  deli: Del[] | null;
  koraki: Korak[] | null;
  porocilo: string | null;
  spoznanja: string | null;
  video: string | null;
  video_velikost: number | null;
  predogled: string | null;
  ocena: Ocena | null;
  updated_at: string;
};

const json = <T,>(v: T | null) => (v === null || v === undefined ? null : { podatki: v });

export type ObjavljenTrening = {
  indeks: TreningIndeks;
  /** URL datoteke iz poti v bucketu. */
  urlji: Record<string, string>;
  objavljeno: string | null;
};

export async function naloziObjavljeno(): Promise<ObjavljenTrening> {
  const sb = db();
  const [m, p, z] = await Promise.all([
    sb.from("wi_ai_modeli").select("id, koda, naziv, opis, zahteva_id, objavljeno_at").eq("visible", true).order("koda"),
    sb
      .from("wi_ai_poskusi")
      .select("model_id, ai, poskus, meta, deli, koraki, porocilo, spoznanja, video, video_velikost, predogled, ocena, updated_at")
      .eq("visible", true)
      .order("poskus"),
    sb.from("wi_ai_besedila").select("vsebina").eq("kljuc", "znanje").maybeSingle(),
  ]);
  napaka(m.error);
  napaka(p.error);
  const modeliV = (m.data ?? []) as ModelVrstica[];
  const poskusiV = (p.data ?? []) as PoskusVrstica[];

  const poti = poskusiV.flatMap((x) => [x.video, x.predogled]).filter((x): x is string => !!x);
  const urlji: Record<string, string> = {};
  if (poti.length) {
    const { data, error } = await sb.storage.from(BUCKET).createSignedUrls(poti, VELJAVNOST_S);
    if (error) throw new Error(error.message);
    for (const d of data ?? []) if (d.path && d.signedUrl) urlji[d.path] = d.signedUrl;
  }

  const modeli: TreningModel[] = modeliV.map((mv) => {
    const poskusi = Object.fromEntries(AI_JI.map((a) => [a.koda, [] as Poskus[]])) as Record<AiKoda, Poskus[]>;
    const ocene: Record<string, Ocena> = {};
    for (const x of poskusiV.filter((v) => v.model_id === mv.id)) {
      const ai = AI_JI.find((a) => a.koda === x.ai)?.koda;
      if (!ai) continue;
      const datoteke: Datoteka[] = [
        x.video && { pot: x.video, ime: x.video.split("/").pop()!, velikost: x.video_velikost ?? 0, cas: x.updated_at },
        x.predogled && { pot: x.predogled, ime: x.predogled.split("/").pop()!, velikost: 0, cas: x.updated_at },
      ].filter((d): d is Datoteka => !!d);
      poskusi[ai].push({
        ai,
        poskus: x.poskus,
        meta: json(x.meta),
        deli: json(x.deli),
        koraki: json(x.koraki),
        porocilo: x.porocilo,
        spoznanja: x.spoznanja,
        video: x.video,
        predogled: x.predogled,
        datoteke,
      });
      if (x.ocena) ocene[kljucOcene(ai, x.poskus)] = x.ocena;
    }
    const info: ModelInfo = { naziv: mv.naziv, opis: mv.opis ?? undefined, zahteva_id: mv.zahteva_id ?? undefined };
    return { id: mv.koda, info: { podatki: info }, vhod: [], poskusi, ocene };
  });

  const objavljeno = modeliV.map((x) => x.objavljeno_at).filter((x): x is string => !!x).sort().pop() ?? null;
  return {
    indeks: { omogoceno: true, vir: "objava", modeli, znanje: (z.data as { vsebina: string | null } | null)?.vsebina ?? null },
    urlji,
    objavljeno,
  };
}

/** Čas zadnje objave (za prikaz na lokalnem strežniku); null, če še ni objave ali tabel. */
export async function zadnjaObjava(): Promise<string | null> {
  const { data, error } = await db()
    .from("wi_ai_modeli")
    .select("objavljeno_at")
    .not("objavljeno_at", "is", null)
    .order("objavljeno_at", { ascending: false })
    .limit(1);
  if (error) return null;
  return (data?.[0] as { objavljeno_at: string } | undefined)?.objavljeno_at ?? null;
}
