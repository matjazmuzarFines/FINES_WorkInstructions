import { KRITERIJI, jeAiKoda, kljucOcene, type Ocena } from "@/lib/trening";
import { beriIndeks, jeVarnoIme, preveriAdmina, razlogIzklopa, shraniOceno, ustvariModel } from "@/lib/treningStreznik";

/** Indeks training grounda: modeli, vhodne datoteke, poskusi obeh AI-jev in ocene. */
export async function GET(req: Request) {
  const izklop = razlogIzklopa();
  if (izklop) return Response.json({ omogoceno: false, razlog: izklop });
  const ni = await preveriAdmina(req);
  if (ni) return Response.json({ napaka: ni }, { status: 401 });
  return Response.json(await beriIndeks(), { headers: { "Cache-Control": "no-store" } });
}

/**
 * POST JSON { akcija: "ocena", model, ai, poskus, ocena } - shrani oceno poskusa v ocene.json.
 * POST multipart (akcija=model, id, naziv, opis, datoteke) - ustvari nov model.
 */
export async function POST(req: Request) {
  const izklop = razlogIzklopa();
  if (izklop) return Response.json({ napaka: izklop }, { status: 403 });
  const ni = await preveriAdmina(req);
  if (ni) return Response.json({ napaka: ni }, { status: 401 });

  try {
    if (req.headers.get("content-type")?.includes("multipart/form-data")) {
      const f = await req.formData();
      const id = String(f.get("id") ?? "").trim().toLowerCase();
      if (!jeVarnoIme(id)) return napaka("ID modela: male črke, številke, - ali _ (do 64 znakov).");
      const naziv = String(f.get("naziv") ?? "").trim();
      if (!naziv) return napaka("Vpiši naziv modela.");
      const datoteke = f.getAll("datoteke").filter((d): d is File => d instanceof File && d.size > 0);
      await ustvariModel(
        id,
        { naziv, opis: String(f.get("opis") ?? "").trim(), ustvarjen: new Date().toISOString() },
        datoteke,
      );
      return Response.json({ ok: true, id });
    }

    const b = (await req.json()) as { akcija?: string; model?: string; ai?: string; poskus?: string; ocena?: Ocena };
    if (b.akcija !== "ocena") return napaka("Neznana akcija.");
    if (!b.model || !jeVarnoIme(b.model) || !jeAiKoda(b.ai) || !b.poskus || !jeVarnoIme(b.poskus)) {
      return napaka("Neveljaven model / AI / poskus.");
    }
    const kriteriji: Ocena["kriteriji"] = {};
    for (const k of KRITERIJI) {
      const v = b.ocena?.kriteriji?.[k.koda];
      if (typeof v === "number" && v >= 1 && v <= 5) kriteriji[k.koda] = Math.round(v);
    }
    await shraniOceno(b.model, kljucOcene(b.ai, b.poskus), {
      kriteriji,
      komentar: String(b.ocena?.komentar ?? "").slice(0, 5000),
      datum: new Date().toISOString(),
    });
    return Response.json({ ok: true });
  } catch (e) {
    return napaka((e as Error).message, 500);
  }
}

const napaka = (sporocilo: string, status = 400) => Response.json({ napaka: sporocilo }, { status });
